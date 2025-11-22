from threading import Lock

class HealthStatus:
    
    def __init__(self):
        self._lock = Lock()
        self._healthy = True
        self._ready = True
        self._error_message = None
    
    def set_healthy(self, healthy: bool, error_message: str = None):
        """Set the health status."""
        with self._lock:
            self._healthy = healthy
            self._error_message = error_message
    
    def set_ready(self, ready: bool):
        """Set the readiness status."""
        with self._lock:
            self._ready = ready
    
    def is_healthy(self) -> bool:
        """Check if application is healthy."""
        with self._lock:
            return self._healthy
    
    def is_ready(self) -> bool:
        """Check if application is ready."""
        with self._lock:
            return self._ready
    
    def get_error_message(self) -> str:
        """Get the current error message."""
        with self._lock:
            return self._error_message