import logging
from typing import Dict, Optional, Any
from src.core.entity import PIIType

logger = logging.getLogger(__name__)

class PIIRegistry:
    """Maintains a mapping of normalized PII -> replacement.
    Ensures the same PII always gets the same fake replacement.
    """
    
    def __init__(self):
        self._registry: Dict[str, str] = {}  # normalized_value -> replacement
        self._type_registry: Dict[str, PIIType] = {}  # normalized_value -> type
        self._person_to_replacement: Dict[str, str] = {} # original person -> replacement name (for emails)
    
    def get_replacement(self, normalized_value: str, entity_type: PIIType) -> Optional[str]:
        """Get existing replacement for this value, or None."""
        if normalized_value in self._registry and self._type_registry.get(normalized_value) == entity_type:
            return self._registry[normalized_value]
        return None
    
    def register(self, normalized_value: str, entity_type: PIIType, replacement: str) -> None:
        """Register a new PII -> replacement mapping."""
        self._registry[normalized_value] = replacement
        self._type_registry[normalized_value] = entity_type
        if entity_type == PIIType.PERSON:
            self._person_to_replacement[normalized_value.lower()] = replacement
    
    def has(self, normalized_value: str) -> bool:
        """Check if a value is already registered."""
        return normalized_value in self._registry
    
    def get_all_mappings(self) -> Dict[str, dict]:
        """Return all mappings for audit report."""
        return {
            val: {
                "replacement": rep,
                "type": self._type_registry[val].name
            }
            for val, rep in self._registry.items()
        }
        
    def get_person_replacement(self, original_name: str) -> Optional[str]:
        """Get replacement for a person, useful for deriving emails."""
        return self._person_to_replacement.get(original_name.lower())
