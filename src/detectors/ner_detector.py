import logging
from typing import List
from src.core.entity import PIIEntity, PIIType
from src.detectors.base_detector import BaseDetector

logger = logging.getLogger(__name__)

try:
    import spacy
except ImportError:
    spacy = None
    logger.warning("spacy is not installed. NER detector will not work.")

class NERDetector(BaseDetector):
    """NER-based PII detector using spaCy."""

    def __init__(self):
        self.nlp = None
        if spacy is not None:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except Exception as e:
                logger.warning(f"Failed to load spaCy model en_core_web_sm: {e}")
                
        self.false_positives = {'the', 'india', 'section', 'act', 'company', 'ltd', 'private', 'limited', 'page'}

    @property
    def name(self) -> str:
        return "NERDetector"

    def detect(self, text: str) -> List[PIIEntity]:
        if self.nlp is None:
            return []
            
        entities = []
        doc = self.nlp(text)
        
        for ent in doc.ents:
            if len(ent.text.strip()) < 2:
                continue
                
            if ent.text.strip().lower() in self.false_positives:
                continue
                
            entity_type = None
            confidence = 0.0
            
            if ent.label_ == "PERSON":
                entity_type = PIIType.PERSON
                confidence = 0.88
            elif ent.label_ == "ORG":
                entity_type = PIIType.COMPANY
                confidence = 0.82
            elif ent.label_ in ("GPE", "LOC"):
                entity_type = PIIType.ADDRESS
                confidence = 0.75
                
            if entity_type:
                entities.append(PIIEntity(
                    text=ent.text,
                    entity_type=entity_type,
                    start=ent.start_char,
                    end=ent.end_char,
                    detector=self.name,
                    confidence=confidence,
                    context=self._get_context(text, ent.start_char, ent.end_char)
                ))
                
        return entities
