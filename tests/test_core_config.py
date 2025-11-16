"""
Unit tests for app.core.config module.
"""
import pytest
from pydantic import ValidationError
from app.core.config import Settings


class TestSettings:
    """Test Settings configuration."""
    
    def test_settings_loads_from_env(self):
        """Test that settings can be loaded."""
        from app.core.config import settings
        
        assert settings.APP_NAME in ["EaseMe API", "NKT_EaseMe_API"]
        assert hasattr(settings, "DATABASE_URL")
        assert hasattr(settings, "SUPABASE_URL")
        assert hasattr(settings, "OPENAI_API_KEY")
    
    def test_settings_defaults(self):
        """Test default values in settings."""
        from app.core.config import settings
        
        assert settings.OPENAI_MODEL == "gpt-4o-mini"
        assert settings.OPENAI_TEMPERATURE == 0.4
        assert settings.JWT_AUDIENCE == "authenticated"
    
    def test_settings_env_override(self, monkeypatch):
        """Test that environment variables override defaults."""
        monkeypatch.setenv("APP_NAME", "Test API")
        monkeypatch.setenv("OPENAI_TEMPERATURE", "0.7")
        
        # Force reload
        test_settings = Settings(_env_file=".env")
        
        assert test_settings.APP_NAME == "Test API"
        assert test_settings.OPENAI_TEMPERATURE == 0.7
    
    def test_required_fields(self, monkeypatch):
        """Test that required fields must be present."""
        # Clear required env vars
        monkeypatch.delenv("DATABASE_URL", raising=False)
        
        with pytest.raises(ValidationError):
            Settings(_env_file=None)
