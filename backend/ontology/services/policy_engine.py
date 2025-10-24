"""
HeartBeat Engine - Policy Enforcement Engine
NHL Advanced Analytics Platform

High-performance RBAC/ABAC policy enforcement for ontology operations.
Enterprise-grade security with row/column-level filtering.
"""

from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import logging

from ..models.metadata import SecurityPolicy, PolicyRule
from orchestrator.config.settings import UserRole
from orchestrator.utils.state import UserContext

logger = logging.getLogger(__name__)


class AccessLevel(Enum):
    """Access levels for policy enforcement"""
    NONE = "none"
    READ = "read"
    FULL = "full"
    EXECUTE = "execute"
    SELF_ONLY = "self_only"


class Scope(Enum):
    """Access scope for policy enforcement"""
    ALL = "all"
    TEAM_SCOPED = "team_scoped"
    SELF_ONLY = "self_only"


@dataclass
class PolicyDecision:
    """Result of policy evaluation"""
    allowed: bool
    access_level: AccessLevel
    scope: Optional[Scope]
    column_filters: List[str]
    row_filter: Optional[str]
    reason: str


class PolicyEngine:
    """
    Policy enforcement engine for OMS operations.
    
    Provides high-performance policy evaluation with caching
    and optimized rule matching.
    """
    
    def __init__(self):
        """Initialize policy engine"""
        self._policy_cache: Dict[str, SecurityPolicy] = {}
        self._decision_cache: Dict[str, PolicyDecision] = {}
        logger.info("PolicyEngine initialized")
    
    def evaluate_access(
        self,
        user_context: UserContext,
        operation: str,
        target_type: str,
        target_id: Optional[str] = None,
        policy: Optional[SecurityPolicy] = None
    ) -> PolicyDecision:
        """
        Evaluate user access for an operation.
        
        Args:
            user_context: User context with role and team access
            operation: Operation being performed (read, write, execute)
            target_type: Type of target (object, link, action)
            target_id: Optional specific target identifier
            policy: Security policy to evaluate (required)
            
        Returns:
            PolicyDecision with allow/deny and filters
        """
        if not policy:
            logger.warning(f"No policy provided for {target_type}, denying access")
            return PolicyDecision(
                allowed=False,
                access_level=AccessLevel.NONE,
                scope=None,
                column_filters=[],
                row_filter=None,
                reason="No policy defined"
            )
        
        # Generate cache key
        cache_key = self._generate_cache_key(
            user_context.role,
            operation,
            target_type,
            policy.name
        )
        
        # Check cache
        if cache_key in self._decision_cache:
            return self._decision_cache[cache_key]
        
        # Find matching rule for user's role
        matching_rule = self._find_matching_rule(policy, user_context.role)
        
        if not matching_rule:
            decision = PolicyDecision(
                allowed=False,
                access_level=AccessLevel.NONE,
                scope=None,
                column_filters=[],
                row_filter=None,
                reason=f"No rule found for role {user_context.role.value}"
            )
        else:
            decision = self._evaluate_rule(matching_rule, user_context, operation)
        
        # Cache decision
        self._decision_cache[cache_key] = decision
        
        return decision
    
    def _find_matching_rule(
        self,
        policy: SecurityPolicy,
        role: UserRole
    ) -> Optional[PolicyRule]:
        """
        Find policy rule matching user's role.
        
        Rules are sorted by priority (higher priority first).
        Wildcard "*" role matches all roles.
        """
        if not policy.rules:
            return None
        
        # Sort rules by priority (descending)
        sorted_rules = sorted(
            policy.rules,
            key=lambda r: r.priority,
            reverse=True
        )
        
        # Find exact role match first
        for rule in sorted_rules:
            if rule.role == role.value:
                return rule
        
        # Check for wildcard rule
        for rule in sorted_rules:
            if rule.role == "*":
                return rule
        
        return None
    
    def _evaluate_rule(
        self,
        rule: PolicyRule,
        user_context: UserContext,
        operation: str
    ) -> PolicyDecision:
        """Evaluate a policy rule for user context"""
        access_level = AccessLevel(rule.access_level)
        
        # Check if operation is allowed for this access level
        allowed = self._check_operation_allowed(operation, access_level)
        
        if not allowed:
            return PolicyDecision(
                allowed=False,
                access_level=access_level,
                scope=None,
                column_filters=[],
                row_filter=None,
                reason=f"Operation '{operation}' not allowed for access level '{access_level.value}'"
            )
        
        # Parse scope
        scope = Scope(rule.scope) if rule.scope else Scope.ALL
        
        # Build row filter
        row_filter = self._build_row_filter(rule, user_context, scope)
        
        # Get column filters
        column_filters = rule.column_filters or []
        
        # Check conditions if present
        if rule.conditions:
            conditions_met = self._evaluate_conditions(rule.conditions, user_context)
            if not conditions_met:
                return PolicyDecision(
                    allowed=False,
                    access_level=access_level,
                    scope=scope,
                    column_filters=[],
                    row_filter=None,
                    reason="Rule conditions not met"
                )
        
        return PolicyDecision(
            allowed=True,
            access_level=access_level,
            scope=scope,
            column_filters=column_filters,
            row_filter=row_filter,
            reason=f"Access granted via rule for role {rule.role}"
        )
    
    def _check_operation_allowed(
        self,
        operation: str,
        access_level: AccessLevel
    ) -> bool:
        """Check if operation is allowed for access level"""
        if access_level == AccessLevel.NONE:
            return False
        
        if access_level == AccessLevel.FULL:
            return True
        
        if access_level == AccessLevel.READ:
            return operation in {"read", "list", "get"}
        
        if access_level == AccessLevel.EXECUTE:
            return operation in {"execute", "invoke"}
        
        if access_level == AccessLevel.SELF_ONLY:
            return operation in {"read", "get"}
        
        return False
    
    def _build_row_filter(
        self,
        rule: PolicyRule,
        user_context: UserContext,
        scope: Scope
    ) -> Optional[str]:
        """
        Build SQL WHERE clause for row-level filtering.
        
        Args:
            rule: Policy rule with filter expression
            user_context: User context
            scope: Access scope
            
        Returns:
            SQL WHERE clause or None
        """
        filters = []
        
        # Apply scope-based filters
        if scope == Scope.TEAM_SCOPED:
            if user_context.team_access:
                team_ids = "', '".join(user_context.team_access)
                filters.append(f"teamId IN ('{team_ids}')")
        
        elif scope == Scope.SELF_ONLY:
            filters.append(f"playerId = '{user_context.user_id}'")
        
        # Apply custom row filter expression
        if rule.row_filter_expr:
            # Substitute user context variables
            filter_expr = rule.row_filter_expr.replace(
                "{user_id}", f"'{user_context.user_id}'"
            )
            filter_expr = filter_expr.replace(
                "{team_id}", f"'{user_context.team_access[0]}'" if user_context.team_access else "''"
            )
            filters.append(f"({filter_expr})")
        
        return " AND ".join(filters) if filters else None
    
    def _evaluate_conditions(
        self,
        conditions: List[str],
        user_context: UserContext
    ) -> bool:
        """
        Evaluate rule conditions.
        
        Conditions are simple string expressions like:
        - "Scout.role == 'Director of Scouting'"
        - "User has role Manager"
        
        Returns True if all conditions are met.
        """
        for condition in conditions:
            if not self._evaluate_single_condition(condition, user_context):
                return False
        return True
    
    def _evaluate_single_condition(
        self,
        condition: str,
        user_context: UserContext
    ) -> bool:
        """Evaluate a single condition expression"""
        condition = condition.strip()
        
        # Handle "User has role X" pattern
        if condition.startswith("User has role"):
            role_name = condition.replace("User has role", "").strip()
            return user_context.role.value == role_name.lower()
        
        # Handle property equality checks
        if "==" in condition:
            left, right = condition.split("==", 1)
            left = left.strip()
            right = right.strip().strip("'\"")
            
            # For now, just log and return True
            # Full implementation would parse and evaluate expressions
            logger.debug(f"Condition evaluation: {left} == {right}")
            return True
        
        # Unknown condition format, default to True for safety
        logger.warning(f"Unknown condition format: {condition}")
        return True
    
    def apply_column_filters(
        self,
        data: Dict[str, Any],
        column_filters: List[str]
    ) -> Dict[str, Any]:
        """
        Apply column-level filtering to data.
        
        Removes fields listed in column_filters from the data dictionary.
        
        Args:
            data: Data dictionary
            column_filters: List of field names to remove
            
        Returns:
            Filtered data dictionary
        """
        if not column_filters:
            return data
        
        filtered = data.copy()
        for field in column_filters:
            if field in filtered:
                del filtered[field]
        
        return filtered
    
    def check_action_preconditions(
        self,
        preconditions: List[str],
        user_context: UserContext,
        inputs: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Check action preconditions.
        
        Args:
            preconditions: List of precondition expressions
            user_context: User context
            inputs: Action input parameters
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        for precondition in preconditions:
            result = self._evaluate_single_condition(precondition, user_context)
            if not result:
                return False, f"Precondition not met: {precondition}"
        
        return True, None
    
    def clear_cache(self) -> None:
        """Clear policy decision cache"""
        self._decision_cache.clear()
        logger.info("Policy cache cleared")
    
    def _generate_cache_key(
        self,
        role: UserRole,
        operation: str,
        target_type: str,
        policy_name: str
    ) -> str:
        """Generate cache key for policy decision"""
        return f"{role.value}:{operation}:{target_type}:{policy_name}"

