# 🛡️ PII Redaction Tool

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://pii-redactiontool-x.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

> **Live Demo**: [Test the tool in your browser!](https://pii-redactiontool-x.streamlit.app/)

A production-ready hybrid detection system designed to identify and redact Personally Identifiable Information (PII) from DOCX documents while preserving original formatting. The tool replaces PII with deterministic fake alternatives, maintaining referential consistency throughout the document.

---

## 📸 Screenshots

*(To display the screenshots you took, create a `docs` folder in your repository and upload your images as `dashboard.png` and `results.png`)*

![Web Interface Dashboard](docs/dashboard.png)  
*Upload and process documents via the intuitive Web UI.*

![Detailed Detection Analytics](docs/results.png)  
*Review comprehensive analytics and deterministic replacements.*

---

## 🧠 Approach & Architecture

The redaction pipeline employs a multi-layered hybrid architecture to maximize both precision and recall across **9 different PII categories**:

1. **Regex Detection**: High-precision regular expressions handle structured PII such as Emails, SSNs, Credit Cards, IP Addresses, and Phone Numbers. Complex negative lookbehinds filter out common document artifacts (e.g., financial figures).
2. **Named Entity Recognition (NER)**: The spaCy `en_core_web_sm` model is used to extract unstructured entities like PERSON, COMPANY (ORG), and ADDRESS (GPE/LOC).
3. **Context-Aware Rules Engine**: Examines the text surrounding candidates to adjust confidence scores. For example, a date near "DOB" receives a massive confidence boost, while a phone number near "CIN" gets suppressed.
4. **Entity Merging**: Resolves overlapping predictions from different detectors based on confidence, specificity (e.g., EMAIL > PERSON), and span length.
5. **Deterministic Replacement**: Uses a `PIIRegistry` backed by the `Faker` library to ensure replacements are realistic, contextually appropriate (e.g., matching email names to the fake person name), and consistent document-wide.
6. **In-place XML Redaction**: The `python-docx` based processor targets specific runs in the DOCX XML, handling cases where PII spans across multiple formatting runs to preserve styling (bold, italic, fonts, tables).

---

## 📊 Evaluation & Metrics

The tool includes a robust evaluation suite `evaluator.py` that compares detected entities against a manually curated ground truth dataset.

- **Metrics Tracked**: True Positives (TP), False Positives (FP), False Negatives (FN), Precision, Recall, and F1 Score for each PII type.
- **Advanced Matching Logic**: Uses type-aware normalization (e.g., comparing phones and SSNs strictly by digits) and allows for partial overlapping matches to account for tokenization boundaries.
- **Overall Accuracy**: Evaluates comprehensive document-wide performance using the Jaccard Index.

### Known Tradeoffs (False Positives / Negatives)

*   **Addresses (High FN)**: Finding complete, multi-line postal addresses using lightweight NER is difficult; the model often extracts only city names instead of the full address block.
*   **Company Names (High FP)**: Financial documents are saturated with generic capitalized entities (e.g., "The Escrow Collection Bank"). Distinguishing these from specific legal entities without deep domain context can lead to false positives.
*   **Speed vs. Accuracy**: The lightweight `en_core_web_sm` model is fast but less accurate on complex Indian names compared to transformer-based models (`en_core_web_trf`), representing a deliberate speed/efficiency tradeoff.

---

## 💻 Usage

### Web Interface (Recommended)
You can run the interactive Streamlit dashboard locally:
```bash
pip install -r requirements.txt
streamlit run app.py
```

### Command Line Interface
Run the tool directly from the terminal for batch processing:
```bash
# Redact a document
python main.py --input Red_Herring_Prospectus.docx --output output/redacted_prospectus.docx

# Redact and generate an evaluation report against ground truth
python main.py --input Red_Herring_Prospectus.docx --output output/redacted_prospectus.docx --evaluate
```

---

## 📁 Repository Structure

*   `app.py`: Streamlit Web UI
*   `main.py`: CLI Entry point and orchestrator
*   `src/`: Core pipeline (Detectors, Context Engine, Registry, XML Processor)
*   `tests/`: Comprehensive unit and integration test suite
*   `evaluation/`: Ground truth data and metrics calculator
