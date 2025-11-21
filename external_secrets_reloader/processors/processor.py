

from abc import ABC, abstractmethod
from typing import TypeVar, Generic

T = TypeVar("T")


class Processor(ABC, Generic[T]):
    
    @abstractmethod
    def load_next_entry(self) -> bool:
        ...

    @abstractmethod
    def get_entry(self) -> T:
        ...