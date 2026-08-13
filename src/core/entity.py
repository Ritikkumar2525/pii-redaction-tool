"""Core entity model for PII detection."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PIIType(Enum):
    """Enumeration of supported PII types."""
    PERSON = "PERSON"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    COMPANY = "COMPANY"
    ADDRESS = "ADDRESS"
    SSN = "SSN"
    CREDIT_CARD = "CREDIT_CARD"
    DOB = "DOB"
    IP_ADDRESS = "IP_ADDRESS"


@dataclass
class PIIEntity:
    """Represents a detected PII entity with metadata.

    Attributes:
        text: The original text of the detected PII.
        entity_type: The classified PII type.
        start: Character offset start position in the source text.
        end: Character offset end position in the source text.
        detector: Name of the detector that found this entity.
        confidence: Confidence score between 0.0 and 1.0.
        normalized_value: Normalized form used for deduplication and registry lookup.
        replacement: The fake replacement value assigned to this entity.
        context: Surrounding text snippet for debugging/audit.
    """
    text: str
    entity_type: PIIType
    start: int
    end: int
    detector: str
    confidence: float
    normalized_value: Optional[str] = None
    replacement: Optional[str] = None
    context: Optional[str] = None

    def __post_init__(self):
        """Set normalized_value from text if not provided."""
        if self.normalized_value is None:
            self.normalized_value = self._normalize(self.text, self.entity_type)

    @staticmethod
    def _normalize(text: str, entity_type: PIIType) -> str:
        """Normalize a PII value for consistent registry lookups.

        Different entity types need different normalization:
        - Names/emails: lowercased, stripped
        - Phones: digits only (no spaces, dashes, parens)
        - SSN/CC: digits only
        - IP: stripped
        - Addresses: lowercased, normalized whitespace
        """
        text = text.strip()

        if entity_type in (PIIType.PERSON, PIIType.EMAIL, PIIType.COMPANY, PIIType.ADDRESS):
            return " ".join(text.lower().split())

        if entity_type == PIIType.PHONE:
            # Keep only digits and leading +
            digits = "".join(c for c in text if c.isdigit() or c == "+")
            return digits

        if entity_type in (PIIType.SSN, PIIType.CREDIT_CARD):
            return "".join(c for c in text if c.isdigit())

        if entity_type == PIIType.IP_ADDRESS:
            return text.strip()

        if entity_type == PIIType.DOB:
            return text.strip()

        return text

    def to_dict(self) -> dict:
        """Serialize entity to a dictionary for JSON output."""
        return {
            "text": self.text,
            "type": self.entity_type.value,
            "start": self.start,
            "end": self.end,
            "detector": self.detector,
            "confidence": round(self.confidence, 4),
            "normalized_value": self.normalized_value,
            "replacement": self.replacement,
            "context": self.context,
        }

    def overlaps_with(self, other: "PIIEntity") -> bool:
        """Check if this entity's span overlaps with another."""
        return self.start < other.end and other.start < self.end

    def contains(self, other: "PIIEntity") -> bool:
        """Check if this entity's span fully contains another."""
        return self.start <= other.start and self.end >= other.end


@dataclass
class DetectionResult:
    """Result from the full detection pipeline.

    Attributes:
        entities: Final list of non-overlapping PII entities.
        raw_candidates: All candidates before merging (for audit).
        text: The full extracted text that was analyzed.
    """
    entities: list = field(default_factory=list)
    raw_candidates: list = field(default_factory=list)
    text: str = ""
