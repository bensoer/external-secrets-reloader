import pytest
from unittest.mock import MagicMock

# --- Update these imports based on your exact file names ---
# Assuming EventBridgeProcessor is defined here:
from external_secrets_reloader.processors.eventbridge_processor import EventBridgeProcessor

# Assuming entries are defined here (needed for type checking/mocking return values):
from external_secrets_reloader.entries.eventbridgeentry import EventBridgeEntry
# SQSEntry doesn't need to be imported if we mock it completely, but useful for context
# from external_secrets_reloader.entries.sqsentry import SQSEntry 
# -----------------------------------------------------------

# --- Fixtures ---

@pytest.fixture
def mock_sqs_entry(mocker):
    """Fixture to mock the SQSEntry object."""
    mock_entry = mocker.MagicMock()
    # Ensure get_message_body returns a known string
    mock_entry.get_message_body.return_value = '{"source": "aws.s3", "detail": {"key": "my/secret/key"}}'
    return mock_entry

@pytest.fixture
def mock_source_processor(mocker, mock_sqs_entry):
    """Fixture to mock the underlying SQS Processor."""
    mock_source = mocker.MagicMock()
    
    # Default successful behavior: load_next_entry returns True, get_entry returns the mock SQS entry
    mock_source.load_next_entry.return_value = True
    mock_source.get_entry.return_value = mock_sqs_entry
    return mock_source

@pytest.fixture
def processor_instance(mock_source_processor):
    """Fixture to create the EventBridgeProcessor instance."""
    return EventBridgeProcessor(source=mock_source_processor)

# --- Tests for Initialization and Properties ---

def test_initialization(processor_instance, mock_source_processor):
    """Test that the processor initializes correctly and sets the source."""
    assert processor_instance.source == mock_source_processor
    assert processor_instance.raw_content == ""
    assert isinstance(processor_instance, EventBridgeProcessor)

# --- Tests for load_next_entry ---

def test_load_next_entry_success(processor_instance, mock_source_processor, mock_sqs_entry):
    """Test successful loading of the next entry."""
    
    # Act
    result = processor_instance.load_next_entry()
    
    # Assert
    assert result is True
    
    # Verify interaction with the source
    mock_source_processor.load_next_entry.assert_called_once()
    mock_source_processor.get_entry.assert_called_once()
    mock_sqs_entry.get_message_body.assert_called_once()
    
    # Verify internal state update
    expected_content = '{"source": "aws.s3", "detail": {"key": "my/secret/key"}}'
    assert processor_instance.raw_content == expected_content

def test_load_next_entry_source_failure(processor_instance, mock_source_processor):
    """Test failure when the source processor cannot load the next entry."""
    
    # Arrange: Source load fails
    mock_source_processor.load_next_entry.return_value = False
    
    # Act
    result = processor_instance.load_next_entry()
    
    # Assert
    assert result is False
    mock_source_processor.load_next_entry.assert_called_once()
    # These should not be called if the load_next_entry failed
    mock_source_processor.get_entry.assert_not_called()
    assert processor_instance.raw_content == "" # Should remain empty

def test_load_next_entry_exception_during_load(processor_instance, mock_source_processor):
    """Test exception handling during the load_next_entry call."""
    
    # Arrange: Source load raises an exception
    mock_source_processor.load_next_entry.side_effect = Exception("SQS Connection Error")
    
    # Act
    result = processor_instance.load_next_entry()
    
    # Assert
    assert result is False
    mock_source_processor.load_next_entry.assert_called_once()

def test_load_next_entry_exception_during_get_entry(processor_instance, mock_source_processor):
    """Test exception handling during the get_entry call."""
    
    # Arrange: get_entry raises an exception (e.g., source entry is corrupt)
    mock_source_processor.get_entry.side_effect = Exception("Corrupt SQS Entry")
    
    # Act
    result = processor_instance.load_next_entry()
    
    # Assert
    assert result is False
    mock_source_processor.load_next_entry.assert_called_once()
    mock_source_processor.get_entry.assert_called_once()

# --- Tests for mark_entry_resolved ---

def test_mark_entry_resolved_calls_source(processor_instance, mock_source_processor):
    """Test that marking an entry resolved delegates the call to the source processor."""
    
    # Act
    processor_instance.mark_entry_resolved()
    
    # Assert
    mock_source_processor.mark_entry_resolved.assert_called_once()

# --- Tests for get_entry ---

def test_get_entry_returns_eventbridge_entry(processor_instance, mocker):
    """Test that get_entry returns an EventBridgeEntry instance constructed with the correct content."""
    
    # ARRANGE 1: Mock the EventBridgeEntry class itself
    # We patch the class where it's looked up (inside the EventBridgeProcessor module)
    mock_eb_entry_cls = mocker.patch(
        'external_secrets_reloader.processors.eventbridge_processor.EventBridgeEntry'
    )
    
    # ARRANGE 2: Manually set raw_content
    expected_content = '{"id": "abc-123", "detail-type": "Object Created"}'
    processor_instance.raw_content = expected_content
    
    # ACT
    entry = processor_instance.get_entry()
    
    # ASSERT 1: Verify the class was called correctly
    # Check that the mock class constructor was called exactly once with the expected content
    mock_eb_entry_cls.assert_called_once_with(expected_content)
    
    # ASSERT 2: Verify the return value is the result of the mocked constructor call
    # The 'entry' variable should be the mock object returned by the mocked constructor
    assert entry == mock_eb_entry_cls.return_value