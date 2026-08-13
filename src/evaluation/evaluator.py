"""Evaluation engine: compare detected entities against ground truth."""

import json
import logging
from typing import Dict, List, Optional, Set, Tuple

from src.core.entity import PIIEntity, PIIType

logger = logging.getLogger(__name__)


class Evaluator:
    """Compare detected PII entities against a ground-truth dataset.

    Matching strategy:
    - Normalized text matching: case-insensitive, whitespace-normalized.
    - A detection counts as a true positive if its normalized value matches
      a ground-truth entry of the same PII type.
    - Each ground-truth entity can match at most one detection (first match wins).
    """

    def __init__(self, ground_truth_path: str):
        """Load ground truth from a JSON file.

        Args:
            ground_truth_path: Path to ground_truth.json.
        """
        self.ground_truth = self._load_ground_truth(ground_truth_path)
        logger.info(
            "Loaded ground truth: %d total entities across %d types",
            sum(len(v) for v in self.ground_truth.values()),
            len(self.ground_truth),
        )

    @staticmethod
    def _load_ground_truth(path: str) -> Dict[str, List[str]]:
        """Load and parse ground truth JSON.

        Expected format:
        {
            "PERSON": ["Rajesh Kumar Agarwal", "Sunita Devi Agarwal", ...],
            "EMAIL": ["rajesh.agarwal@nexusfintech.co.in", ...],
            ...
        }
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Normalize all ground truth values using type-aware normalization
        normalized = {}
        for pii_type, values in data.items():
            normalized[pii_type] = [
                Evaluator._normalize_value(v, pii_type) for v in values
            ]
        return normalized

    @staticmethod
    def _normalize_entity(entity: PIIEntity) -> str:
        """Normalize an entity's text for matching using type-aware rules."""
        return Evaluator._normalize_value(entity.text, entity.entity_type.value)

    @staticmethod
    def _normalize_value(text: str, pii_type: str) -> str:
        """Normalize a value based on its PII type for consistent matching."""
        text = text.strip()
        if pii_type in ("PHONE",):
            # Digits-only comparison for phones
            return "".join(c for c in text if c.isdigit())
        elif pii_type in ("CREDIT_CARD", "SSN"):
            # Digits-only for credit cards and SSNs
            return "".join(c for c in text if c.isdigit())
        elif pii_type == "EMAIL":
            return text.lower().strip()
        else:
            return " ".join(text.lower().split())

    def evaluate(
        self, detected_entities: List[PIIEntity]
    ) -> Dict[str, Dict[str, object]]:
        """Run evaluation comparing detected entities to ground truth.

        Args:
            detected_entities: List of PIIEntity objects from the detection pipeline.

        Returns:
            Dictionary with per-type and overall metrics.
        """
        # Group detected entities by type
        detected_by_type: Dict[str, Set[str]] = {}
        for entity in detected_entities:
            type_key = entity.entity_type.value
            if type_key not in detected_by_type:
                detected_by_type[type_key] = set()
            detected_by_type[type_key].add(self._normalize_entity(entity))

        # All PII types to evaluate
        all_types = set(list(self.ground_truth.keys()) + list(detected_by_type.keys()))

        results = {}
        total_tp = 0
        total_fp = 0
        total_fn = 0

        for pii_type in sorted(all_types):
            gt_set = set(self.ground_truth.get(pii_type, []))
            det_set = detected_by_type.get(pii_type, set())

            # True positives: detected AND in ground truth
            tp_set = gt_set & det_set
            # Also check partial matches for names/addresses (fuzzy)
            tp_partial = set()
            remaining_gt = gt_set - tp_set
            remaining_det = det_set - tp_set
            for gt_val in remaining_gt:
                for det_val in remaining_det - tp_partial:
                    if self._partial_match(gt_val, det_val, pii_type):
                        tp_partial.add(det_val)
                        break

            tp = len(tp_set) + len(tp_partial)
            fp = len(det_set) - len(tp_set) - len(tp_partial)
            fn = len(gt_set) - len(tp_set) - len(tp_partial)

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (
                2 * precision * recall / (precision + recall)
                if (precision + recall) > 0
                else 0.0
            )

            results[pii_type] = {
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "ground_truth_count": len(gt_set),
                "detected_count": len(det_set),
                "tp_exact": list(tp_set),
                "tp_partial": list(tp_partial),
                "false_positives": list(det_set - tp_set - tp_partial),
                "false_negatives": list(remaining_gt - {self._find_match(gt, tp_partial) for gt in remaining_gt if self._find_match(gt, tp_partial)}),
            }

            total_tp += tp
            total_fp += fp
            total_fn += fn

        # Overall metrics
        overall_precision = (
            total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        )
        overall_recall = (
            total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        )
        overall_f1 = (
            2 * overall_precision * overall_recall / (overall_precision + overall_recall)
            if (overall_precision + overall_recall) > 0
            else 0.0
        )
        # Accuracy as Jaccard index: TP / (TP + FP + FN)
        overall_accuracy = (
            total_tp / (total_tp + total_fp + total_fn)
            if (total_tp + total_fp + total_fn) > 0
            else 0.0
        )

        results["OVERALL"] = {
            "tp": total_tp,
            "fp": total_fp,
            "fn": total_fn,
            "precision": round(overall_precision, 4),
            "recall": round(overall_recall, 4),
            "f1": round(overall_f1, 4),
            "accuracy": round(overall_accuracy, 4),
            "accuracy_definition": (
                "Jaccard index: TP / (TP + FP + FN). "
                "This measures the overlap between detected and ground-truth entity sets. "
                "Unlike traditional accuracy which requires true negatives (undefined for "
                "entity extraction over arbitrary text spans), the Jaccard index provides "
                "a meaningful single metric for set-based evaluation."
            ),
        }

        return results

    @staticmethod
    def _partial_match(gt_val: str, det_val: str, pii_type: str) -> bool:
        """Check for partial match between ground truth and detection.

        For PERSON and COMPANY types, we allow substring matching
        (e.g., 'rajesh agarwal' matches 'rajesh kumar agarwal').
        For PHONE, we compare digit-only forms.
        For ADDRESS, we check if significant overlap exists.
        """
        if pii_type in ("PERSON", "COMPANY"):
            # Check if one is a substring of the other
            if gt_val in det_val or det_val in gt_val:
                return True
            # Check word overlap
            gt_words = set(gt_val.split())
            det_words = set(det_val.split())
            overlap = gt_words & det_words
            if len(overlap) >= 2 and len(overlap) / max(len(gt_words), len(det_words)) >= 0.5:
                return True

        elif pii_type == "PHONE":
            gt_digits = "".join(c for c in gt_val if c.isdigit())
            det_digits = "".join(c for c in det_val if c.isdigit())
            # Match if last 10 digits are the same
            if len(gt_digits) >= 10 and len(det_digits) >= 10:
                if gt_digits[-10:] == det_digits[-10:]:
                    return True

        elif pii_type == "ADDRESS":
            gt_words = set(gt_val.split())
            det_words = set(det_val.split())
            overlap = gt_words & det_words
            if len(overlap) >= 3 and len(overlap) / max(len(gt_words), len(det_words)) >= 0.3:
                return True

        elif pii_type == "CREDIT_CARD":
            gt_digits = "".join(c for c in gt_val if c.isdigit())
            det_digits = "".join(c for c in det_val if c.isdigit())
            if gt_digits == det_digits:
                return True

        return False

    @staticmethod
    def _find_match(gt_val: str, partial_matches: set) -> Optional[str]:
        """Find if a ground truth value was matched partially."""
        for pm in partial_matches:
            if gt_val in pm or pm in gt_val:
                return gt_val
        return None
