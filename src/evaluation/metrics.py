"""Metrics calculation and report generation."""

import json
import logging
from datetime import datetime
from typing import Dict, List

from src.core.entity import PIIEntity

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Generate evaluation reports in JSON and Markdown formats."""

    @staticmethod
    def generate_detection_report(
        entities: List[PIIEntity], output_path: str
    ) -> None:
        """Generate a JSON detection/audit report.

        Args:
            entities: List of detected and redacted PIIEntity objects.
            output_path: Path to write the JSON report.
        """
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_entities_detected": len(entities),
            "entities_by_type": {},
            "detections": [],
        }

        # Count by type
        type_counts: Dict[str, int] = {}
        for entity in entities:
            type_key = entity.entity_type.value
            type_counts[type_key] = type_counts.get(type_key, 0) + 1

        report["entities_by_type"] = type_counts

        # Individual detections
        for entity in entities:
            detection = {
                "type": entity.entity_type.value,
                "original": entity.text,
                "replacement": entity.replacement,
                "confidence": round(entity.confidence, 4),
                "detector": entity.detector,
                "action": "REDACT" if entity.replacement else "SKIP",
                "normalized_value": entity.normalized_value,
            }
            report["detections"].append(detection)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info("Detection report written to %s", output_path)

    @staticmethod
    def generate_evaluation_report(
        eval_results: Dict[str, Dict],
        output_path: str,
        source_document: str = "Red_Herring_Prospectus.docx",
    ) -> None:
        """Generate a Markdown evaluation report.

        Args:
            eval_results: Results from Evaluator.evaluate().
            output_path: Path to write the Markdown report.
            source_document: Name of the source document.
        """
        overall = eval_results.get("OVERALL", {})
        total_gt = sum(
            v.get("ground_truth_count", 0)
            for k, v in eval_results.items()
            if k != "OVERALL"
        )

        lines = [
            "# PII Redaction Evaluation Report",
            "",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## Dataset",
            "",
            f"- **Source Document**: {source_document}",
            f"- **Manually Annotated Entities**: {total_gt}",
            f"- **PII Categories Evaluated**: {len(eval_results) - 1}",
            "",
            "---",
            "",
            "## Overall Metrics",
            "",
            "| Metric | Score |",
            "|--------|-------|",
            f"| **Accuracy** (Jaccard Index) | {overall.get('accuracy', 0):.4f} |",
            f"| **Precision** | {overall.get('precision', 0):.4f} |",
            f"| **Recall** | {overall.get('recall', 0):.4f} |",
            f"| **F1 Score** | {overall.get('f1', 0):.4f} |",
            "",
            f"> **Accuracy Definition**: {overall.get('accuracy_definition', 'N/A')}",
            "",
            "---",
            "",
            "## Per-Type Metrics",
            "",
            "| PII Type | TP | FP | FN | Precision | Recall | F1 |",
            "|----------|----|----|----|-----------+--------+----|",
        ]

        pii_types_order = [
            "PERSON", "EMAIL", "PHONE", "COMPANY", "ADDRESS",
            "SSN", "CREDIT_CARD", "DOB", "IP_ADDRESS",
        ]

        for pii_type in pii_types_order:
            if pii_type in eval_results:
                r = eval_results[pii_type]
                lines.append(
                    f"| {pii_type} | {r['tp']} | {r['fp']} | {r['fn']} | "
                    f"{r['precision']:.4f} | {r['recall']:.4f} | {r['f1']:.4f} |"
                )
            else:
                lines.append(f"| {pii_type} | 0 | 0 | 0 | N/A | N/A | N/A |")

        # Also include any types in results not in our standard order
        for pii_type in sorted(eval_results.keys()):
            if pii_type not in pii_types_order and pii_type != "OVERALL":
                r = eval_results[pii_type]
                lines.append(
                    f"| {pii_type} | {r['tp']} | {r['fp']} | {r['fn']} | "
                    f"{r['precision']:.4f} | {r['recall']:.4f} | {r['f1']:.4f} |"
                )

        lines.extend([
            "",
            "---",
            "",
            "## Error Analysis",
            "",
        ])

        # Analyze errors per type
        for pii_type in pii_types_order:
            if pii_type not in eval_results:
                continue
            r = eval_results[pii_type]
            if r["fp"] > 0 or r["fn"] > 0:
                lines.append(f"### {pii_type}")
                lines.append("")
                if r["fn"] > 0:
                    fn_items = r.get("false_negatives", [])
                    lines.append(f"**Missed ({r['fn']})**: {', '.join(fn_items[:10]) if fn_items else 'See detailed report'}")
                    lines.append("")
                if r["fp"] > 0:
                    fp_items = r.get("false_positives", [])
                    lines.append(f"**False Positives ({r['fp']})**: {', '.join(fp_items[:10]) if fp_items else 'See detailed report'}")
                    lines.append("")

        lines.extend([
            "---",
            "",
            "## Discussion",
            "",
            "### Strengths",
            "- Regex-based detection provides high precision for structured PII (email, SSN, credit card, IP).",
            "- Luhn validation eliminates most credit card false positives.",
            "- Context-aware detection helps classify dates as DOB vs. ordinary dates.",
            "- Deterministic replacement ensures referential consistency across the document.",
            "",
            "### Known Limitations",
            "- NER model (spaCy en_core_web_sm) may miss some person names, especially Indian names not well-represented in training data.",
            "- Address detection is inherently challenging without a full address parser.",
            "- Company names in financial documents often appear in legal/regulatory contexts that are borderline between PII and public information.",
            "- Phone number detection must balance against financial figures, CIN numbers, and other numeric identifiers common in prospectuses.",
            "- DOCX run boundaries can split PII text, making some replacements imperfect.",
            "",
            "### Methodology Notes",
            "- Ground truth was manually curated from the source document.",
            "- Matching uses normalized text comparison (case-insensitive, whitespace-normalized).",
            "- Partial matching is allowed for PERSON and COMPANY types (substring/word-overlap matching).",
            "- Phone matching compares last 10 digits to handle format variations.",
            "",
        ])

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info("Evaluation report written to %s", output_path)

    @staticmethod
    def save_evaluation_json(
        eval_results: Dict[str, Dict], output_path: str
    ) -> None:
        """Save raw evaluation results as JSON for programmatic access."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(eval_results, f, indent=2, ensure_ascii=False, default=str)
        logger.info("Evaluation JSON written to %s", output_path)
