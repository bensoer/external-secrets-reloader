

import json
import logging

from external_secrets_reloader.parsers.eso_key_parser import ESOKeyParser

class EventBridgeEntry(ESOKeyParser):

    def __init__(self, event_bridge_entry:str):
        self._logger = logging.getLogger(self.__class__.__name__)

        self.raw_entry = event_bridge_entry
        self.entry = json.loads(event_bridge_entry)

    def get_resources(self) -> list:
        return self.entry["resources"]
    
    def get_name(self) -> str:
        return self.entry["detail"]["name"]
    
    def get_operation(self) -> str:
        return self.entry["detail"]["operation"]
    
    def get_key(self):
        return self.entry["detail"]["name"]