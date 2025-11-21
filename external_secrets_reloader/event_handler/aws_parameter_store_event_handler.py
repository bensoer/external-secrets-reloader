

from external_secrets_reloader.clouds.aws.parameter_store_key_parser import ParameterStoreKeyParser
from external_secrets_reloader.processors.processor import Processor
import logging

class AWSParameterStoreEventHandler():

    def __init__(self, processor: Processor[ParameterStoreKeyParser]):
        self.processor = processor
        self._logger = logging.getLogger(self.__class__.__name__)


    def start(self):

        while True:
            if self.processor.load_next_entry():
            
                entry = self.processor.get_entry()
                key = entry.get_parameter_store_key()

                # This key can now be searched for in kubernetes ExternalSecrets
                self._logger.info(f"{key} Key Changed. Reloading Matching ExternalSecrets")
