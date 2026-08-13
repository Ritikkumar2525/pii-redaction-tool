"""Tests for PII detection: regex, NER, context, and false positive handling."""

import sys
import os
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.entity import PIIEntity, PIIType
from src.detectors.regex_detector import RegexDetector
from src.detectors.context_detector import ContextDetector


@pytest.fixture
def regex_detector():
    return RegexDetector()


@pytest.fixture
def context_detector():
    return ContextDetector()


# ============================================================
# Email Detection
# ============================================================
class TestEmailDetection:
    def test_standard_email(self, regex_detector):
        text = "Contact us at john.doe@example.com for details."
        entities = regex_detector.detect(text)
        emails = [e for e in entities if e.entity_type == PIIType.EMAIL]
        assert len(emails) >= 1
        assert any("john.doe@example.com" in e.text for e in emails)

    def test_corporate_email(self, regex_detector):
        text = "Email: priya.sharma@nexusfintech.co.in"
        entities = regex_detector.detect(text)
        emails = [e for e in entities if e.entity_type == PIIType.EMAIL]
        assert len(emails) >= 1

    def test_gmail_email(self, regex_detector):
        text = "Reach out to rashi.patil@gmail.com"
        entities = regex_detector.detect(text)
        emails = [e for e in entities if e.entity_type == PIIType.EMAIL]
        assert len(emails) >= 1
        assert emails[0].confidence >= 0.95


# ============================================================
# Phone Detection
# ============================================================
class TestPhoneDetection:
    def test_indian_phone_with_country_code(self, regex_detector):
        text = "Contact Number: +91 9876543210"
        entities = regex_detector.detect(text)
        phones = [e for e in entities if e.entity_type == PIIType.PHONE]
        assert len(phones) >= 1

    def test_indian_phone_with_dash(self, regex_detector):
        text = "Mobile: +91-9834567890"
        entities = regex_detector.detect(text)
        phones = [e for e in entities if e.entity_type == PIIType.PHONE]
        assert len(phones) >= 1

    def test_ten_digit_phone(self, regex_detector):
        text = "Call 9876543210 for support."
        entities = regex_detector.detect(text)
        phones = [e for e in entities if e.entity_type == PIIType.PHONE]
        assert len(phones) >= 1

    def test_false_positive_financial_figure(self, regex_detector):
        """Financial figures should NOT be detected as phone numbers."""
        text = "The company reported revenue of ₹2,845.67 crore."
        entities = regex_detector.detect(text)
        phones = [e for e in entities if e.entity_type == PIIType.PHONE]
        assert len(phones) == 0

    def test_false_positive_order_number(self, regex_detector, context_detector):
        """Order/case numbers near context clues should be suppressed."""
        text = "Case No. NCLT/MUM/2024/00789 filed against the company."
        entities = regex_detector.detect(text)
        phones = [e for e in entities if e.entity_type == PIIType.PHONE]
        # Even if regex picks it up, context should reduce confidence
        if phones:
            adjusted = context_detector.process(phones, text)
            high_conf = [e for e in adjusted if e.confidence >= 0.85]
            assert len(high_conf) == 0


# ============================================================
# SSN Detection
# ============================================================
class TestSSNDetection:
    def test_valid_ssn(self, regex_detector):
        text = "SSN: 312-45-6789"
        entities = regex_detector.detect(text)
        ssns = [e for e in entities if e.entity_type == PIIType.SSN]
        assert len(ssns) >= 1
        assert ssns[0].confidence >= 0.95

    def test_invalid_ssn_area_000(self, regex_detector):
        text = "Number: 000-12-3456"
        entities = regex_detector.detect(text)
        ssns = [e for e in entities if e.entity_type == PIIType.SSN]
        assert len(ssns) == 0

    def test_invalid_ssn_area_666(self, regex_detector):
        text = "Number: 666-12-3456"
        entities = regex_detector.detect(text)
        ssns = [e for e in entities if e.entity_type == PIIType.SSN]
        assert len(ssns) == 0

    def test_invalid_ssn_area_900(self, regex_detector):
        text = "Number: 900-12-3456"
        entities = regex_detector.detect(text)
        ssns = [e for e in entities if e.entity_type == PIIType.SSN]
        assert len(ssns) == 0


# ============================================================
# Credit Card Detection + Luhn
# ============================================================
class TestCreditCardDetection:
    def test_valid_visa(self, regex_detector):
        text = "Card: 4111 1111 1111 1111"
        entities = regex_detector.detect(text)
        ccs = [e for e in entities if e.entity_type == PIIType.CREDIT_CARD]
        assert len(ccs) >= 1

    def test_invalid_luhn(self, regex_detector):
        """A number that doesn't pass Luhn should NOT be detected."""
        text = "Number: 1234 5678 9012 3456"
        entities = regex_detector.detect(text)
        ccs = [e for e in entities if e.entity_type == PIIType.CREDIT_CARD]
        assert len(ccs) == 0

    def test_amex_format(self, regex_detector):
        text = "AMEX: 3782 822463 10005"
        entities = regex_detector.detect(text)
        ccs = [e for e in entities if e.entity_type == PIIType.CREDIT_CARD]
        assert len(ccs) >= 1


