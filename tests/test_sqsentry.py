import pytest
import logging
import json
from unittest.mock import patch, MagicMock

# Assuming the path structure: tests/ -> src/external_secrets_reloader/entries/sqsentry.py
from external_secrets_reloader.entries.sqsentry import SQSEntry

# --- Test Data ---

# A mock SQS message record dictionary
# Note: The 'Body' field is a string, which usually contains JSON if configured.
MOCK_SQS_ENTRY_DICT = {
    "messageId": "19b7ac81-817e-40cc-9993-e574d6b5e05d",
    "receiptHandle": "AQEB5wT2Yg...",
    "body": '{"key": "value", "data": "payload"}', # Body usually contains the actual event data as a string
    "attributes": {
        "ApproximateReceiveCount": "1",
        "SentTimestamp": "1678886400000",
        "SenderId": "AIDAJ7C...",
        "ApproximateFirstReceiveTimestamp": "1678886400000"
    },
    "messageAttributes": {},
    "md5OfBody": "4e73dd29497e5b61e05d7b5391d1c4f5",
    "eventSource": "aws:sqs",
    "eventSourceARN": "arn:aws:sqs:us-east-1:123456789012:MyQueue",
    "awsRegion": "us-east-1"
}

# SQS uses 'Body' (capital B) in the record structure when retrieved from the queue
MOCK_SQS_ENTRY_WITH_CAPITAL_BODY = {
    "MessageId": "19b7ac81-817e-40cc-9993-e574d6b5e05d",
    "ReceiptHandle": "AQEB5wT2Yg...",
    "Body": '{"key": "value", "data": "payload"}',
    # ... other fields
}

# --- Fixtures ---

@pytest.fixture
def mock_sqs_entry_instance():
    """Provides a fresh instance of SQSEntry for testing using the standard SQS format."""
    return SQSEntry(MOCK_SQS_ENTRY_WITH_CAPITAL_BODY)

# --- Tests ---

def test_sqsentry_initialization():
    """Tests the __init__ method for correct attribute assignment and logger setup."""
    
    # 1. Test initialization and attribute assignment
    entry = SQSEntry(MOCK_SQS_ENTRY_DICT)
    assert entry.entry == MOCK_SQS_ENTRY_DICT
    assert isinstance(entry.entry, dict)
    
    # 2. Check for logger initialization
    with patch('logging.getLogger', autospec=True) as mock_get_logger:
        SQSEntry(MOCK_SQS_ENTRY_DICT)
        mock_get_logger.assert_called_once_with('SQSEntry')

def test_sqsentry_get_message_body(mock_sqs_entry_instance):
    """Tests the get_message_body method for correct extraction."""
    expected_body = MOCK_SQS_ENTRY_WITH_CAPITAL_BODY['Body']
    assert mock_sqs_entry_instance.get_message_body() == expected_body
    assert isinstance(mock_sqs_entry_instance.get_message_body(), str)
    
def test_sqsentry_handle_missing_body_key():
    """Tests that a KeyError is raised if the 'Body' key is missing in the entry."""
    
    entry_without_body = {
        "MessageId": "12345",
        "ReceiptHandle": "abcde"
        # 'Body' is missing
    }
    
    entry_instance = SQSEntry(entry_without_body)
    
    with pytest.raises(KeyError):
        entry_instance.get_message_body()

def test_sqsentry_body_case_sensitivity():
    """Tests that the method correctly uses 'Body' (capital B) as expected by the SQS structure."""
    
    # Test case with lowercase 'body' (should fail to find the body)
    entry_with_lowercase_body = {
        "MessageId": "123",
        "body": "this is lowercase"
    }
    
    entry_instance = SQSEntry(entry_with_lowercase_body)
    
    with pytest.raises(KeyError):
        # We expect this to fail because SQS returns 'Body', not 'body'
        entry_instance.get_message_body()
    
    # Sanity check against the expected key
    assert 'Body' not in entry_with_lowercase_body