"""
Test configuration loading
"""
import os
from config.settings import Settings

def test_settings_loading():
    """Test that settings load correctly from environment and defaults"""
    # Set test environment variables
    os.environ["APP_NAME"] = "Test PM Agent"
    os.environ["APP_ENV"] = "testing"
    os.environ["DEBUG"] = "true"
    os.environ["PORT"] = "8080"

    # Create settings instance
    settings = Settings()

    # Test that values are loaded correctly
    assert settings.app_name == "Test PM Agent"
    assert settings.app_env == "testing"
    assert settings.debug == True
    assert settings.port == 8080

    # Test nested settings
    assert isinstance(settings.database, Settings.DatabaseSettings, DatabaseSettings)
    assert isinstance(settings.redis, RedisSettings)

    # Test computed properties
    assert settings.is_testing == True
    assert settings.is_development == False
    assert settings.is_production == False

    print("✅ Settings test passed!")

if __name__ == "__main__":
    test_settings_loading()