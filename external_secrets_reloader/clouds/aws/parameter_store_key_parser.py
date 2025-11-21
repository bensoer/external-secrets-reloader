from abc import ABC, abstractmethod

class ParameterStoreKeyParser(ABC):

    def __init__(self):
        pass

    @abstractmethod
    def get_parameter_store_key() -> str:
        ...