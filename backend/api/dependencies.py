"""
HeartBeat Engine - FastAPI Dependencies
Montreal Canadiens Advanced Analytics Assistant

Dependency injection for FastAPI routes.
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import base64
import logging

from orchestrator.agents.qwen3_best_practices_orchestrator import Qwen3BestPracticesOrchestrator
from orchestrator.config.settings import UserRole
from orchestrator.utils.state import UserContext

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

# Global orchestrator instance (will be initialized in main.py)
_orchestrator: Qwen3BestPracticesOrchestrator = None

def set_orchestrator(orchestrator: Qwen3BestPracticesOrchestrator) -> None:
    """Set the global orchestrator instance"""
    global _orchestrator
    _orchestrator = orchestrator

def get_orchestrator() -> Qwen3BestPracticesOrchestrator:
    """Get the orchestrator instance - now using Best Practices Orchestrator"""
    if _orchestrator is None:
        # Lazy initialization with new best practices orchestrator
        from orchestrator.agents.qwen3_best_practices_orchestrator import get_orchestrator as get_bp_orch
        return get_bp_orch()
    return _orchestrator

# User database (same as auth.py for consistency)
USERS_DB = {
    "coach_martin": {
        "password": "coach2024",
        "name": "Martin St-Louis",
        "role": UserRole.COACH,
        "email": "martin@canadiens.com",
        "team_access": ["MTL"]
    },
    "analyst_hughes": {
        "password": "analyst2024", 
        "name": "Kent Hughes",
        "role": UserRole.ANALYST,
        "email": "kent@canadiens.com",
        "team_access": ["MTL"]
    },
    "player_suzuki": {
        "password": "player2024",
        "name": "Nick Suzuki", 
        "role": UserRole.PLAYER,
        "email": "nick@canadiens.com",
        "team_access": ["MTL"]
    },
    "scout_lapointe": {
        "password": "scout2024",
        "name": "Martin Lapointe",
        "role": UserRole.SCOUT, 
        "email": "martin.lapointe@canadiens.com",
        "team_access": ["MTL"]
    },
    "staff_molson": {
        "password": "staff2024",
        "name": "Geoff Molson",
        "role": UserRole.STAFF,
        "email": "geoff@canadiens.com", 
        "team_access": ["MTL"]
    }
}

def get_current_user_context(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserContext:
    """
    Extract user context from authentication token.
    
    For development, using simple token format: base64(username:password)
    In production, use proper JWT tokens with signing and expiration.
    """
    
    try:
        # Decode simple token format
        decoded = base64.b64decode(credentials.credentials).decode()
        username, password = decoded.split(":", 1)
        
        # Validate credentials
        user_data = USERS_DB.get(username)
        if not user_data or user_data["password"] != password:
            logger.warning(f"Invalid credentials for user: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create user context for orchestrator
        user_context = UserContext(
            user_id=username,
            role=user_data["role"],
            name=user_data["name"],
            team_access=user_data["team_access"],
            session_id=f"api-session-{username}"
        )
        
        logger.debug(f"User context created for: {username} ({user_data['role'].value})")
        return user_context
        
    except ValueError as e:
        logger.error(f"Token format error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_user_context_allow_query(
    request: Request,
) -> UserContext:
    """Variant that also accepts a base64 token via `?token=` query param for media requests.

    This enables <video> and <img> tags to access protected resources without custom headers.
    """
    token_param = request.query_params.get("token")
    if token_param:
        try:
            decoded = base64.b64decode(token_param).decode()
            username, password = decoded.split(":", 1)
            user_data = USERS_DB.get(username)
            if not user_data or user_data["password"] != password:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
            return UserContext(
                user_id=username,
                role=user_data["role"],
                name=user_data["name"],
                team_access=user_data["team_access"],
                session_id=f"api-session-{username}"
            )
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # Fallback to Authorization header if provided
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1]
        try:
            decoded = base64.b64decode(token).decode()
            username, password = decoded.split(":", 1)
            user_data = USERS_DB.get(username)
            if not user_data or user_data["password"] != password:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
            return UserContext(
                user_id=username,
                role=user_data["role"],
                name=user_data["name"],
                team_access=user_data["team_access"],
                session_id=f"api-session-{username}"
            )
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    # No auth supplied
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing credentials")
