#!/usr/bin/env python3
"""
Script to export DDL and DML from Supabase database using pg_dump
"""
import subprocess
import os
from urllib.parse import urlparse
from app.core.config import settings

def parse_database_url(db_url: str) -> dict:
    """Parse database URL into components"""
    parsed = urlparse(str(db_url))
    return {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'database': parsed.path[1:],  # Remove leading '/'
        'username': parsed.username,
        'password': parsed.password
    }

def export_schema_only(db_config: dict, output_file: str = "schema.sql"):
    """Export only the database schema (DDL)"""
    env = os.environ.copy()
    env['PGPASSWORD'] = db_config['password']
    
    cmd = [
        'pg_dump',
        '-h', db_config['host'],
        '-p', str(db_config['port']),
        '-U', db_config['username'],
        '-d', db_config['database'],
        '--schema-only',
        '--no-privileges',
        '--no-owner',
        '-f', output_file
    ]
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
        print(f"✅ Schema exported successfully to {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error exporting schema: {e.stderr}")
        return False

def export_data_only(db_config: dict, output_file: str = "data.sql"):
    """Export only the database data (DML)"""
    env = os.environ.copy()
    env['PGPASSWORD'] = db_config['password']
    
    cmd = [
        'pg_dump',
        '-h', db_config['host'],
        '-p', str(db_config['port']),
        '-U', db_config['username'],
        '-d', db_config['database'],
        '--data-only',
        '--no-privileges',
        '--no-owner',
        '-f', output_file
    ]
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
        print(f"✅ Data exported successfully to {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error exporting data: {e.stderr}")
        return False

def export_full_database(db_config: dict, output_file: str = "full_backup.sql"):
    """Export complete database (DDL + DML)"""
    env = os.environ.copy()
    env['PGPASSWORD'] = db_config['password']
    
    cmd = [
        'pg_dump',
        '-h', db_config['host'],
        '-p', str(db_config['port']),
        '-U', db_config['username'],
        '-d', db_config['database'],
        '--no-privileges',
        '--no-owner',
        '-f', output_file
    ]
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
        print(f"✅ Full database exported successfully to {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error exporting database: {e.stderr}")
        return False

def export_specific_tables(db_config: dict, tables: list, output_file: str = "tables.sql"):
    """Export specific tables only"""
    env = os.environ.copy()
    env['PGPASSWORD'] = db_config['password']
    
    table_args = []
    for table in tables:
        table_args.extend(['-t', table])
    
    cmd = [
        'pg_dump',
        '-h', db_config['host'],
        '-p', str(db_config['port']),
        '-U', db_config['username'],
        '-d', db_config['database'],
        '--no-privileges',
        '--no-owner',
    ] + table_args + ['-f', output_file]
    
    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
        print(f"✅ Tables {tables} exported successfully to {output_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error exporting tables: {e.stderr}")
        return False

if __name__ == "__main__":
    # Parse database configuration
    db_config = parse_database_url(settings.DATABASE_URL)
    
    print("🗄️  Supabase Database Export Tool")
    print("=" * 40)
    print("1. Export Schema Only (DDL)")
    print("2. Export Data Only (DML)")
    print("3. Export Full Database (DDL + DML)")
    print("4. Export Specific Tables")
    print("=" * 40)
    
    choice = input("Select option (1-4): ").strip()
    
    if choice == "1":
        export_schema_only(db_config, "exports/schema.sql")
    elif choice == "2":
        export_data_only(db_config, "exports/data.sql")
    elif choice == "3":
        export_full_database(db_config, "exports/full_backup.sql")
    elif choice == "4":
        tables_input = input("Enter table names (comma-separated): ").strip()
        tables = [t.strip() for t in tables_input.split(",") if t.strip()]
        if tables:
            export_specific_tables(db_config, tables, "exports/specific_tables.sql")
        else:
            print("❌ No tables specified")
    else:
        print("❌ Invalid choice")