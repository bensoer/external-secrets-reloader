import pytest
import logging
import time
from unittest.mock import MagicMock, call, patch

# Import the class under test
from external_secrets_reloader.event_handler.eso_event_handler import ESOEventHandler
# Import the ABCs/Types for typing hints
from external_secrets_reloader.parsers.eso_key_parser import ESOKeyParser
from external_secrets_reloader.processors.processor import Processor
from external_secrets_reloader.reloader.reloader import Reloader

# --- Fixtures ---

@pytest.fixture
def mock_processor():
    """Provides a mock Processor instance."""
    processor = MagicMock(spec=Processor)
    # Configure the mock ESOKeyParser that the processor will return
    mock_entry = MagicMock(spec=ESOKeyParser)
    mock_entry.get_key.return_value = "test-secret-key"
    
    # Configure the processor's methods
    processor.get_entry.return_value = mock_entry
    processor.load_next_entry.return_value = True # Default to having an event
    processor.mark_entry_resolved.return_value = None
    
    return processor

@pytest.fixture
def mock_reloader():
    """Provides a mock Reloader instance."""
    reloader = MagicMock(spec=Reloader)
    reloader.reload.return_value = True # Default to successful reload
    return reloader

@pytest.fixture
def eso_event_handler(mock_processor, mock_reloader):
    """Provides an instance of ESOEventHandler."""
    return ESOEventHandler(mock_processor, mock_reloader)

# --- Tests ---

def test_eso_event_handler_initialization(mock_processor, mock_reloader):
    """Tests the __init__ method for correct attribute assignment and logger setup."""
    
    # Check attributes
    handler = ESOEventHandler(mock_processor, mock_reloader)
    assert handler.processor == mock_processor
    assert handler.reloader == mock_reloader
    
    # Check logger initialization
    with patch('logging.getLogger', autospec=True) as mock_get_logger:
        ESOEventHandler(mock_processor, mock_reloader)
        mock_get_logger.assert_called_once_with('ESOEventHandler')

def test_poll_for_events_no_event(eso_event_handler, mock_processor, mock_reloader):
    """Tests poll_for_events when load_next_entry returns False (no event)."""
    
    # Configure processor to return False (no event)
    mock_processor.load_next_entry.return_value = False
    
    eso_event_handler.poll_for_events()
    
    # Assert nothing else was called
    mock_processor.load_next_entry.assert_called_once()
    mock_processor.get_entry.assert_not_called()
    mock_processor.mark_entry_resolved.assert_not_called()
    
    # --- FIX APPLIED HERE ---
    # The 'reload' method belongs to the mock_reloader object, not mock_processor
    mock_reloader.reload.assert_not_called()
    # -------------------------

@patch('logging.Logger.info')
@patch('logging.Logger.error')
def test_poll_for_events_success_on_first_attempt(mock_log_error, mock_log_info, eso_event_handler, mock_processor, mock_reloader):
    """Tests poll_for_events when reload is successful on the first attempt."""
    
    eso_event_handler.poll_for_events()
    
    # Assert sequence of calls
    mock_processor.load_next_entry.assert_called_once()
    mock_processor.get_entry.assert_called_once()
    
    # Assert reloader was called once and succeeded
    mock_reloader.reload.assert_called_once_with("test-secret-key")
    
    # Assert entry was marked resolved
    mock_processor.mark_entry_resolved.assert_called_once()
    
    # Assert logging of success
    mock_log_info.assert_any_call("test-secret-key Key Changed. Searching For Matching ExternalSecrets")
    mock_log_error.assert_not_called()

@patch('time.sleep', return_value=None) # Prevent actual sleep during tests
@patch('random.uniform', return_value=0.5) # Fix jitter for predictable testing
@patch('logging.Logger.info')
@patch('logging.Logger.error')
def test_poll_for_events_success_on_second_attempt(mock_log_error, mock_log_info, mock_random_uniform, mock_time_sleep, eso_event_handler, mock_processor, mock_reloader):
    """Tests poll_for_events when reload fails once and succeeds on the second attempt."""
    
    # Configure reloader to fail, then succeed
    mock_reloader.reload.side_effect = [False, True]
    
    eso_event_handler.poll_for_events()
    
    # Assert reloader was called twice
    assert mock_reloader.reload.call_count == 2
    mock_reloader.reload.assert_has_calls([
        call("test-secret-key"),
        call("test-secret-key")
    ])
    
    # Assert sleep and error log occurred once
    mock_time_sleep.assert_called_once()
    mock_log_error.assert_called_once()
    mock_log_error.assert_any_call("Reloading Appears To Have Failed. This Is BackOff Attempt 1/3. We Will Abort After 3 Attempts")
    
    # Assert entry was marked resolved (since it eventually succeeded)
    mock_processor.mark_entry_resolved.assert_called_once()


@patch('time.sleep', return_value=None) # Prevent actual sleep during tests
@patch('random.uniform', return_value=0.5) # Fix jitter for predictable testing
@patch('logging.Logger.info')
@patch('logging.Logger.error')
def test_poll_for_events_failure_and_max_attempts_reached(mock_log_error, mock_log_info, mock_random_uniform, mock_time_sleep, eso_event_handler, mock_processor, mock_reloader):
    """Tests poll_for_events when all three reload attempts fail."""
    
    # Configure reloader to fail three times
    mock_reloader.reload.return_value = False
    
    eso_event_handler.poll_for_events()
    
    # Assert reloader was called max_attempts (3) times
    assert mock_reloader.reload.call_count == 3
    
    # Assert sleep occurred twice (after the 1st and 2nd failures)
    assert mock_time_sleep.call_count == 3
    
    # Assert the final error log occurred
    mock_log_error.assert_called_with("Reloading Key test-secret-key Failed. Aborting And Moving On")
    
    # Assert mark_entry_resolved is STILL called, as per the logic:
    # "If successful OR backoff retries runout, mark the entry resolved"
    mock_processor.mark_entry_resolved.assert_called_once()