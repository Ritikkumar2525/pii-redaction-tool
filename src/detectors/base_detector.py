from abc import ABC, abstractmethod
from typing import List
from src.core.entity import PIIEntity

class BaseDetector(ABC):
    """Abstract base class for PII detectors."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name of this detector."""
    
    @abstractmethod
    def detect(self, text: str) -> List[PIIEntity]:
        """Detect PII entities in the given text."""
    
    def _get_context(self, text: str, start: int, end: int, window: int = 50) -> str:
        """Extract surrounding context for an entity."""
        ctx_start = max(0, start - window)
        ctx_end = min(len(text), end + window)
        return text[ctx_start:ctx_end]
