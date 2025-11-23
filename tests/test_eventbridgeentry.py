import pytest
import json
import logging
from unittest.mock import patch, MagicMock

# Assuming the path structure: tests/ -> src/external_secrets_reloader/entries/eventbridgeentry.py
from external_secrets_reloader.entries.eventbridgeentry import EventBridgeEntry

# --- Test Data ---

# Example EventBridge entry for a secret
MOCK_EVENTBRIDGE_ENTRY_STR = """
{
    "version": "0",
    "id": "12345678-abcd-1234-abcd-1234567890ab",
    "detail-type": "External Secrets Secret Synchronization",
    "source": "external-secrets.io",
    "account": "123456789012",
    "time": "2023-11-23T18:00:00Z",
    "region": "us-east-1",
    "resources": [
        "arn:aws:s3:::some-bucket/path/to/resource"
    ],
    "detail": {
        "namespace": "default",
        "name": "my-external-secret-1",
        "operation": "update",
        "status": "Success",
        "message": "Secret data updated successfully"
    }
}
"""

MOCK_EVENTBRIDGE_ENTRY_DICT = json.loads(MOCK_EVENTBRIDGE_ENTRY_STR)

# --- Fixtures ---

@pytest.fixture
def mock_eventbridge_entry_instance():
    """Provides a fresh instance of EventBridgeEntry for testing."""
    return EventBridgeEntry(MOCK_EVENTBRIDGE_ENTRY_STR)

# --- Tests ---

def test_eventbridgeentry_initialization(mock_eventbridge_entry_instance):
    """Tests the __init__ method for correct attribute assignment and JSON loading."""
    entry = mock_eventbridge_entry_instance
    
    # Check if raw_entry is stored correctly
    assert entry.raw_entry == MOCK_EVENTBRIDGE_ENTRY_STR
    
    # Check if entry is correctly loaded as a dictionary
    assert isinstance(entry.entry, dict)
    assert entry.entry == MOCK_EVENTBRIDGE_ENTRY_DICT
    
    # Check for logger initialization (using MagicMock to prevent actual log output in test)
    with patch('logging.getLogger', autospec=True) as mock_get_logger:
        EventBridgeEntry(MOCK_EVENTBRIDGE_ENTRY_STR)
        mock_get_logger.assert_called_once_with('EventBridgeEntry')

def test_eventbridgeentry_get_resources(mock_eventbridge_entry_instance):
    """Tests the get_resources method."""
    expected_resources = MOCK_EVENTBRIDGE_ENTRY_DICT["resources"]
    assert mock_eventbridge_entry_instance.get_resources() == expected_resources

def test_eventbridgeentry_get_name(mock_eventbridge_entry_instance):
    """Tests the get_name method."""
    expected_name = MOCK_EVENTBRIDGE_ENTRY_DICT["detail"]["name"]
    assert mock_eventbridge_entry_instance.get_name() == expected_name

def test_eventbridgeentry_get_operation(mock_eventbridge_entry_instance):
    """Tests the get_operation method."""
    expected_operation = MOCK_EVENTBRIDGE_ENTRY_DICT["detail"]["operation"]
    assert mock_eventbridge_entry_instance.get_operation() == expected_operation

def test_eventbridgeentry_get_key(mock_eventbridge_entry_instance):
    """Tests the get_key method (which should return the same as get_name)."""
    expected_key = MOCK_EVENTBRIDGE_ENTRY_DICT["detail"]["name"]
    assert mock_eventbridge_entry_instance.get_key() == expected_key

@pytest.mark.parametrize("missing_key", ["resources", "detail", "detail.name", "detail.operation"])
def test_eventbridgeentry_handle_missing_keys(missing_key):
    """Tests that methods raise KeyError when expected keys are missing."""
    
    # Create a broken entry structure
    broken_dict = json.loads(MOCK_EVENTBRIDGE_ENTRY_STR)
    
    if missing_key == "resources":
        del broken_dict["resources"]
    elif missing_key == "detail":
        del broken_dict["detail"]
    elif missing_key.startswith("detail."):
        key_to_remove = missing_key.split(".")[1]
        del broken_dict["detail"][key_to_remove]
    
    broken_entry_str = json.dumps(broken_dict)
    entry = EventBridgeEntry(broken_entry_str)
    
    # Determine which method call should raise the error
    with pytest.raises(KeyError):
        if missing_key == "resources":
            entry.get_resources()
        elif missing_key == "detail.name" or missing_key == "detail" or missing_key == "detail.operation":
            # Testing get_name and get_key first, as they rely on "detail" and "detail.name"
            if missing_key != "detail.operation":
                entry.get_name()
            else:
                entry.get_operation()

def test_eventbridgeentry_invalid_json():
    """Tests initialization failure when the input string is invalid JSON."""
    invalid_json_str = "{'key': 'value'"
    
    with pytest.raises(json.JSONDecodeError):
        EventBridgeEntry(invalid_json_str)