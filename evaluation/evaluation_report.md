# PII Redaction Evaluation Report

**Generated**: 2026-08-13 17:30:28

---

## Dataset

- **Source Document**: Red_Herring_Prospectus.docx
- **Manually Annotated Entities**: 145
- **PII Categories Evaluated**: 9

---

## Overall Metrics

| Metric | Score |
|--------|-------|
| **Accuracy** (Jaccard Index) | 0.4605 |
| **Precision** | 0.5858 |
| **Recall** | 0.6828 |
| **F1 Score** | 0.6306 |

> **Accuracy Definition**: Jaccard index: TP / (TP + FP + FN). This measures the overlap between detected and ground-truth entity sets. Unlike traditional accuracy which requires true negatives (undefined for entity extraction over arbitrary text spans), the Jaccard index provides a meaningful single metric for set-based evaluation.

---

## Per-Type Metrics

| PII Type | TP | FP | FN | Precision | Recall | F1 |
|----------|----|----|----|-----------+--------+----|
| PERSON | 25 | 27 | 0 | 0.4808 | 1.0000 | 0.6494 |
| EMAIL | 25 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |
| PHONE | 15 | 0 | 8 | 1.0000 | 0.6522 | 0.7895 |
| COMPANY | 13 | 41 | 5 | 0.2407 | 0.7222 | 0.3611 |
| ADDRESS | 0 | 0 | 23 | 0.0000 | 0.0000 | 0.0000 |
| SSN | 4 | 0 | 1 | 1.0000 | 0.8000 | 0.8889 |
| CREDIT_CARD | 4 | 1 | 4 | 0.8000 | 0.5000 | 0.6154 |
| DOB | 8 | 1 | 5 | 0.8889 | 0.6154 | 0.7273 |
| IP_ADDRESS | 5 | 0 | 0 | 1.0000 | 1.0000 | 1.0000 |

---

## Error Analysis

### PERSON

**False Positives (27)**: offer, bharatpe, parekh marg, b-1402, haryana contact, bandra east, floor, nm joshi marg, mittal tower, bapat marg

### PHONE

**Missed (8)**: 914067162222, 912243360000, 912266396880, 912245678901, 919712345678, 912223456789, 919845678901, 912222882460

### COMPANY

**Missed (5)**: icici securities limited, cyril amarchand mangaldas, icici bank limited, remfry & sagar, razorpay software private limited

**False Positives (41)**: maharashtra corporate office unit, the memorandum of association of the company, key managerial, nclt, the offer escrow collection bank, bkc branch, the securities and exchange board of india, us tax, the draft red herring prospectus, prestige meridian

### ADDRESS

**Missed (23)**: 204, prestige lakeside habitat, whitefield, bengaluru – 560066, karnataka, 509, mittal tower, nariman point, mumbai – 400021, no. 8, 2nd main road, koramangala 4th block, bengaluru – 560034, karnataka, flat 601, raheja atlantis, parel, mumbai – 400012, maharashtra, 4th floor, zenith tower, plot no. 42, bandra kurla complex, bandra east, mumbai – 400051, maharashtra, india, one international center, tower 3, 27th floor, senapati bapat marg, elphinstone road, mumbai – 400013, millennium plaza, sector 27, gurugram – 122009, haryana, unit 1201-1205, prestige meridian, mg road, bengaluru – 560001, karnataka, india, no. 15, 3rd cross, indiranagar, bengaluru – 560038, karnataka, house no. 47, sector 15, chandigarh – 160015, punjab

### SSN

**Missed (1)**: 789012345

### CREDIT_CARD

**Missed (4)**: 6011123456789012, 4532012345678901, 5425678901234567, 4532890123456789

**False Positives (1)**: 2345601112345678

### DOB

**Missed (5)**: 30/09/1980, february 9, 1991, 05/06/1968, november 3, 1985, 19/02/1972

**False Positives (1)**: january 5, 2018

---

## Discussion

### Strengths
- Regex-based detection provides high precision for structured PII (email, SSN, credit card, IP).
- Luhn validation eliminates most credit card false positives.
- Context-aware detection helps classify dates as DOB vs. ordinary dates.
- Deterministic replacement ensures referential consistency across the document.

### Known Limitations
- NER model (spaCy en_core_web_sm) may miss some person names, especially Indian names not well-represented in training data.
- Address detection is inherently challenging without a full address parser.
- Company names in financial documents often appear in legal/regulatory contexts that are borderline between PII and public information.
- Phone number detection must balance against financial figures, CIN numbers, and other numeric identifiers common in prospectuses.
- DOCX run boundaries can split PII text, making some replacements imperfect.

### Methodology Notes
- Ground truth was manually curated from the source document.
- Matching uses normalized text comparison (case-insensitive, whitespace-normalized).
- Partial matching is allowed for PERSON and COMPANY types (substring/word-overlap matching).
- Phone matching compares last 10 digits to handle format variations.
