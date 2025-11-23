

from external_secrets_reloader.parsers.eso_key_parser import ESOKeyParser
from external_secrets_reloader.processors.processor import Processor
import logging
import time
import random

from external_secrets_reloader.reloader.eso_aws_provider_reloader import ESOAWSProviderReloader

class AWSEventHandler():

    def __init__(self, processor: Processor[ESOKeyParser], reloader: ESOAWSProviderReloader):
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
            
            # Backoff Retry A Bit if the reload fails
            count = 0
            backoff_factor = 2.0
            initial_delay = 1
            max_attempts = 3
            while not self.reloader.reload(key):
                count += 1
                self._logger.error(f"Reloading Appears To Have Failed. This Is BackOff Attempt {count}/{max_attempts}. We Will Abort After {max_attempts} Attempts")

                base_delay = initial_delay * (backoff_factor ** count)
                jitter = random.uniform(0, base_delay)
                sleep_time = base_delay + jitter

                self._logger.info(f"Will ReAttempt Reload In {sleep_time:.2f} Seconds")
                time.sleep(sleep_time)

                if count >= max_attempts:
                    self._logger.error(f"Reloading Key {key} Failed. Aborting And Moving On")
                    break

            # If successful OR backoff retries runout, mark the entry resolved so that it is removed from being attempted
            self.processor.mark_entry_resolved()


