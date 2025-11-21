

import logging
from external_secrets_reloader.event_handler.aws_parameter_store_event_handler import AWSParameterStoreEventHandler
from external_secrets_reloader.processors.eventbridge_processor import EventBridgeProcessor
from external_secrets_reloader.processors.sqs_processor import SQSProcessor


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

def main() -> None:
    logger.info("Starting external-secrets-reloader")

    sqs_processor = SQSProcessor("https://sqs.us-east-1.amazonaws.com/445477118420/ssm-parameter-store-event-queue")
    event_bridge_processor = EventBridgeProcessor(sqs_processor)

    aws_pseh = AWSParameterStoreEventHandler(event_bridge_processor)
    aws_pseh.start()
