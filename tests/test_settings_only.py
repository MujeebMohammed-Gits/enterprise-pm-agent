# -*- coding: utf-8 -*-
"""
Test just the settings function
"""
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

def test_settings():
    """Test settings configuration"""
    try:
        from config.settings import settings

        print(f"app_name: {settings.app_name}")
        print(f"app_version: {settings.app_version}")
        print(f"app_env: {settings.app_env}")
        print(f"debug: {settings.debug}")

        assert settings.app_name == "Enterprise PM Agent"
        assert settings.app_version == "1.0.0"
        assert settings.app_env == "development"
        assert settings.debug == False  # Default value from Field

        print("[OK] Settings validation successful")
        return True
    except Exception as e:
        print(f"[ERROR] Settings validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_settings()