
from abc import ABC, abstractmethod

class Reloader(ABC):

    @abstractmethod
    def reload(key:str):
        ...