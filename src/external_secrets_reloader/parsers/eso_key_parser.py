

from abc import ABC, abstractmethod

class ESOKeyParser(ABC):
    '''
    ESOKeyParser is an interface that dictates required methods needed in order for ESO ExternalSecret reloaders
    to retrieve the key that identifies the external secret that has been changed. 

    In other words, this interface allows reloaders to fetch the key from the event that it will then be used to 
    compare against the ESO ExternalSecret to tell if the ExternalSecret uses that key. If they match, the 
    reloader will reload that specific ExternalSecret
    '''

    def __init__(self):
        pass

    @abstractmethod
    def get_key() -> str:
        '''
        Fetch the key from the event, that the reloader can use to identify whether the ExternalSecret uses this key located
        in the external source

        @return str: The string representation of the key
        '''
        ...