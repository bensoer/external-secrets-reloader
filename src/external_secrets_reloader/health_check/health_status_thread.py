

from external_secrets_reloader.health_check.health_status import HealthStatus

import logging
from threading import Thread, Lock
from flask import Flask, jsonify
from typing import Optional

class HealthStatusThread():

    def __init__(self):
        self.health_status = HealthStatus()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.thread: Optional[Thread] = None
        self.app: Optional[Flask] = None

    def get_health_status(self) -> HealthStatus:
        return self.health_status

    def start(self, host = "0.0.0.0", port = 8080, debug=False):
        self.app = self.create_health_app()
    
        def run_server():
            self.logger.info(f"Starting Health Endpoint On Port {port}")
            self.app.run(host=host, port=port, debug=debug, use_reloader=False)
        
        self.thread = Thread(target=run_server, daemon=True) # Daemon means it will terminate when the main thread terminates
        self.thread.start()
        self.logger.info("Health Check Endpoint Thread Started Successfully")


    def create_health_app(self) -> Flask:
        """
        Create a minimal Flask app with a health check endpoint.
        
        Args:
            port: Port to run the health check server on (default: 8080)
        
        Returns:
            Flask application instance
        """
        app = Flask('HealthStatusServer')
        
        @app.route('/health', methods=['GET'])
        def health():
            """Liveness probe endpoint."""
            if self.health_status.is_healthy():
                return jsonify({"status": "healthy"}), 200
            else:
                error_msg = self.health_status.get_error_message()
                return jsonify({"status": "unhealthy", "error": error_msg}), 503
        
        @app.route('/ready', methods=['GET'])
        def ready():
            """Readiness probe endpoint."""
            if self.health_status.is_ready():
                return jsonify({"status": "ready"}), 200
            else:
                return jsonify({"status": "not_ready"}), 503
        
        return app
        
        

