

from abc import ABC, abstractmethod

class KeyParser(ABC):

    def __init__(self):
        pass

    @abstractmethod
    def get_key() -> str:
        ...