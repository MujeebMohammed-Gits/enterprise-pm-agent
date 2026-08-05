# -*- coding: utf-8 -*-
"""
Basic test for the Enterprise PM Agent application
"""
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

def test_imports():
    """Test that we can import the main modules"""
    try:
        from config.settings import settings
        print("[OK] Settings import successful")

        from src.core.workflow.engine import workflow_engine
        print("[OK] Workflow engine import successful")

        from app.main import app
        print("[OK] Main app import successful")

        return True
    except Exception as e:
        print(f"[ERROR] Import failed: {e}")
        return False

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

def test_workflow_engine():
    """Test workflow engine basic functionality"""
    try:
        from src.core.workflow.engine import workflow_engine

        # Check that default workflows are registered
        workflows = workflow_engine.list_workflows()
        assert len(workflows) >= 2, f"Expected at least 2 workflows, got {len(workflows)}"

        # Check for waterfall and scrum workflows
        workflow_names = [wf.name for wf in workflows]
        assert "Waterfall Development" in workflow_names, "Waterfall workflow not found"
        assert "Scrum Development" in workflow_names, "Scrum workflow not found"

        print("[OK] Workflow engine validation successful")
        return True
    except Exception as e:
        print(f"[ERROR] Workflow engine validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("Running Enterprise PM Agent basic tests...\n")

    tests = [
        test_imports,
        test_settings,
        test_workflow_engine
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()  # Blank line between tests

    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("[SUCCESS] All tests passed!")
        return 0
    else:
        print("[ERROR] Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())