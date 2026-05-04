from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseConnector(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """The identifier for this connector."""
        pass

    @abstractmethod
    def fetch_data(self) -> List[Dict[str, Any]]:
        """Fetch raw data from the external source."""
        pass

    def __init__(self):
        self.errors: List[str] = []

    def handle_error(self, error: Exception):
        """Default error handler — stores error for reporting."""
        msg = f"Error in {self.name}: {error}"
        print(f"[!]  {msg}")
        self.errors.append(msg)
