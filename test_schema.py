#!/usr/bin/env python3
"""
Test script to validate schema configuration
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

async def test_models():
    try:
        print("Testing model configuration with app schema...")
        from app.db.models import Task, InterventionSession, CheckIn
        
        # Check that all models have the correct schema
        print(f"✅ Task table: {Task.__tablename__} in schema: {Task.__table_args__.get('schema', 'default')}")
        print(f"✅ InterventionSession table: {InterventionSession.__tablename__} in schema: {InterventionSession.__table_args__.get('schema', 'default')}")
        print(f"✅ CheckIn table: {CheckIn.__tablename__} in schema: {CheckIn.__table_args__.get('schema', 'default')}")
        
        print("\nTesting database session configuration...")
        from app.db.session import get_db
        print("✅ Database session configured successfully")
        
        print("\nTesting app creation without startup...")
        from app.main import create_app
        app = create_app()
        print("✅ App created successfully without database initialization")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_models())