

import logging
import signal

from external_secrets_reloader.event_handler.aws_parameter_store_event_handler import AWSParameterStoreEventHandler
from external_secrets_reloader.health_check.health_status_thread import HealthStatusThread
from external_secrets_reloader.processors.eventbridge_processor import EventBridgeProcessor
from external_secrets_reloader.processors.sqs_processor import SQSProcessor
from external_secrets_reloader.reloader.eso_aws_parameter_store_reloader import ESOAWSParameterStoreReloader
from external_secrets_reloader.settings import Settings

print("==== Starting Application ====")

CONTINUE_PROCESSING = True
def signal_handler(sig, frame):
    global CONTINUE_PROCESSING

    """
    Custom handler function for signals.
    """
    if sig == signal.SIGINT:
        print('Received SIGINT (Ctrl+C). Performing graceful shutdown...')
    elif sig == signal.SIGTERM:
        print('Received SIGTERM. Performing graceful shutdown...')
    else:
        print(f'Received signal {sig}. Performing graceful shutdown...')

    CONTINUE_PROCESSING = False


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

print("==== SIG Handlers Registered ====")

settings = Settings()

print("==== Environment Settings Parsed ====")

logging_levels = {
    'ERROR': logging.ERROR,
    'WARN': logging.WARN,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
}
logging_level_int = logging_levels.get(settings.LOG_LEVEL, logging.INFO)

logging.basicConfig(
    level=logging_level_int,
    format='%(asctime)s [%(levelname)s] %(name)s : %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Suppress verbose logging from third-party libraries
logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = logging.getLogger("external-secrets-reloader")

print("==== Logging Registered ====")

def main() -> None:
    global CONTINUE_PROCESSING

    startup_message = """
==============================================================================================================
 _____     _                        _   _____                    _    ______     _                 _           
|  ___|   | |                      | | /  ___|                  | |   | ___ \   | |               | |          
| |____  _| |_ ___ _ __ _ __   __ _| | \ `--.  ___  ___ _ __ ___| |_  | |_/ /___| | ___   __ _  __| | ___ _ __ 
|  __\ \/ / __/ _ \ '__| '_ \ / _` | |  `--. \/ _ \/ __| '__/ _ \ __| |    // _ \ |/ _ \ / _` |/ _` |/ _ \ '__|
| |___>  <| ||  __/ |  | | | | (_| | | /\__/ /  __/ (__| | |  __/ |_  | |\ \  __/ | (_) | (_| | (_| |  __/ |   
\____/_/\_\\__\___|_|  |_| |_|\__,_|_| \____/ \___|\___|_|  \___|\__| \_| \_\___|_|\___/ \__,_|\__,_|\___|_|   
                                                                                                               
===============================================================================================================
                                    Created By Ben Soer (@bensoer)                                              """

    print(startup_message + "\n\n")

    # Start health check server for Kubernetes probes
    logger.info("Starting Health Check Endpoints")
    hst = HealthStatusThread()
    hst.start(port=settings.HEALTH_CHECK_PORT, debug=(logging_level_int == logging.DEBUG))
    # Get the health status object to update during initialization
    health_status = hst.get_health_status()
    health_status.set_ready(False)  # Mark as not ready during initialization
    logger.debug("Health Check Endpoints Started")

    
    try:
        logger.info("Initializing processors, reloaders and event handlers")

        sqs_processor = SQSProcessor(settings.SQS_QUEUE_URL, settings.SQS_QUEUE_WAIT_TIME)
        event_bridge_processor = EventBridgeProcessor(sqs_processor)

        esoapsr = ESOAWSParameterStoreReloader()
        aws_pseh = AWSParameterStoreEventHandler(event_bridge_processor, esoapsr)
        
        logger.debug("All components initialized successfully")
        health_status.set_healthy(True)
        health_status.set_ready(True)
        
    except Exception as e:
        error_msg = f"Failed to initialize components: {str(e)}"
        logger.error(error_msg, exc_info=e)
        health_status.set_healthy(False, error_msg)
        health_status.set_ready(False)
        return

    while CONTINUE_PROCESSING:
        aws_pseh.poll_for_events()

