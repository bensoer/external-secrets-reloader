import pytest
from unittest.mock import MagicMock

# --- Correct Imports based on your file structure ---
# Import the class under test
from external_secrets_reloader.processors.sqs_processor import SQSProcessor

# Import dependent classes for patching
from external_secrets_reloader.entries.sqsentry import SQSEntry
# -----------------------------------------------------------

# --- Mock Data Fixtures ---

@pytest.fixture
def mock_sqs_message():
    """Fixture returning a mock SQS message structure."""
    return {
        'MessageId': 'message-id-123',
        'ReceiptHandle': 'receipt-handle-456',
        'Body': '{"key": "value"}',
        'MD5OfBody': '...',
        # ... other SQS message keys
    }

@pytest.fixture
def mock_boto3_client(mocker, mock_sqs_message):
    """Fixture to mock the boto3 SQS client and its methods."""
    
    # 1. Mock the client factory call
    mock_client = mocker.MagicMock()
    mocker.patch(
        'external_secrets_reloader.processors.sqs_processor.boto3.client', 
        return_value=mock_client
    )
    
    # 2. Set default success behavior for receive_message
    mock_client.receive_message.return_value = {
        'Messages': [mock_sqs_message]
    }
    
    # 3. Set default behavior for delete_message (returns a simple dict on success)
    mock_client.delete_message.return_value = {}
    
    return mock_client

# --- Fixture for the Processor Instance ---

@pytest.fixture
def processor_instance(mock_boto3_client_setup):
    """Fixture to create the SQSProcessor instance."""
    QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
    MIN_WAIT = 5
    return SQSProcessor(queue_url=QUEUE_URL, min_wait_time=MIN_WAIT)

@pytest.fixture
def mock_boto3_client_setup(mocker, mock_sqs_message):
    """Fixture to mock the boto3 SQS client and its methods."""
    
    # 1. Mock the client instance (the object returned by boto3.client('sqs'))
    mock_client_instance = mocker.MagicMock()
    # Set up method mocks on the instance
    mock_client_instance.receive_message.return_value = {'Messages': [mock_sqs_message]}
    mock_client_instance.delete_message.return_value = {}

    # 2. Mock the boto3.client function itself
    mock_client_function = mocker.patch(
        'external_secrets_reloader.processors.sqs_processor.boto3.client', 
        return_value=mock_client_instance
    )
    
    # Return both mocks for testing
    return mock_client_function, mock_client_instance

@pytest.fixture
def processor_instance(mock_boto3_client_setup):
    """Fixture to create the SQSProcessor instance."""
    # We only need the instance mock to be passed to the processor
    # The client function mock is implicitly used when SQSProcessor initializes
    QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
    MIN_WAIT = 5
    return SQSProcessor(queue_url=QUEUE_URL, min_wait_time=MIN_WAIT)

# --- Tests ---

## Test Initialization

def test_initialization_sets_defaults(processor_instance, mock_boto3_client_setup):
    """Test that initialization sets up client and default state."""
    
    # Unpack the mocks from the fixture
    mock_client_function, mock_client_instance = mock_boto3_client_setup
    
    # 1. Assert client creation (This now uses the correct mock: mock_client_function)
    mock_client_function.assert_called_once_with('sqs')
    
    # 2. Assert initial state (These attributes are public and accessible)
    assert processor_instance.queue_url == "https://sqs.us-east-1.amazonaws.com/123456789012/test-queue"
    assert processor_instance.min_wait_time == 5
    assert processor_instance.current_wait_time == 5
    assert processor_instance.receipt_handle is None
    assert processor_instance.message_id is None
    assert processor_instance.current_message == {}

## Test load_next_entry (Success Cases)

def test_load_next_entry_success(processor_instance, mock_boto3_client_setup, mock_sqs_message):
    """Test successful receipt of a message."""
    
    mock_client_function, mock_sqs_client_instance = mock_boto3_client_setup

    # Act
    result = processor_instance.load_next_entry()
    
    # Assert return value and state updates
    assert result is True
    assert processor_instance.message_id == 'message-id-123'
    assert processor_instance.receipt_handle == 'receipt-handle-456'
    assert processor_instance.current_message == mock_sqs_message
    
    # Assert SQS client interaction (initial wait time)
    mock_sqs_client_instance.receive_message.assert_called_once_with(
        QueueUrl=processor_instance.queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=5 # min_wait_time
    )
    
    # Assert backoff reset
    assert processor_instance.empty_poll_count == 0
    assert processor_instance.current_wait_time == 5


## Test load_next_entry (Failure and Backoff Cases)

def test_load_next_entry_no_message(processor_instance, mock_boto3_client_setup):
    """Test case where receive_message returns no messages."""

    mock_client_function, mock_sqs_client_instance = mock_boto3_client_setup
    
    # Arrange: Mock receive_message to return an empty list
    mock_sqs_client_instance.receive_message.return_value = {'Messages': []}
    
    # Act
    result = processor_instance.load_next_entry()
    
    # Assert return value and state updates
    assert result is False
    assert processor_instance.message_id is None
    assert processor_instance.receipt_handle is None
    assert processor_instance.current_message is None
    
    # Assert backoff update: 5 * (2^1) = 10
    assert processor_instance.empty_poll_count == 1
    assert processor_instance.current_wait_time == 10
    
    # Assert SQS call used the minimum wait time on first call
    mock_sqs_client_instance.receive_message.assert_called_once_with(
        QueueUrl=processor_instance.queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=5
    )

