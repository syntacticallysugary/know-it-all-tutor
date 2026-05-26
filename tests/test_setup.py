"""
Basic setup validation tests
"""
import pytest
import os
from pathlib import Path


def test_project_structure():
    """Test that basic project structure exists"""
    required_dirs = [
        "src/lambda_functions",
        "src/shared",
        "infrastructure",
        "scripts",
    ]
    
    for dir_path in required_dirs:
        assert Path(dir_path).exists(), f"Required directory {dir_path} does not exist"


def test_lambda_functions_exist():
    """Test that all Lambda function directories exist"""
    lambda_functions = [
        "auth",
        "domain_management", 
        "quiz_engine",

        "progress_tracking",
        "batch_upload",
        "db_migration"
    ]
    
    for func in lambda_functions:
        func_path = Path(f"src/lambda_functions/{func}")
        assert func_path.exists(), f"Lambda function directory {func} does not exist"
        
        handler_path = func_path / "handler.py"
        assert handler_path.exists(), f"Handler file for {func} does not exist"


def test_shared_utilities_exist():
    """Test that shared utility modules exist"""
    shared_modules = [
        "database.py",
        "auth_utils.py",
        "config.py",
        "response_utils.py"
    ]
    
    for module in shared_modules:
        module_path = Path(f"src/shared/{module}")
        assert module_path.exists(), f"Shared module {module} does not exist"


def test_infrastructure_files_exist():
    """Test that CDK infrastructure files exist"""
    infra_files = [
        "infrastructure/app.py",

        "cdk.json"
    ]
    
    for file_path in infra_files:
        assert Path(file_path).exists(), f"Infrastructure file {file_path} does not exist"


def test_configuration_files_exist():
    """Test that configuration files exist"""
    config_files = [
        "requirements.txt",
        "src/lambda_functions/requirements.txt",
        "infrastructure/requirements.txt",
        ".env.example",
        "pyproject.toml",
        "pytest.ini",
        ".gitignore",
        "Makefile"
    ]
    
    for file_path in config_files:
        assert Path(file_path).exists(), f"Configuration file {file_path} does not exist"


def test_scripts_exist():
    """Test that deployment and setup scripts exist"""
    scripts = [
        "scripts/setup_environment.py",
        "scripts/deploy.py"
    ]
    
    for script in scripts:
        assert Path(script).exists(), f"Script {script} does not exist"


@pytest.mark.integration
def test_imports_work():
    """Test that basic imports work without errors"""
    try:
        # Test shared module imports
        from src.shared import config, auth_utils, response_utils, database
        
        # Test that classes/functions can be imported
        from src.shared.config import ConfigManager
        from src.shared.auth_utils import hash_password, verify_jwt
        from src.shared.response_utils import create_response
        from src.shared.database import DatabaseManager
        
    except ImportError as e:
        pytest.fail(f"Import error: {e}")


def test_environment_example_has_required_vars():
    """Test that .env.example contains required environment variables"""
    env_example = Path(".env.example")
    assert env_example.exists(), ".env.example file does not exist"
    
    content = env_example.read_text()
    
    required_vars = [
        "ENVIRONMENT",
        "AWS_ACCOUNT_ID",
        "AWS_REGION",
        "AURORA_ENDPOINT",
        "JWT_SECRET",
        "MODEL_PATH"
    ]
    
    for var in required_vars:
        assert var in content, f"Required environment variable {var} not found in .env.example"