#!/usr/bin/env python3
"""
Fix Database Schema - Add minors_salary column if missing
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

import duckdb
from bot.config import BOT_CONFIG

db_path = Path(__file__).parent.parent / BOT_CONFIG['db_path'].replace('../', '')

print(f"Database: {db_path}")

conn = duckdb.connect(str(db_path))

# Check current schema
schema = conn.execute("PRAGMA table_info(contract_details)").fetchall()
columns = [col[1] for col in schema]

print(f"\nCurrent columns: {columns}")

if 'minors_salary' not in columns:
    print("\nAdding minors_salary column...")
    conn.execute("ALTER TABLE contract_details ADD COLUMN minors_salary BIGINT")
    conn.commit()
    print("✓ minors_salary column added")
else:
    print("\n✓ minors_salary column already exists")

# Verify
schema = conn.execute("PRAGMA table_info(contract_details)").fetchall()
print("\nFinal schema:")
for col in schema:
    print(f"  {col[1]}: {col[2]}")

conn.close()
print("\nDatabase schema fixed!")