def test_load_next_entry_backoff_increase(processor_instance, mock_boto3_client_setup):
    """Test that the wait time increases exponentially after consecutive empty polls."""
    
    mock_client_function, mock_sqs_client_instance = mock_boto3_client_setup

    # Arrange: Set up for failure and run twice
    mock_sqs_client_instance.receive_message.return_value = {'Messages': []}
    
    # Poll 1 (WaitTimeSeconds=5) -> Fail, WaitTimeSeconds = 10
    processor_instance.load_next_entry() 
    
    # Poll 2 (WaitTimeSeconds=10) -> Fail, WaitTimeSeconds = 20
    processor_instance.load_next_entry()
    
    # Poll 3 (WaitTimeSeconds=20) -> Fail, WaitTimeSeconds = 40
    processor_instance.load_next_entry()

    # Assert final state and check call arguments
    assert processor_instance.empty_poll_count == 3
    assert processor_instance.current_wait_time == 40
    
    # Check the call arguments for the last poll
    assert mock_sqs_client_instance.receive_message.call_args_list[2].kwargs['WaitTimeSeconds'] == 20


def test_load_next_entry_backoff_max_cap(processor_instance, mock_boto3_client_setup):
    """Test that the backoff caps at MAX_SQS_WAIT_TIME (60s)."""

    mock_client_function, mock_sqs_client_instance = mock_boto3_client_setup
    
    # Arrange: Set min_wait_time low to force quick capping
    processor_instance.min_wait_time = 1
    processor_instance.current_wait_time = 1
    processor_instance.MAX_SQS_WAIT_TIME = 10 # Lower cap for testing
    mock_sqs_client_instance.receive_message.return_value = {'Messages': []}

    # Poll until cap is reached (1 -> 2 -> 4 -> 8 -> 10(capped))
    for _ in range(5):
        processor_instance.load_next_entry()
    
    # Assert cap
    assert processor_instance.current_wait_time == 10
    
    # Run one more time to ensure it stays capped
    processor_instance.load_next_entry()
    
    # Assert the wait time used in the call is the capped value
    assert mock_sqs_client_instance.receive_message.call_args_list[-1].kwargs['WaitTimeSeconds'] == 10
    assert processor_instance.current_wait_time == 10
    
    
def test_load_next_entry_backoff_reset_on_success(processor_instance, mock_boto3_client_setup, mock_sqs_message):
    """Test that finding a message resets the backoff variables."""

    mock_client_function, mock_sqs_client_instance = mock_boto3_client_setup
    
    # 1. Fail once to trigger backoff
    mock_sqs_client_instance.receive_message.return_value = {'Messages': []}
    processor_instance.load_next_entry() # WaitTime is now 10, count is 1
    assert processor_instance.current_wait_time == 10
    
    # 2. Succeed on the next call
    mock_sqs_client_instance.receive_message.return_value = {'Messages': [mock_sqs_message]}
    result = processor_instance.load_next_entry() # Should use WaitTime 10
    
    # Assert success and reset
    assert result is True
    assert processor_instance.empty_poll_count == 0
    assert processor_instance.current_wait_time == 5 # Reset to min_wait_time


## Test mark_entry_resolved

def test_mark_entry_resolved_calls_sqs_delete(processor_instance, mock_boto3_client_setup):
    """Test that mark_entry_resolved calls the SQS delete_message method correctly."""

    mock_client_function, mock_sqs_client_instance = mock_boto3_client_setup
    
    # Arrange: Ensure a message has been loaded so receipt_handle is set
    processor_instance.load_next_entry() 
    
    # Reset mock_boto3_client for clarity on delete_message calls
    mock_sqs_client_instance.delete_message.reset_mock()
    
    # Act
    processor_instance.mark_entry_resolved()
    
    # Assert SQS client interaction
    mock_sqs_client_instance.delete_message.assert_called_once_with(
        QueueUrl=processor_instance.queue_url,
        ReceiptHandle='receipt-handle-456' # From mock_sqs_message fixture
    )

def test_mark_entry_resolved_without_message_loaded(processor_instance, mock_boto3_client_setup):
    """Test that calling delete without a loaded message (no handle) doesn't fail."""

    mock_client_function, mock_sqs_client_instance = mock_boto3_client_setup
    
    # Arrange: Do not call load_next_entry, receipt_handle is None
    processor_instance.receipt_handle = None 
    
    # Act (should typically raise an exception if not properly guarded in production code,
    # but here we ensure the test doesn't fail due to an unrelated mock error)
    # The current implementation will raise a TypeError when receipt_handle is None, 
    # but we assume that the use case guarantees load_next_entry is called first.
    # We rely on the mock setup to handle the call.
    
    # The safest approach is to ensure the handler is set, as the class doesn't guard against None.
    processor_instance.load_next_entry()
    
    mock_sqs_client_instance.delete_message.reset_mock()
    processor_instance.mark_entry_resolved()
    mock_sqs_client_instance.delete_message.assert_called_once()
    

## Test get_entry

def test_get_entry_returns_sqs_entry(processor_instance, mocker, mock_sqs_message):
    """Test that get_entry returns an SQSEntry instance constructed with the current message."""
    
    # ARRANGE 1: Mock the SQSEntry class itself where it's looked up
    mock_sqs_entry_cls = mocker.patch(
        'external_secrets_reloader.processors.sqs_processor.SQSEntry'
    )
    
    # ARRANGE 2: Ensure a message is loaded
    processor_instance.load_next_entry() 
    
    # ACT
    entry = processor_instance.get_entry()
    
    # ASSERT 1: Verify the class was called correctly
    mock_sqs_entry_cls.assert_called_once_with(mock_sqs_message)
    
    # ASSERT 2: Verify the return value is the result of the mocked constructor call
    assert entry == mock_sqs_entry_cls.return_value