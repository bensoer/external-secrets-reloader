

from typing import Optional
import boto3
import logging

from external_secrets_reloader.entries.sqsentry import SQSEntry
from external_secrets_reloader.processors.processor import Processor

class SQSProcessor(Processor[SQSEntry]):
    MAX_SQS_WAIT_TIME = 60

    def __init__(self, queue_url: str, min_wait_time:int):
        self.sqs_client = boto3.client('sqs')
        self._logger = logging.getLogger(self.__class__.__name__)

        self.queue_url = queue_url
        self.min_wait_time = min_wait_time
        
        self._logger.debug(f"QUEUE URL: {self.queue_url}")
        self._logger.debug(f"QUEUE_MIN_WAIT_TIME: {self.min_wait_time}")

        # When it comes out the sqs_client it returns already as a dict
        self.current_message = dict()
        self.receipt_handle: Optional[str] = None
        self.message_id: Optional[str] = None

        # Backoff waittime configuration
        self.empty_poll_count = 0
        self.current_wait_time = min_wait_time

    def load_next_entry(self) -> bool:

        current_poll_wait_time = min(
            self.current_wait_time,
            self.MAX_SQS_WAIT_TIME
        )
        
        self._logger.debug(f"Hanging {current_poll_wait_time} Seconds To Receive Next Message")
        response = self.sqs_client.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=current_poll_wait_time
        ) 

        self._logger.debug("Message Received Or Timeout Reached")
        messages = response.get('Messages', [])
        if messages:
            self._logger.debug("Message Found. Loading...")
            self.current_message = messages[0]
            self.receipt_handle = self.current_message['ReceiptHandle']
            self.message_id = self.current_message['MessageId']
            self._logger.debug(f"Processing of Message ID: {self.message_id} Complete. Returning True")

            # Reset the backoff timer and go back to our minimum wait time
            self.empty_poll_count = 0
            self.current_wait_time = self.min_wait_time

            return True
        else:
            self._logger.debug("No Message Found. Returning False")
            self.current_message = None

            # Because there was no entry, lets hang longer as that costs cheaper
            self.empty_poll_count += 1
            self.current_wait_time = min(
                self.min_wait_time * (2 ** self.empty_poll_count),
                self.MAX_SQS_WAIT_TIME
            )


            return False
    
    def mark_entry_resolved(self):

        self._logger.debug(f"Deleting Message ID: {self.message_id} From SQS Queue")
        self.sqs_client.delete_message(
            QueueUrl=self.queue_url,
            ReceiptHandle=self.receipt_handle
        )
        

    # Further optimisation here would be to allow this method to return a list of SQSEntry, thus allowing
    # us to bulk grab results from the SQS Queue

    def get_entry(self) -> SQSEntry:
        return SQSEntry(self.current_message)