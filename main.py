#!/usr/bin/env python3
"""PII Redaction Tool — Main entry point.

A hybrid detection system that identifies and redacts personally identifiable
information (PII) from DOCX documents using regex, NER, and context-aware
detection with deterministic, consistent replacements.

Usage:
    python main.py --input input.docx --output redacted.docx
    python main.py --input input.docx --output redacted.docx --report reports/detection_report.json
    python main.py --input input.docx --output redacted.docx --evaluate --ground-truth evaluation/ground_truth.json
"""

import argparse
import json
import logging
import os
import sys
from typing import List

from src.core.entity import PIIEntity, PIIType, DetectionResult
from src.core.merger import EntityMerger
from src.core.confidence import ConfidenceScorer
from src.core.registry import PIIRegistry
from src.core.replacement import ReplacementGenerator
from src.detectors.regex_detector import RegexDetector
from src.detectors.ner_detector import NERDetector
from src.detectors.context_detector import ContextDetector
from src.document.docx_processor import DocxProcessor
from src.evaluation.metrics import MetricsCalculator


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Suppress noisy third-party loggers
    logging.getLogger("spacy").setLevel(logging.WARNING)
    logging.getLogger("faker").setLevel(logging.WARNING)


def build_pipeline():
    """Construct the detection pipeline components.

    Returns:
        Tuple of (regex_detector, ner_detector, context_detector,
                  merger, scorer, registry, replacement_generator, docx_processor)
    """
    regex_detector = RegexDetector()
    ner_detector = NERDetector()
    context_detector = ContextDetector()
    merger = EntityMerger()
    scorer = ConfidenceScorer()
    registry = PIIRegistry()
    replacement_gen = ReplacementGenerator(registry)
    docx_processor = DocxProcessor()

    return (regex_detector, ner_detector, context_detector,
            merger, scorer, registry, replacement_gen, docx_processor)


def detect_pii(text: str, regex_detector, ner_detector, context_detector,
               merger, scorer, threshold: float) -> DetectionResult:
    """Run the full PII detection pipeline.

    Pipeline: Regex → NER → Merge → Context → Confidence Filter

    Args:
        text: Full extracted text from the document.
        regex_detector: RegexDetector instance.
        ner_detector: NERDetector instance.
        context_detector: ContextDetector instance.
        merger: EntityMerger instance.
        scorer: ConfidenceScorer instance.
        threshold: Minimum confidence to include an entity.

    Returns:
        DetectionResult with final entities and raw candidates.
    """
    logger = logging.getLogger(__name__)

    # Step 1: Run regex detection
    logger.info("Running regex detectors...")
    regex_entities = regex_detector.detect(text)
    logger.info("  Regex found %d candidates", len(regex_entities))

    # Step 2: Run NER detection
    logger.info("Running NER detector...")
    ner_entities = ner_detector.detect(text)
    logger.info("  NER found %d candidates", len(ner_entities))

    # Step 3: Combine all candidates
    all_candidates = regex_entities + ner_entities
    logger.info("Total raw candidates: %d", len(all_candidates))

    # Step 4: Apply context-based adjustments
    logger.info("Running context detector...")
    adjusted_candidates = context_detector.process(all_candidates, text)

    # Step 5: Merge overlapping entities
    logger.info("Merging overlapping entities...")
    merged_entities = merger.merge_entities(adjusted_candidates)
    logger.info("  After merging: %d entities", len(merged_entities))

    # Step 6: Apply confidence threshold
    filtered_entities = [e for e in merged_entities if e.confidence >= threshold]
    dropped = len(merged_entities) - len(filtered_entities)
    logger.info(
        "  After threshold (%.2f): %d entities (%d dropped)",
        threshold, len(filtered_entities), dropped,
    )

    return DetectionResult(
        entities=filtered_entities,
        raw_candidates=all_candidates,
        text=text,
    )


def assign_replacements(entities: List[PIIEntity],
                        replacement_gen: ReplacementGenerator) -> List[PIIEntity]:
    """Assign deterministic fake replacements to all detected entities.

    Processes PERSON entities first so email replacements can be derived
    from person name replacements.

    Args:
        entities: List of detected PII entities.
        replacement_gen: ReplacementGenerator instance.

    Returns:
        The same list with replacement fields populated.
    """
    logger = logging.getLogger(__name__)

    # Process PERSON entities first (emails may depend on them)
    person_entities = [e for e in entities if e.entity_type == PIIType.PERSON]
    other_entities = [e for e in entities if e.entity_type != PIIType.PERSON]

    for entity in person_entities:
        entity.replacement = replacement_gen.generate(
            entity.text, entity.normalized_value, entity.entity_type
        )

    for entity in other_entities:
        entity.replacement = replacement_gen.generate(
            entity.text, entity.normalized_value, entity.entity_type
        )

    logger.info("Assigned replacements for %d entities", len(entities))
    return entities


