import pytest
import os # Necessary for environment manipulation in the fixture
from unittest.mock import patch
from pydantic import ValidationError

# Import the class under test
from external_secrets_reloader.settings import Settings

# Define a baseline set of valid required environment variables
VALID_ENV = {
    "EVENT_SOURCE": "AWS",
    "EVENT_SERVICE": "SecretsManager",
    "SQS_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
}

# --- Fixtures ---

@pytest.fixture(autouse=True)
def cleanup_env():
    """
    Fixture to temporarily save relevant environment variables before each test
    and restore them after, ensuring test isolation.
    """
    keys_to_manage = [
        "SQS_QUEUE_URL", "SQS_QUEUE_WAIT_TIME", "EVENT_SOURCE", 
        "EVENT_SERVICE", "HEALTH_CHECK_PORT", "LOG_LEVEL"
    ]
    
    # 1. Save the original values of the keys we intend to test/clear
    original_values = {}
    for key in keys_to_manage:
        if key in os.environ:
            original_values[key] = os.environ[key]
            # 2. Clear the env var before the test runs (ensures a clean slate)
            del os.environ[key] 

    # 3. Yield to run the test
    yield

    # 4. Teardown: Restore the original environment variables
    # First, clear any new keys/values the test might have set
    for key in keys_to_manage:
        if key in os.environ:
            del os.environ[key] 
            
    # Then, restore the saved original values
    for key, value in original_values.items():
        os.environ[key] = value 

# --- Helper Functions ---

def load_settings_with_env(env_vars: dict) -> Settings:
    """
    Helper function to load the Settings model by patching the environment.
    """
    # Use patch.dict for reliable temporary setting of env vars for the duration of the call
    with patch.dict('os.environ', env_vars): 
        return Settings()

# --------------------------------------------------------------------------------------
## 🧪 Tests for Successful Initialization and Defaults
# --------------------------------------------------------------------------------------

def test_settings_load_successfully_with_required_aws_fields():
    """Tests the settings model loads correctly with valid required AWS fields."""
    settings = load_settings_with_env(VALID_ENV)
    
    # Assert values are set correctly
    assert settings.EVENT_SOURCE == "AWS"
    assert settings.EVENT_SERVICE == "SecretsManager"
    assert settings.SQS_QUEUE_URL == VALID_ENV["SQS_QUEUE_URL"]
    
    # Assert default values are used
    assert settings.SQS_QUEUE_WAIT_TIME == 10
    assert settings.HEALTH_CHECK_PORT == 8080
    assert settings.LOG_LEVEL == "INFO"

def test_settings_overriding_default_values():
    """Tests that optional fields can be correctly overridden via environment variables."""
    custom_env = VALID_ENV.copy()
    custom_env.update({
        "SQS_QUEUE_WAIT_TIME": "30",
        "HEALTH_CHECK_PORT": "9000",
        "LOG_LEVEL": "DEBUG"
    })
    
    settings = load_settings_with_env(custom_env)
    
    assert settings.SQS_QUEUE_WAIT_TIME == 30
    assert settings.HEALTH_CHECK_PORT == 9000
    assert settings.LOG_LEVEL == "DEBUG"

# --------------------------------------------------------------------------------------
## 🧪 Tests for Pydantic Field Validation
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("invalid_wait_time", [0, 61, -1])
def test_validation_sqs_queue_wait_time_limits(invalid_wait_time):
    """Tests validation for SQS_QUEUE_WAIT_TIME (gt=0, le=60)."""
    invalid_env = VALID_ENV.copy()
    invalid_env["SQS_QUEUE_WAIT_TIME"] = str(invalid_wait_time)
    
    with pytest.raises(ValidationError) as exc_info:
        load_settings_with_env(invalid_env)
    
    assert "SQS_QUEUE_WAIT_TIME" in str(exc_info.value)

@pytest.mark.parametrize("invalid_port", [1023, 65535, 70000])
def test_validation_health_check_port_limits(invalid_port):
    """Tests validation for HEALTH_CHECK_PORT (ge=1024, lt=65535)."""
    invalid_env = VALID_ENV.copy()
    invalid_env["HEALTH_CHECK_PORT"] = str(invalid_port)
    
    with pytest.raises(ValidationError) as exc_info:
        load_settings_with_env(invalid_env)
        
    assert "HEALTH_CHECK_PORT" in str(exc_info.value)


# --------------------------------------------------------------------------------------
## 🧪 Tests for Custom model_validator Validation (validate_cloud_dependencies)
# --------------------------------------------------------------------------------------

def test_validator_aws_valid_secretsmanager():
    """Ensures the validator passes with EVENT_SERVICE='SecretsManager'."""
    settings = load_settings_with_env(VALID_ENV)
    assert settings.EVENT_SERVICE == "SecretsManager"
    
def test_validator_aws_valid_parameterstore():
    """Ensures the validator passes with EVENT_SERVICE='ParameterStore'."""
    valid_env_ssm = VALID_ENV.copy()
    valid_env_ssm["EVENT_SERVICE"] = "ParameterStore"
    
    settings = load_settings_with_env(valid_env_ssm)
    assert settings.EVENT_SERVICE == "ParameterStore"

'''
Does not work because we don't have more options then ones that are valid for AWS
def test_validator_aws_invalid_event_service():
    """Tests the validator raises ValueError when EVENT_SERVICE is invalid for AWS."""
    invalid_env = VALID_ENV.copy()
    invalid_env["EVENT_SERVICE"] = "KMS"  # Invalid service for AWS source
    
    with pytest.raises(ValueError) as exc_info:
        load_settings_with_env(invalid_env)
        
    assert "is invalid for EVENT_SOURCE='AWS'" in str(exc_info.value)
    assert "KMS" in str(exc_info.value)
'''

def test_validator_aws_missing_sqs_queue_url():
    """Tests the validator raises ValueError when SQS_QUEUE_URL is missing for AWS."""
    invalid_env = VALID_ENV.copy()
    del invalid_env["SQS_QUEUE_URL"]  # Remove the required field
    
    with pytest.raises(ValueError) as exc_info:
        load_settings_with_env(invalid_env)
        
    assert "SQS_QUEUE_URL is required when EVENT_CLOUD='AWS'." in str(exc_info.value)