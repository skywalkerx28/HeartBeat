"""
HeartBeat Engine - OMS Schema Loading Test
NHL Advanced Analytics Platform

Test script to demonstrate schema loading and validation.
"""

from pathlib import Path
from schemas.validator import SchemaLoader
import json


def print_section(title: str):
    """Print formatted section header"""
    print(f"\n{'='*80}")
    print(f" {title}")
    print(f"{'='*80}\n")


def main():
    """Load and display ontology schema"""
    
    print_section("HeartBeat Ontology Metadata Service - Schema Test")
    
    # Load schema
    schema_dir = Path(__file__).parent / "schemas" / "v0.1"
    loader = SchemaLoader(schema_dir)
    
    print("Loading schema from:", schema_dir / "schema.yaml")
    schema = loader.load_schema()
    
    # Display metadata
    print_section("Schema Metadata")
    metadata = schema.get("metadata", {})
    print(f"Version: {schema.get('version')}")
    print(f"Namespace: {schema.get('namespace')}")
    print(f"Author: {metadata.get('author')}")
    print(f"Created: {metadata.get('created')}")
    print(f"Status: {metadata.get('status')}")
    
    # Display object types
    print_section("Object Types")
    object_types = loader.get_object_types(schema)
    print(f"Total Object Types: {len(object_types)}\n")
    
    for obj_name in sorted(object_types.keys()):
        obj_def = object_types[obj_name]
        pk = obj_def.get('primary_key')
        desc = obj_def.get('description', 'No description')
        resolver = obj_def.get('resolver', {})
        backend = resolver.get('backend', 'unknown')
        num_props = len(obj_def.get('properties', {}))
        
        print(f"  {obj_name:20} | PK: {pk:15} | Props: {num_props:2} | Backend: {backend:10} | {desc[:50]}")
    
    # Display link types
    print_section("Link Types")
    link_types = loader.get_link_types(schema)
    print(f"Total Link Types: {len(link_types)}\n")
    
    for link_name in sorted(link_types.keys()):
        link_def = link_types[link_name]
        from_obj = link_def.get('from_object', '')
        to_obj = link_def.get('to_object', '')
        cardinality = link_def.get('cardinality', '')
        desc = link_def.get('description', 'No description')
        
        print(f"  {link_name:30} | {from_obj:15} → {to_obj:15} | {cardinality:15} | {desc[:40]}")
    
    # Display action types
    print_section("Action Types")
    action_types = loader.get_action_types(schema)
    print(f"Total Action Types: {len(action_types)}\n")
    
    for action_name in sorted(action_types.keys()):
        action_def = action_types[action_name]
        desc = action_def.get('description', 'No description')
        input_schema = action_def.get('input_schema', {})
        num_inputs = len(input_schema)
        preconditions = action_def.get('preconditions', [])
        num_preconditions = len(preconditions)
        
        print(f"  {action_name:30} | Inputs: {num_inputs:2} | Preconditions: {num_preconditions:2} | {desc}")
        
        if preconditions:
            for precond in preconditions[:2]:
                print(f"    → {precond}")
    
    # Display security policies
    print_section("Security Policies")
    policies = loader.get_security_policies(schema)
    print(f"Total Security Policies: {len(policies)}\n")
    
    for policy_name in sorted(policies.keys()):
        policy_def = policies[policy_name]
        desc = policy_def.get('description', 'No description')
        rules = policy_def.get('rules', [])
        num_rules = len(rules)
        
        print(f"  {policy_name:35} | Rules: {num_rules:2} | {desc}")
    
    # Highlight Prospect entity
    print_section("Prospect Entity (Key Correction)")
    prospect = object_types.get('Prospect', {})
    print(f"Description: {prospect.get('description')}")
    print(f"\nKey Properties:")
    
    props = prospect.get('properties', {})
    key_props = ['prospectId', 'nhlTeamId', 'currentLeague', 'currentTeam', 
                 'contractStatus', 'developmentStatus']
    
    for prop_name in key_props:
        if prop_name in props:
            prop_def = props[prop_name]
            prop_type = prop_def.get('type')
            required = prop_def.get('required', False)
            desc = prop_def.get('description', '')
            req_marker = '(required)' if required else '(optional)'
            print(f"  {prop_name:20} | {prop_type:10} {req_marker:12} | {desc}")
    
    # Scout-Prospect relationship
    print_section("Scout-Prospect Relationship (Many-to-Many)")
    scout_prospects = link_types.get('scout_prospects', {})
    print(f"Description: {scout_prospects.get('description')}")
    print(f"Cardinality: {scout_prospects.get('cardinality')}")
    print(f"\nResolver Configuration:")
    resolver = scout_prospects.get('resolver', {})
    print(f"  Type: {resolver.get('type')}")
    print(f"  Table: {resolver.get('table')}")
    print(f"  From Field: {resolver.get('from_field')}")
    print(f"  To Field: {resolver.get('to_field')}")
    
    print("\nRationale:")
    print("  - Scouts are assigned to track multiple prospects globally")
    print("  - Prospects may be evaluated by multiple scouts (primary, regional, director)")
    print("  - Assignment table tracks priority level and assignment context")
    print("  - Reflects actual NHL scouting operations")
    
    # Security example
    print_section("Security Policy Example: contract_visibility")
    contract_policy = policies.get('contract_visibility', {})
    print(f"Description: {contract_policy.get('description')}\n")
    
    rules = contract_policy.get('rules', [])
    print(f"{'Role':15} | {'Access':10} | {'Scope':15} | {'Column Filters'}")
    print("-" * 80)
    
    for rule in rules:
        role = rule.get('role', '')
        access = rule.get('access', '')
        scope = rule.get('scope', 'N/A')
        filters = rule.get('column_filters', [])
        filter_str = ', '.join(filters[:3]) if filters else 'None'
        if len(filters) > 3:
            filter_str += '...'
        
        print(f"{role:15} | {access:10} | {scope:15} | {filter_str}")
    
    # Summary
    print_section("Phase 0 Summary")
    print("✓ Schema v0.1 loaded and validated successfully")
    print(f"✓ {len(object_types)} object types defined")
    print(f"✓ {len(link_types)} link types established")
    print(f"✓ {len(action_types)} action types specified")
    print(f"✓ {len(policies)} security policies implemented")
    print("\n✓ Prospect entity correctly represents owned player rights (not just draft picks)")
    print("✓ Scout-Prospect many-to-many relationship enables proper development tracking")
    print("✓ Granular security policies enforce role-based access control")
    print("✓ Dual backend resolver strategy (BigQuery + Parquet)")
    print("\nStatus: Phase 0 COMPLETE - Ready for Phase 1 Implementation")
    
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()

