#!/usr/bin/env python3
"""Quick verification that OMS is working"""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://heartbeat:192882@127.0.0.1:5434/postgres")
engine = create_engine(DATABASE_URL)

print("Verifying OMS in PostgreSQL...")
print(f"Database: {DATABASE_URL.split('@')[1]}\n")

with engine.connect() as conn:
    # Check schema
    result = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'oms'"))
    if result.scalar():
        print("✓ OMS schema exists")
    
    # Count object types
    result = conn.execute(text("SELECT COUNT(*) FROM oms.object_types"))
    print(f"✓ Object types in DB: {result.scalar()}")
    
    # Check active schema
    result = conn.execute(text("SELECT version, is_active FROM oms.schema_versions WHERE is_active=true"))
    row = result.fetchone()
    if row:
        print(f"✓ Active schema version: {row[0]}")
    
    # List object types
    result = conn.execute(text("SELECT name FROM oms.object_types ORDER BY name"))
    objects = [row[0] for row in result]
    print(f"\nObject types registered: {', '.join(objects)}")

print("\n✓ OMS PostgreSQL integration verified!")

