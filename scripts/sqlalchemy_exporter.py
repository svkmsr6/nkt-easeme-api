#!/usr/bin/env python3
"""
Export database schema using SQLAlchemy - works with your existing setup
"""
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.schema import CreateTable, CreateIndex
from app.core.config import settings
import os

class SQLAlchemySchemaExporter:
    def __init__(self):
        self.engine = create_engine(str(settings.DATABASE_URL))
        self.metadata = MetaData()
        
    def reflect_database(self):
        """Reflect the database schema"""
        print("🔍 Reflecting database schema...")
        self.metadata.reflect(bind=self.engine)
        print(f"✅ Found {len(self.metadata.tables)} tables")
        
    def export_ddl(self, output_file: str = "exports/sqlalchemy_schema.sql"):
        """Export DDL using SQLAlchemy"""
        os.makedirs("exports", exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("-- Database Schema Export using SQLAlchemy\n")
            f.write("-- Generated from Supabase database\n\n")
            
            # Export table creation statements
            for table_name, table in self.metadata.tables.items():
                f.write(f"-- Table: {table_name}\n")
                create_table_ddl = str(CreateTable(table).compile(self.engine))
                f.write(create_table_ddl)
                f.write(";\n\n")
                
                # Export indexes
                for index in table.indexes:
                    create_index_ddl = str(CreateIndex(index).compile(self.engine))
                    f.write(create_index_ddl)
                    f.write(";\n")
                
                f.write("\n" + "="*50 + "\n\n")
        
        print(f"✅ DDL exported to {output_file}")
    
    def export_table_data(self, table_name: str, limit: int = None):
        """Export data from a specific table"""
        if table_name not in self.metadata.tables:
            print(f"❌ Table '{table_name}' not found")
            return ""
        
        table = self.metadata.tables[table_name]
        
        with self.engine.connect() as conn:
            # Build SELECT query
            query = f"SELECT * FROM {table_name}"
            if limit:
                query += f" LIMIT {limit}"
            
            result = conn.execute(text(query))
            rows = result.fetchall()
            
            if not rows:
                return f"-- No data in table: {table_name}\n"
            
            # Generate INSERT statements
            insert_statements = [f"-- Data for table: {table_name}"]
            
            column_names = [col.name for col in table.columns]
            columns_str = ", ".join(column_names)
            
            for row in rows:
                values = []
                for value in row:
                    if value is None:
                        values.append("NULL")
                    elif isinstance(value, str):
                        escaped_value = value.replace("'", "''")
                        values.append(f"'{escaped_value}'")
                    elif isinstance(value, (int, float, bool)):
                        values.append(str(value))
                    else:
                        values.append(f"'{str(value)}'")
                
                values_str = ", ".join(values)
                insert_statements.append(f"INSERT INTO {table_name} ({columns_str}) VALUES ({values_str});")
            
            return "\n".join(insert_statements) + "\n"
    
    def export_all_data(self, output_file: str = "exports/sqlalchemy_data.sql", rows_per_table: int = 100):
        """Export data from all tables"""
        os.makedirs("exports", exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("-- Database Data Export using SQLAlchemy\n")
            f.write(f"-- Limited to {rows_per_table} rows per table\n\n")
            
            for table_name in self.metadata.tables.keys():
                print(f"📊 Exporting data from: {table_name}")
                data = self.export_table_data(table_name, limit=rows_per_table)
                f.write(data)
                f.write("\n" + "="*50 + "\n\n")
        
        print(f"✅ Data exported to {output_file}")
    
    def list_tables(self):
        """List all tables in the database"""
        print("\n📋 Tables in database:")
        for i, table_name in enumerate(self.metadata.tables.keys(), 1):
            table = self.metadata.tables[table_name]
            column_count = len(table.columns)
            print(f"  {i}. {table_name} ({column_count} columns)")
    
    def get_table_info(self, table_name: str):
        """Get detailed information about a specific table"""
        if table_name not in self.metadata.tables:
            print(f"❌ Table '{table_name}' not found")
            return
        
        table = self.metadata.tables[table_name]
        
        print(f"\n📋 Table: {table_name}")
        print("-" * 40)
        print("Columns:")
        for col in table.columns:
            nullable = "NULL" if col.nullable else "NOT NULL"
            default = f" DEFAULT {col.default}" if col.default else ""
            print(f"  - {col.name}: {col.type} {nullable}{default}")
        
        if table.primary_key.columns:
            pk_columns = [col.name for col in table.primary_key.columns]
            print(f"\nPrimary Key: {', '.join(pk_columns)}")
        
        if table.foreign_keys:
            print("\nForeign Keys:")
            for fk in table.foreign_keys:
                print(f"  - {fk.parent.name} -> {fk.column.table.name}.{fk.column.name}")
        
        if table.indexes:
            print("\nIndexes:")
            for idx in table.indexes:
                columns = [col.name for col in idx.columns]
                unique = "UNIQUE " if idx.unique else ""
                print(f"  - {unique}{idx.name}: {', '.join(columns)}")

if __name__ == "__main__":
    exporter = SQLAlchemySchemaExporter()
    exporter.reflect_database()
    
    print("🗄️  SQLAlchemy Schema Exporter")
    print("=" * 40)
    print("1. Export Schema (DDL)")
    print("2. Export Data (DML)")
    print("3. Export Both Schema and Data")
    print("4. List All Tables")
    print("5. Get Table Info")
    print("=" * 40)
    
    choice = input("Select option (1-5): ").strip()
    
    if choice == "1":
        exporter.export_ddl()
    elif choice == "2":
        rows = input("Enter rows per table (default 100): ").strip()
        rows_per_table = int(rows) if rows.isdigit() else 100
        exporter.export_all_data(rows_per_table=rows_per_table)
    elif choice == "3":
        exporter.export_ddl()
        rows = input("Enter rows per table for data export (default 100): ").strip()
        rows_per_table = int(rows) if rows.isdigit() else 100
        exporter.export_all_data(rows_per_table=rows_per_table)
    elif choice == "4":
        exporter.list_tables()
    elif choice == "5":
        table_name = input("Enter table name: ").strip()
        if table_name:
            exporter.get_table_info(table_name)
    else:
        print("❌ Invalid choice")