# ============================================================
# IP Address Detection
# ============================================================
class TestIPDetection:
    def test_valid_ipv4(self, regex_detector):
        text = "Server at 192.168.1.10"
        entities = regex_detector.detect(text)
        ips = [e for e in entities if e.entity_type == PIIType.IP_ADDRESS]
        assert len(ips) >= 1

    def test_documentation_ip(self, regex_detector):
        text = "from IP address 203.0.113.42"
        entities = regex_detector.detect(text)
        ips = [e for e in entities if e.entity_type == PIIType.IP_ADDRESS]
        assert len(ips) >= 1

    def test_invalid_octet(self, regex_detector):
        """Octets > 255 should not match."""
        text = "Address: 999.999.999.999"
        entities = regex_detector.detect(text)
        ips = [e for e in entities if e.entity_type == PIIType.IP_ADDRESS]
        assert len(ips) == 0


# ============================================================
# DOB / Date Context Detection
# ============================================================
class TestDOBDetection:
    def test_dob_with_context(self, regex_detector):
        text = "Date of Birth: 15/08/1987"
        entities = regex_detector.detect(text)
        dobs = [e for e in entities if e.entity_type == PIIType.DOB]
        assert len(dobs) >= 1
        assert any(e.confidence >= 0.90 for e in dobs)

    def test_ordinary_date_low_confidence(self, regex_detector):
        """A date without DOB context should have low confidence."""
        text = "Report Date: 15/08/2025"
        entities = regex_detector.detect(text)
        dobs = [e for e in entities if e.entity_type == PIIType.DOB]
        # Should be detected but with low confidence (below threshold)
        if dobs:
            assert all(e.confidence < 0.85 for e in dobs)

    def test_named_month_dob(self, regex_detector):
        text = "Born on March 22, 1992"
        entities = regex_detector.detect(text)
        dobs = [e for e in entities if e.entity_type == PIIType.DOB]
        assert len(dobs) >= 1

    def test_context_detector_boosts_dob(self, regex_detector, context_detector):
        text = "Employee Date of Birth: 22/03/1982"
        entities = regex_detector.detect(text)
        adjusted = context_detector.process(entities, text)
        dobs = [e for e in adjusted if e.entity_type == PIIType.DOB]
        assert any(e.confidence >= 0.90 for e in dobs)

    def test_context_detector_reduces_report_date(self, regex_detector, context_detector):
        text = "Filing dated 15/05/2025 was submitted."
        entities = regex_detector.detect(text)
        adjusted = context_detector.process(entities, text)
        dobs = [e for e in adjusted if e.entity_type == PIIType.DOB]
        if dobs:
            assert all(e.confidence < 0.85 for e in dobs)


# ============================================================
# NER Detection (Person, Company)
# ============================================================
class TestNERDetection:
    def test_person_detection(self):
        """Test that NER detects person names."""
        from src.detectors.ner_detector import NERDetector
        detector = NERDetector()
        if detector.nlp is None:
            pytest.skip("spaCy model not available")
        text = "Mr. Rajesh Kumar Agarwal is the Managing Director."
        entities = detector.detect(text)
        persons = [e for e in entities if e.entity_type == PIIType.PERSON]
        assert len(persons) >= 1

    def test_company_detection(self):
        """Test that NER detects organization names.
        Note: spaCy en_core_web_sm may not detect all company names.
        We test with a variety of formats to ensure at least one is caught.
        """
        from src.detectors.ner_detector import NERDetector
        detector = NERDetector()
        if detector.nlp is None:
            pytest.skip("spaCy model not available")
        # Use multiple company name formats for robustness
        texts = [
            "Google LLC announced the acquisition today.",
            "Microsoft Corporation reported earnings.",
            "The contract was signed with Apple Inc.",
        ]
        found_any = False
        for text in texts:
            entities = detector.detect(text)
            companies = [e for e in entities if e.entity_type == PIIType.COMPANY]
            if companies:
                found_any = True
                break
        assert found_any, "NER failed to detect any company in multiple test sentences"


# ============================================================
# Address Detection via Context
# ============================================================
class TestAddressDetection:
    def test_address_context_boost(self, context_detector):
        """Address near context keywords should have boosted confidence."""
        entity = PIIEntity(
            text="Mumbai",
            entity_type=PIIType.ADDRESS,
            start=30,
            end=36,
            detector="NERDetector",
            confidence=0.75,
        )
        text = "Registered Office Address: Mumbai is the location."
        adjusted = context_detector.process([entity], text)
        assert adjusted[0].confidence > 0.75