def main():
    """Main entry point for the PII Redaction Tool."""
    parser = argparse.ArgumentParser(
        description="PII Redaction Tool — Detect and redact PII from DOCX documents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --input doc.docx --output redacted.docx
  python main.py --input doc.docx --output redacted.docx --threshold 0.80
  python main.py --input doc.docx --output redacted.docx --evaluate
        """,
    )
    parser.add_argument(
        "--input", "-i", required=True,
        help="Path to the input DOCX file.",
    )
    parser.add_argument(
        "--output", "-o", required=True,
        help="Path to the output redacted DOCX file.",
    )
    parser.add_argument(
        "--threshold", "-t", type=float, default=0.85,
        help="Confidence threshold for auto-redaction (default: 0.85).",
    )
    parser.add_argument(
        "--report", "-r", default="reports/detection_report.json",
        help="Path for the detection audit report (default: reports/detection_report.json).",
    )
    parser.add_argument(
        "--evaluate", "-e", action="store_true",
        help="Run evaluation against ground truth after detection.",
    )
    parser.add_argument(
        "--ground-truth", "-g", default="evaluation/ground_truth.json",
        help="Path to ground truth JSON (default: evaluation/ground_truth.json).",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose/debug logging.",
    )

    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger("main")

    # Validate input
    if not os.path.exists(args.input):
        logger.error("Input file not found: %s", args.input)
        sys.exit(1)

    # Ensure output directories exist
    for path in [args.output, args.report]:
        dir_path = os.path.dirname(path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

    # Build pipeline
    logger.info("=" * 60)
    logger.info("PII Redaction Tool")
    logger.info("=" * 60)
    logger.info("Input:     %s", args.input)
    logger.info("Output:    %s", args.output)
    logger.info("Threshold: %.2f", args.threshold)
    logger.info("=" * 60)

    (regex_detector, ner_detector, context_detector,
     merger, scorer, registry, replacement_gen, docx_processor) = build_pipeline()

    # Step 1: Extract text
    logger.info("Loading document...")
    text, segments = docx_processor.extract_text_with_positions(args.input)
    logger.info("Extracted %d characters from %d segments", len(text), len(segments))

    # Step 2: Detect PII
    logger.info("Detecting PII...")
    result = detect_pii(
        text, regex_detector, ner_detector, context_detector,
        merger, scorer, args.threshold,
    )

    # Step 3: Assign replacements
    logger.info("Assigning replacements...")
    assign_replacements(result.entities, replacement_gen)

    # Log summary
    type_counts = {}
    for entity in result.entities:
        type_key = entity.entity_type.value
        type_counts[type_key] = type_counts.get(type_key, 0) + 1

    logger.info("Detection summary:")
    for pii_type, count in sorted(type_counts.items()):
        logger.info("  %-15s: %d", pii_type, count)
    logger.info("  %-15s: %d", "TOTAL", len(result.entities))

    # Step 4: Generate detection report
    logger.info("Generating detection report...")
    MetricsCalculator.generate_detection_report(result.entities, args.report)

    # Step 5: Apply redactions to DOCX
    logger.info("Applying redactions to document...")
    docx_processor.apply_redactions(args.input, args.output, result.entities)
    logger.info("Redacted document saved to: %s", args.output)

    # Step 6: Evaluation (optional)
    if args.evaluate:
        gt_path = args.ground_truth
        if not os.path.exists(gt_path):
            logger.warning("Ground truth file not found: %s. Skipping evaluation.", gt_path)
        else:
            logger.info("Running evaluation...")
            from src.evaluation.evaluator import Evaluator

            evaluator = Evaluator(gt_path)
            eval_results = evaluator.evaluate(result.entities)

            # Generate evaluation report
            os.makedirs("evaluation", exist_ok=True)
            MetricsCalculator.generate_evaluation_report(
                eval_results,
                "evaluation/evaluation_report.md",
                source_document=os.path.basename(args.input),
            )
            MetricsCalculator.save_evaluation_json(
                eval_results,
                "evaluation/evaluation_results.json",
            )

            # Print summary
            overall = eval_results.get("OVERALL", {})
            logger.info("=" * 60)
            logger.info("EVALUATION RESULTS")
            logger.info("=" * 60)
            logger.info("  Accuracy  (Jaccard): %.4f", overall.get("accuracy", 0))
            logger.info("  Precision:           %.4f", overall.get("precision", 0))
            logger.info("  Recall:              %.4f", overall.get("recall", 0))
            logger.info("  F1 Score:            %.4f", overall.get("f1", 0))
            logger.info("=" * 60)

    logger.info("Done!")


if __name__ == "__main__":
    main()
