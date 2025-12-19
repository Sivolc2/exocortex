from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseFetcher(ABC):
    """
    Abstract base class for data source fetchers.
    
    Each fetcher is responsible for connecting to a specific data source,
    retrieving data, and formatting it into a standardized structure.
    """

    @abstractmethod
    def __init__(self, config: Dict[str, Any]):
        """Initializes the fetcher with its specific configuration."""
        pass

    @abstractmethod
    def fetch(self) -> List[Dict[str, Any]]:
        """Fetches data and returns it in the standard format."""
        pass