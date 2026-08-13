import logging
from typing import List
from src.core.entity import PIIEntity, PIIType

logger = logging.getLogger(__name__)

TYPE_SPECIFICITY = {
    PIIType.CREDIT_CARD: 100,
    PIIType.SSN: 90,
    PIIType.EMAIL: 80,
    PIIType.IP_ADDRESS: 75,
    PIIType.PHONE: 70,
    PIIType.DOB: 60,
    PIIType.COMPANY: 50,
    PIIType.PERSON: 40,
    PIIType.ADDRESS: 30
}

def get_specificity(pii_type: PIIType) -> int:
    return TYPE_SPECIFICITY.get(pii_type, 0)

class EntityMerger:
    """Merges overlapping PII entities."""
    
    @staticmethod
    def merge_entities(entities: List[PIIEntity]) -> List[PIIEntity]:
        if not entities:
            return []
            
        # Deduplicate identical entities (start, end, type) and boost confidence
        unique_spans = {}
        for ent in entities:
            key = (ent.start, ent.end, ent.entity_type)
            if key not in unique_spans:
                unique_spans[key] = []
            unique_spans[key].append(ent)
            
        deduplicated = []
        for key, group in unique_spans.items():
            best_ent = max(group, key=lambda e: e.confidence)
            detectors = set(e.detector for e in group)
            if len(detectors) > 1:
                best_ent.confidence = min(1.0, best_ent.confidence + 0.05 * (len(detectors) - 1))
                best_ent.detector = f"Multiple({','.join(sorted(list(detectors)))})"
            deduplicated.append(best_ent)
            
        # Sort by start position
        sorted_entities = sorted(deduplicated, key=lambda e: (e.start, -e.end))
        
        merged_results = []
        current_group = []
        
        for ent in sorted_entities:
            if not current_group:
                current_group.append(ent)
            else:
                # Check overlap with the current group's extent
                group_end = max(e.end for e in current_group)
                if ent.start < group_end: # Overlaps
                    current_group.append(ent)
                else:
                    # Resolve group and start new
                    merged_results.append(EntityMerger._resolve_group(current_group))
                    current_group = [ent]
                    
        if current_group:
            merged_results.append(EntityMerger._resolve_group(current_group))
            
        return merged_results
        
    @staticmethod
    def _resolve_group(group: List[PIIEntity]) -> PIIEntity:
        if len(group) == 1:
            return group[0]
            
        def rank_key(e: PIIEntity):
            return (
                e.confidence,
                get_specificity(e.entity_type),
                e.end - e.start
            )
            
        return max(group, key=rank_key)
