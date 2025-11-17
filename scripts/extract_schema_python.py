#!/usr/bin/env python3
"""
Python script to extract database schema information programmatically
"""
import psycopg2
from urllib.parse import urlparse
from app.core.config import settings
import os

class SupabaseSchemaExtractor:
    def __init__(self, database_url: str):
        self.db_url = database_url
        self.connection = None
        
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(self.db_url)
            print("✅ Connected to Supabase database")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def get_all_tables(self):
        """Get list of all tables in the database"""
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name;
        """
        
        with self.connection.cursor() as cursor:
            cursor.execute(query)
            return [row[0] for row in cursor.fetchall()]
    
    def get_table_ddl(self, table_name: str):
        """Generate DDL for a specific table"""
        ddl_parts = []
        
        # Get table structure
        query = """
        SELECT 
            column_name, 
            data_type, 
            is_nullable,
            column_default,
            character_maximum_length,
            numeric_precision,
            numeric_scale
        FROM information_schema.columns 
        WHERE table_name = %s AND table_schema = 'public'
        ORDER BY ordinal_position;
        """
        
        with self.connection.cursor() as cursor:
            cursor.execute(query, (table_name,))
            columns = cursor.fetchall()
            
            ddl_parts.append(f"-- DDL for table: {table_name}")
            ddl_parts.append(f"CREATE TABLE {table_name} (")
            
            column_definitions = []
            for col in columns:
                col_name, data_type, is_nullable, default, max_length, precision, scale = col
                
                # Build column definition
                col_def = f"    {col_name} {data_type.upper()}"
                
                # Add length/precision
                if max_length and data_type in ['character varying', 'varchar', 'char']:
                    col_def += f"({max_length})"
                elif precision and data_type in ['numeric', 'decimal']:
                    if scale:
                        col_def += f"({precision},{scale})"
                    else:
                        col_def += f"({precision})"
                
                # Add NOT NULL constraint
                if is_nullable == 'NO':
                    col_def += " NOT NULL"
                
                # Add DEFAULT value
                if default:
                    col_def += f" DEFAULT {default}"
                
                column_definitions.append(col_def)
            
            ddl_parts.append(",\n".join(column_definitions))
            ddl_parts.append(");\n")
            
            # Get constraints (primary keys, foreign keys, etc.)
            constraints_query = """
            SELECT
                tc.constraint_name,
                tc.constraint_type,
                string_agg(kcu.column_name, ', ' ORDER BY kcu.ordinal_position) as columns,
                ccu.table_name as foreign_table_name,
                string_agg(ccu.column_name, ', ' ORDER BY kcu.ordinal_position) as foreign_columns
            FROM information_schema.table_constraints tc
            LEFT JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name
            LEFT JOIN information_schema.constraint_column_usage ccu 
                ON tc.constraint_name = ccu.constraint_name
            WHERE tc.table_name = %s AND tc.table_schema = 'public'
            GROUP BY tc.constraint_name, tc.constraint_type, ccu.table_name;
            """
            
            cursor.execute(constraints_query, (table_name,))
            constraints = cursor.fetchall()
            
            for constraint in constraints:
                constraint_name, constraint_type, columns, foreign_table, foreign_columns = constraint
                
                if constraint_type == 'PRIMARY KEY':
                    ddl_parts.append(f"ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} PRIMARY KEY ({columns});\n")
                elif constraint_type == 'FOREIGN KEY' and foreign_table:
                    ddl_parts.append(f"ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} FOREIGN KEY ({columns}) REFERENCES {foreign_table}({foreign_columns});\n")
                elif constraint_type == 'UNIQUE':
                    ddl_parts.append(f"ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} UNIQUE ({columns});\n")
            
            # Get indexes
            indexes_query = """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = %s AND schemaname = 'public'
            AND indexname NOT IN (
                SELECT constraint_name FROM information_schema.table_constraints 
                WHERE table_name = %s AND constraint_type IN ('PRIMARY KEY', 'UNIQUE')
            );
            """
            
            cursor.execute(indexes_query, (table_name, table_name))
            indexes = cursor.fetchall()
            
            for index_name, index_def in indexes:
                ddl_parts.append(f"{index_def};\n")
        
        return "\n".join(ddl_parts)
    
    def get_table_data(self, table_name: str, limit: int = None):
        """Generate INSERT statements for table data"""
        with self.connection.cursor() as cursor:
            # Get column names
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 0")
            column_names = [desc[0] for desc in cursor.description]
            
            # Get data
            query = f"SELECT * FROM {table_name}"
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            insert_statements = []
            insert_statements.append(f"-- DML for table: {table_name}")
            
            for row in rows:
                values = []
                for value in row:
                    if value is None:
                        values.append("NULL")
                    elif isinstance(value, str):
                        # Escape single quotes
                        escaped_value = value.replace("'", "''")
                        values.append(f"'{escaped_value}'")
                    elif isinstance(value, (int, float)):
                        values.append(str(value))
                    else:
                        values.append(f"'{str(value)}'")
                
                columns_str = ", ".join(column_names)
                values_str = ", ".join(values)
                insert_statements.append(f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str});")
            
            return "\n".join(insert_statements) + "\n"
    
    def export_all_schemas(self, output_file: str = "exports/complete_schema.sql"):
        """Export complete database schema"""
        os.makedirs("exports", exist_ok=True)
        
        tables = self.get_all_tables()
        
        with open(output_file, 'w') as f:
            f.write("-- Complete Database Schema Export\n")
            f.write(f"-- Generated from Supabase database\n\n")
            
            for table in tables:
                print(f"📋 Processing table: {table}")
                ddl = self.get_table_ddl(table)
                f.write(ddl)
                f.write("\n" + "="*50 + "\n\n")
        
        print(f"✅ Complete schema exported to {output_file}")
    
    def export_sample_data(self, output_file: str = "exports/sample_data.sql", rows_per_table: int = 100):
        """Export sample data from all tables"""
        os.makedirs("exports", exist_ok=True)
        
        tables = self.get_all_tables()
        
        with open(output_file, 'w') as f:
            f.write("-- Sample Data Export\n")
            f.write(f"-- Limited to {rows_per_table} rows per table\n\n")
            
            for table in tables:
                print(f"📊 Exporting data from: {table}")
                data = self.get_table_data(table, limit=rows_per_table)
                f.write(data)
                f.write("\n" + "="*50 + "\n\n")
        
        print(f"✅ Sample data exported to {output_file}")
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            print("🔌 Database connection closed")

if __name__ == "__main__":
    extractor = SupabaseSchemaExtractor(str(settings.DATABASE_URL))
    
    if extractor.connect():
        print("🗄️  Supabase Schema Extractor")
        print("=" * 40)
        print("1. Export Complete Schema (DDL)")
        print("2. Export Sample Data (DML)")
        print("3. Export Both Schema and Data")
        print("4. List All Tables")
        print("=" * 40)
        
        choice = input("Select option (1-4): ").strip()
        
        try:
            if choice == "1":
                extractor.export_all_schemas()
            elif choice == "2":
                rows = input("Enter rows per table (default 100): ").strip()
                rows_per_table = int(rows) if rows.isdigit() else 100
                extractor.export_sample_data(rows_per_table=rows_per_table)
            elif choice == "3":
                extractor.export_all_schemas()
                rows = input("Enter rows per table for data export (default 100): ").strip()
                rows_per_table = int(rows) if rows.isdigit() else 100
                extractor.export_sample_data(rows_per_table=rows_per_table)
            elif choice == "4":
                tables = extractor.get_all_tables()
                print("\n📋 Tables in database:")
                for i, table in enumerate(tables, 1):
                    print(f"  {i}. {table}")
            else:
                print("❌ Invalid choice")
        
        finally:
            extractor.close()