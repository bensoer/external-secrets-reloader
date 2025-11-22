

from external_secrets_reloader.parsers.eso_key_parser import KeyParser
from external_secrets_reloader.processors.processor import Processor
import logging

from external_secrets_reloader.reloader.eso_aws_parameter_store_reloader import ESOAWSParameterStoreReloader

class AWSParameterStoreEventHandler():

    def __init__(self, processor: Processor[KeyParser], reloader: ESOAWSParameterStoreReloader):
        self.processor = processor
        self.reloader = reloader
        self._logger = logging.getLogger(self.__class__.__name__)

    def poll_for_events(self):
        '''
        Check for new events. If there are any, process them. If not return
        '''

        if self.processor.load_next_entry():
            
            entry = self.processor.get_entry()
            key = entry.get_key()

            # This key can now be searched for in kubernetes ExternalSecrets
            self._logger.info(f"{key} Key Changed. Searching For Matching ExternalSecrets")

            # Reload AWS Parameter Store External Secrets
            self.reloader.reload(key)
