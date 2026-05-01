from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class BaseDetector(ABC):
    name: str = "Base"

    def __init__(self, custom_path: Optional[Path] = None):
        self.custom_path = custom_path

    @abstractmethod
    def detect(self) -> bool:
        """Return True if this editor's data files are found on the system."""
        pass

    @abstractmethod
    def scan(self, since=None, until=None) -> dict:
        """Return normalized stats dict."""
        pass

    def _safe_path(self, path: Path) -> bool:
        return path.exists()
