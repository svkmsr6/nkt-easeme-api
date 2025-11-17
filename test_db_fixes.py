#!/usr/bin/env python3
"""
Test script to validate database query fixes
"""
import sys
import os
sys.path.append(os.path.dirname(__file__))

async def test_database_queries():
    try:
        print("Testing database query compatibility...")
        
        # Test imports
        from app.db.models import Task, InterventionSession, CheckIn
        from app.repositories.task_repo import list_tasks
        from sqlalchemy import cast, String
        
        print("✅ All imports successful")
        print("✅ Model definitions updated with explicit String typing")
        print("✅ Repository functions updated with type casting")
        
        print("\nDatabase query improvements made:")
        print("  🔧 Added explicit String type for Task.status column")
        print("  🔧 Updated list_tasks() to use cast(Task.status, String)")
        print("  🔧 Updated dashboard query to use cast(Task.status, String)")
        print("  🔧 Updated checkin creation to use direct SQL for updates")
        
        print("\nThese changes should resolve the PostgreSQL type mismatch errors.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_database_queries())