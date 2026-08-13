# PII Redaction Tool

A hybrid detection system designed to identify and redact Personally Identifiable Information (PII) from DOCX documents while preserving original formatting. The tool replaces PII with deterministic fake alternatives, maintaining referential consistency throughout the document (e.g., if "John Doe" is replaced with "Peter Parker", all occurrences will use "Peter Parker").

## Approach

The redaction pipeline employs a multi-layered hybrid architecture to maximize both precision and recall across 9 different PII categories:

1. **Regex Detection**: High-precision regular expressions handle structured PII such as Emails, SSNs, Credit Cards, IP Addresses, and basic Phone Numbers. Complex negative lookbehinds filter out common document artifacts (e.g., financial figures).
2. **Named Entity Recognition (NER)**: The spaCy `en_core_web_sm` model is used to extract unstructured entities like PERSON, COMPANY (ORG), and ADDRESS (GPE/LOC).
3. **Context-Aware Adjustment**: A contextual rule engine examines the text surrounding candidates to adjust confidence scores. For example, a date near "DOB" receives a massive confidence boost, while a phone number near "CIN" or "Order" gets suppressed.
4. **Entity Merging**: Overlapping predictions from different detectors are merged. Ties are broken by confidence, specificity (e.g., EMAIL > PERSON), and span length. Identical exact spans detected by multiple models receive a confidence boost.
5. **Deterministic Replacement**: Uses a `PIIRegistry` backed by the `Faker` library seeded with a fixed value to ensure replacements are realistic, contextually appropriate (e.g., matching email names to the fake person name), and consistent document-wide.
6. **In-place Redaction**: The `python-docx` based processor targets specific runs in the document XML, handling cases where PII spans across multiple formatting runs to preserve styling (bold, italic, font, etc.).

## Evaluation Approach

The tool includes a robust evaluation suite `evaluator.py` that compares detected entities against a manually curated `ground_truth.json`. 

- **Metrics**: Calculates True Positives (TP), False Positives (FP), False Negatives (FN), Precision, Recall, and F1 Score for each PII type. 
- **Matching Logic**: Uses type-aware normalization (e.g., comparing phones and SSNs strictly by digits) and allows for partial overlapping matches to account for minor tokenization differences between the NER model and human annotation.
- **Set-based Metrics**: Evaluates performance using the Jaccard Index for overall accuracy.

## Tradeoffs and Observations (False Positives / False Negatives)

- **Addresses (High FN)**: Finding complete postal addresses using just NER is notoriously difficult since the `en_core_web_sm` model usually only extracts smaller entities (GPE) like "Mumbai" instead of the full multi-line address. Recall for full addresses is low.
- **Company Names (High FP/FN)**: Financial documents like a Prospectus are saturated with entities that look like companies (e.g., "The Escrow Collection Bank", "Refund Bank", "Retail Individual Investors"). Distinguishing between a generic capitalized term and a specific legal entity without deep domain context leads to false positives.
- **Phone Numbers (Moderate FN)**: Landline numbers and numbers split across table cells can be challenging to reliably parse with regex without matching general numerical identifiers like CINs or application IDs.
- **DOCX Run Splitting**: Microsoft Word frequently splits text into multiple `Run` elements mid-word for invisible formatting reasons. While the tool handles spanning runs, extreme fragmentation can sometimes obscure regex matches during initial text extraction.
- **Speed vs Accuracy Tradeoff**: The lightweight `en_core_web_sm` model is fast but less accurate on Indian names and complex contexts compared to transformer-based models (`en_core_web_trf`), representing a deliberate speed/efficiency tradeoff.

## Deliverables

1. Source code in `src/` and `main.py`
2. Redacted output: `output/redacted_prospectus.docx`
3. Evaluation outputs: `reports/detection_report.json` and `evaluation/evaluation_report.md`

## Usage

```bash
# Redact a document
python main.py --input Red_Herring_Prospectus.docx --output output/redacted_prospectus.docx

# Redact and run evaluation against ground truth
python main.py --input Red_Herring_Prospectus.docx --output output/redacted_prospectus.docx --evaluate
```
