import logging
from typing import List
from src.core.entity import PIIEntity, PIIType

logger = logging.getLogger(__name__)

class ContextDetector:
    """Detector that adjusts confidence of PII candidates based on context."""
    
    def __init__(self):
        self.phone_boost = ['contact', 'phone', 'mobile', 'tel', 'call']
        self.phone_reduce = ['order', 'reference', 'invoice', 'ticket', 'case no', 'registration', 'cin', 'din']
        
        self.dob_boost = ['date of birth', 'dob', 'born', 'birth']
        self.date_reduce = ['report date', 'filing date', 'dated', 'order date', 'incorporation', 'established', 'listed']
        
        self.person_boost = ['mr.', 'mrs.', 'ms.', 'dr.', 'shri']
        self.email_boost = ['email', 'contact', 'mail']
        self.company_boost = ['limited', 'pvt', 'llp', 'inc', 'corp']
        self.address_boost = ['address', 'residence', 'located', 'office', 'floor', 'plot']

    def process(self, entities: List[PIIEntity], text: str) -> List[PIIEntity]:
        """Adjust confidence based on context."""
        adjusted_entities = []
        
        for ent in entities:
            ctx_start = max(0, ent.start - 100)
            ctx_end = min(len(text), ent.end + 100)
            context = text[ctx_start:ctx_end].lower()
            
            new_conf = ent.confidence
            new_type = ent.entity_type
            
            if ent.entity_type == PIIType.PHONE:
                if any(kw in context for kw in self.phone_boost):
                    new_conf += 0.05
                if any(kw in context for kw in self.phone_reduce):
                    new_conf -= 0.3
                    
            elif ent.entity_type == PIIType.DOB:
                if any(kw in context for kw in self.dob_boost):
                    new_conf = 0.96
                elif any(kw in context for kw in self.date_reduce):
                    new_conf = 0.2
                    
            elif ent.entity_type == PIIType.PERSON:
                if any(kw in context for kw in self.person_boost):
                    new_conf += 0.05
                    
            elif ent.entity_type == PIIType.EMAIL:
                if any(kw in context for kw in self.email_boost):
                    new_conf += 0.01
                    
            elif ent.entity_type == PIIType.COMPANY:
                if any(kw in context for kw in self.company_boost):
                    new_conf += 0.05
                    
            elif ent.entity_type == PIIType.ADDRESS:
                if any(kw in context for kw in self.address_boost):
                    new_conf += 0.08
                    
            # Cap confidence
            new_conf = max(0.0, min(1.0, new_conf))
            
            # Create a new entity with adjusted properties
            adjusted_entities.append(PIIEntity(
                text=ent.text,
                entity_type=new_type,
                start=ent.start,
                end=ent.end,
                detector=ent.detector + "+Context",
                confidence=new_conf,
                context=ent.context,
                normalized_value=ent.normalized_value,
                replacement=ent.replacement
            ))
            
        return adjusted_entities
