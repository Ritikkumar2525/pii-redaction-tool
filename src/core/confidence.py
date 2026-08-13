import logging
from typing import List, Dict, Tuple
from src.core.entity import PIIEntity, PIIType

logger = logging.getLogger(__name__)

class ConfidenceScorer:
    """Adjusts confidence scores based on multi-detector agreement and context."""
    
    # Default thresholds
    AUTO_REDACT_THRESHOLD = 0.85
    REVIEW_THRESHOLD = 0.60
    
    def __init__(self, auto_threshold: float = AUTO_REDACT_THRESHOLD, review_threshold: float = REVIEW_THRESHOLD):
        self.auto_threshold = auto_threshold
        self.review_threshold = review_threshold
    
    def should_redact(self, entity: PIIEntity) -> bool:
        """Whether entity meets auto-redact threshold."""
        return entity.confidence >= self.auto_threshold
    
    def boost_for_multi_detection(self, entities: List[PIIEntity]) -> List[PIIEntity]:
        """Boost confidence when multiple detectors agree on same span."""
        if not entities:
            return []
            
        # Group by identical spans and type
        grouped: Dict[Tuple[int, int, PIIType], List[PIIEntity]] = {}
        for ent in entities:
            key = (ent.start, ent.end, ent.entity_type)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(ent)
            
        result = []
        for key, group in grouped.items():
            if len(group) == 1:
                result.append(group[0])
            else:
                # Merge logic: if multiple detectors agree, boost confidence
                # Pick the entity with the highest base confidence
                best_ent = max(group, key=lambda e: e.confidence)
                detectors = set(e.detector for e in group)
                if len(detectors) > 1:
                    logger.debug(f"Boosting confidence for {best_ent.text} (detectors: {detectors})")
                    best_ent.confidence = min(1.0, best_ent.confidence + 0.05 * (len(detectors) - 1))
                    best_ent.detector = f"Multiple({','.join(sorted(list(detectors)))})"
                result.append(best_ent)
                
        return result
