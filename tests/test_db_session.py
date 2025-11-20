"""
Unit tests for app.db.session module.
"""
import pytest
from app.db.session import SessionLocal, get_db, engine


class TestSession:
    """Test database session creation and management."""
    
    def test_sessionlocal_exists(self):
        """Test that SessionLocal is properly configured."""
        assert SessionLocal is not None
        assert hasattr(SessionLocal, '__call__')
    
    def test_engine_exists(self):
        """Test that engine is created."""
        assert engine is not None
    
    def test_get_db_generator(self):
        """Test that get_db is a generator."""
        db_gen = get_db()
        
        # Verify it's a generator
        assert hasattr(db_gen, '__next__')
        
        # Get session
        session = next(db_gen)
        
        # Verify it's a session
        assert session is not None
        
        # Close properly
        try:
            next(db_gen)
        except StopIteration:
            pass  # Expected when generator finishes
