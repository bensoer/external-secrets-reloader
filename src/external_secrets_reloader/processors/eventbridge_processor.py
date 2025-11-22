

from external_secrets_reloader.entries.eventbridgeentry import EventBridgeEntry
from external_secrets_reloader.entries.sqsentry import SQSEntry
from external_secrets_reloader.processors.processor import Processor

import logging

class EventBridgeProcessor(Processor[EventBridgeEntry]):

    def __init__(self, source: Processor[SQSEntry]):
        self.source = source
        self._logger = logging.getLogger(self.__class__.__name__)

        self.raw_content = ""

    def load_next_entry(self) -> bool:
        try:
            if not self.source.load_next_entry():
                self._logger.debug("Loading Of Next Item Failed")
                return False
            
            self._logger.debug("Next Item Loaded Successful. Fetching Out SQSEntry")
            sqs_entry = self.source.get_entry()
            self.raw_content = sqs_entry.get_message_body()

            return True
        except Exception as e:
            self._logger.error(e)
            self._logger.error("Exception Thrown Trying To Load Next Entry")
            return False
        

    def get_entry(self) -> EventBridgeEntry:
        # Implementation for retrieving the message from the EventBridge entry
        return EventBridgeEntry(self.raw_content)
    