"""
Simple health check HTTP endpoint for Kubernetes liveness/readiness probes.
"""

import logging
from threading import Thread, Lock
from flask import Flask, jsonify

logger = logging.getLogger("flask")


class HealthStatus:
    """Thread-safe health status tracker."""
    
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


# Global health status instance
_health_status = HealthStatus()


def get_health_status() -> HealthStatus:
    """Get the global health status object."""
    return _health_status


def create_health_app(port: int = 8080) -> Flask:
    """
    Create a minimal Flask app with a health check endpoint.
    
    Args:
        port: Port to run the health check server on (default: 8080)
    
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    
    @app.route('/health', methods=['GET'])
    def health():
        """Liveness probe endpoint."""
        status = get_health_status()
        if status.is_healthy():
            return jsonify({"status": "healthy"}), 200
        else:
            error_msg = status.get_error_message()
            return jsonify({"status": "unhealthy", "error": error_msg}), 503
    
    @app.route('/ready', methods=['GET'])
    def ready():
        """Readiness probe endpoint."""
        status = get_health_status()
        if status.is_ready():
            return jsonify({"status": "ready"}), 200
        else:
            return jsonify({"status": "not_ready"}), 503
    
    return app


def start_health_check_server(port: int = 8080) -> Thread:
    """
    Start the health check server in a background thread.
    
    Args:
        port: Port to run the health check server on (default: 8080)
    
    Returns:
        Thread object (daemon thread)
    """
    app = create_health_app(port)
    
    def run_server():
        logger.info(f"Starting health check server on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
    
    thread = Thread(target=run_server, daemon=True)
    thread.start()
    logger.info("Health check server started in background thread")
    
    return thread
