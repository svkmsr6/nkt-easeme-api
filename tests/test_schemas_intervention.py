"""
Unit tests for app.schemas.intervention module.
"""
import pytest
from pydantic import ValidationError
from app.schemas.intervention import CheckinTimePatchIn


class TestCheckinTimePatchIn:
    """Test CheckinTimePatchIn schema validation."""
    
    def test_valid_checkin_minutes(self):
        """Test valid checkin minutes values."""
        # Test minimum
        schema = CheckinTimePatchIn(checkin_minutes=15)
        assert schema.checkin_minutes == 15
        
        # Test maximum
        schema = CheckinTimePatchIn(checkin_minutes=120)
        assert schema.checkin_minutes == 120
        
        # Test middle value
        schema = CheckinTimePatchIn(checkin_minutes=60)
        assert schema.checkin_minutes == 60
    
    def test_below_minimum_fails(self):
        """Test that values below 15 fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            CheckinTimePatchIn(checkin_minutes=14)
        
        errors = exc_info.value.errors()
        assert len(errors) > 0
        assert "checkin_minutes" in str(errors[0])
    
    def test_above_maximum_fails(self):
        """Test that values above 120 fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            CheckinTimePatchIn(checkin_minutes=121)
        
        errors = exc_info.value.errors()
        assert len(errors) > 0
        assert "checkin_minutes" in str(errors[0])
