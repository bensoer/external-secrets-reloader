

import logging
import signal

from external_secrets_reloader.event_handler.aws_parameter_store_event_handler import AWSParameterStoreEventHandler
from external_secrets_reloader.processors.eventbridge_processor import EventBridgeProcessor
from external_secrets_reloader.processors.sqs_processor import SQSProcessor
from external_secrets_reloader.reloader.eso_aws_parameter_store_reloader import ESOAWSParameterStoreReloader

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

logging.basicConfig(
    level=logging.DEBUG,
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

    sqs_processor = SQSProcessor("https://sqs.us-east-1.amazonaws.com/445477118420/ssm-parameter-store-event-queue")
    event_bridge_processor = EventBridgeProcessor(sqs_processor)

    esoapsr = ESOAWSParameterStoreReloader()
    aws_pseh = AWSParameterStoreEventHandler(event_bridge_processor, esoapsr)

    while CONTINUE_PROCESSING:
        aws_pseh.poll_for_events()
