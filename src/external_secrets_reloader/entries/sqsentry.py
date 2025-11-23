import logging

class SQSEntry():

    def __init__(self, sqs_entry: dict):
        self._logger = logging.getLogger(self.__class__.__name__)

        self.entry = sqs_entry

    def get_message_body(self) -> str:
        return self.entry['Body']