"""Regex-based PII detector for structured data types."""

import re
import logging
from typing import List

from src.core.entity import PIIEntity, PIIType
from src.detectors.base_detector import BaseDetector

logger = logging.getLogger(__name__)


class RegexDetector(BaseDetector):
    """Detector for structured PII using regular expressions.

    Handles: EMAIL, PHONE, SSN, CREDIT_CARD, IP_ADDRESS, DOB.
    Uses validation and context checks to minimize false positives.
    """

    def __init__(self):
        # Email: standard format with domain
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'
        )

        # Phone: Indian (+91 / 91) and bare 10-digit starting with 6-9
        # Deliberately simple — false positives filtered by _is_false_positive_phone()
        self.phone_pattern = re.compile(
            r'(?<![0-9,.])'                # Not preceded by digit/comma/dot (financial)
            r'(?:\+?91[\-\s]?)?'           # Optional +91 prefix
            r'[6-9]\d{9}'                  # 10 digits starting with 6-9
            r'(?!\d)'                       # Not followed by more digits
        )

        # Landline: +91 XX XXXX XXXX format
        self.landline_pattern = re.compile(
            r'\+91\s+\d{2,3}\s+\d{3,4}\s+\d{4}\b'
        )

        # SSN: XXX-XX-XXXX
        self.ssn_pattern = re.compile(r'\b(\d{3})-(\d{2})-(\d{4})\b')

        # Credit Card: various formats (4-4-4-4, 4-6-5 AMEX, continuous)
        self.cc_pattern = re.compile(
            r'\b(?:'
            r'\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}'  # 4-4-4-4
            r'|\d{4}[\s\-]?\d{6}[\s\-]?\d{5}'              # 4-6-5 (AMEX)
            r'|\d{13,19}'                                    # Continuous
            r')\b'
        )

        # IPv4: each octet 0-255
        self.ip_pattern = re.compile(
            r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
            r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
        )

        # Dates: multiple formats
        self.date_pattern = re.compile(
            r'\b(?:'
            r'\d{1,2}[/\-]\d{1,2}[/\-]\d{4}'              # DD/MM/YYYY etc.
            r'|\d{4}[/\-]\d{1,2}[/\-]\d{1,2}'              # YYYY-MM-DD
            r'|(?:January|February|March|April|May|June|July|August|'
            r'September|October|November|December)\s+\d{1,2},?\s+\d{4}'
            r')\b',
            re.IGNORECASE,
        )

        # Keywords that indicate a date is a DOB
        self.dob_keywords = [
            'date of birth', 'dob', 'born', 'birth date', 'birthdate', 'age',
        ]

    @property
    def name(self) -> str:
        return "RegexDetector"

    def detect(self, text: str) -> List[PIIEntity]:
        """Run all regex patterns against the text."""
        entities: List[PIIEntity] = []

        # --- EMAIL ---
        for match in self.email_pattern.finditer(text):
            entities.append(PIIEntity(
                text=match.group(0),
                entity_type=PIIType.EMAIL,
                start=match.start(),
                end=match.end(),
                detector=self.name,
                confidence=0.99,
                context=self._get_context(text, match.start(), match.end()),
            ))

        # --- PHONE (mobile) ---
        for match in self.phone_pattern.finditer(text):
            if not self._is_false_positive_phone(text, match.start(), match.end()):
                entities.append(PIIEntity(
                    text=match.group(0),
                    entity_type=PIIType.PHONE,
                    start=match.start(),
                    end=match.end(),
                    detector=self.name,
                    confidence=0.93,
                    context=self._get_context(text, match.start(), match.end()),
                ))

        # --- PHONE (landline) ---
        for match in self.landline_pattern.finditer(text):
            if not self._is_false_positive_phone(text, match.start(), match.end()):
                entities.append(PIIEntity(
                    text=match.group(0),
                    entity_type=PIIType.PHONE,
                    start=match.start(),
                    end=match.end(),
                    detector=self.name,
                    confidence=0.91,
                    context=self._get_context(text, match.start(), match.end()),
                ))

        # --- SSN ---
        for match in self.ssn_pattern.finditer(text):
            area, group, serial = match.groups()
            area_int = int(area)
            # Validate SSN ranges
            if (area != '000' and area != '666'
                    and not (900 <= area_int <= 999)
                    and group != '00' and serial != '0000'):
                entities.append(PIIEntity(
                    text=match.group(0),
                    entity_type=PIIType.SSN,
                    start=match.start(),
                    end=match.end(),
                    detector=self.name,
                    confidence=0.97,
                    context=self._get_context(text, match.start(), match.end()),
                ))

        # --- CREDIT CARD ---
        for match in self.cc_pattern.finditer(text):
            cc_text = match.group(0)
            if self._luhn_check(cc_text):
                entities.append(PIIEntity(
                    text=cc_text,
                    entity_type=PIIType.CREDIT_CARD,
                    start=match.start(),
                    end=match.end(),
                    detector=self.name,
                    confidence=0.98,
                    context=self._get_context(text, match.start(), match.end()),
                ))

        # --- IP ADDRESS ---
        for match in self.ip_pattern.finditer(text):
            ip_text = match.group(0)
            # Skip version-like patterns (e.g., "Python 3.8.13")
            ctx_before = text[max(0, match.start() - 15):match.start()].lower()
            if 'version' in ctx_before or ctx_before.rstrip().endswith('v'):
                continue
            entities.append(PIIEntity(
                text=ip_text,
                entity_type=PIIType.IP_ADDRESS,
                start=match.start(),
                end=match.end(),
                detector=self.name,
                confidence=0.97,
                context=self._get_context(text, match.start(), match.end()),
            ))

        # --- DOB / DATE ---
        for match in self.date_pattern.finditer(text):
            ctx_before = text[max(0, match.start() - 100):match.start()].lower()
            is_dob = any(kw in ctx_before for kw in self.dob_keywords)
            entities.append(PIIEntity(
                text=match.group(0),
                entity_type=PIIType.DOB,
                start=match.start(),
                end=match.end(),
                detector=self.name,
                confidence=0.96 if is_dob else 0.30,
                context=self._get_context(text, match.start(), match.end()),
            ))

        return entities

    def _is_false_positive_phone(self, text: str, start: int, end: int) -> bool:
        """Check if a phone candidate is actually a financial/document number."""
        ctx_before = text[max(0, start - 30):start].lower()

        # Financial context
        financial_cues = [
            '₹', 'rs.', 'rs ', 'inr', 'crore', 'lakh', 'million',
            'revenue', 'profit', 'expense', 'income', 'cost',
        ]
        if any(cue in ctx_before for cue in financial_cues):
            return True

        # Document/ID context — but NOT if preceded by phone/contact/mobile
        phone_context = ['phone', 'contact', 'mobile', 'tel', 'fax']
        has_phone_context = any(kw in ctx_before for kw in phone_context)

        doc_cues = [
            'account', 'cin', 'registration', 'section', 'page',
            'ifsc', 'pan', '#', 'membership',
        ]
        if not has_phone_context and any(cue in ctx_before for cue in doc_cues):
            return True

        # Preceded by comma+digits (part of larger number like 2,85,00,000)
        if start > 0 and text[start - 1] in (',', '.'):
            return True

        # Part of a financial figure with commas
        ctx_around = text[max(0, start - 5):min(len(text), end + 5)]
        if re.search(r'\d{1,3}(?:,\d{2,3})+', ctx_around):
            return True

        return False

    @staticmethod
    def _luhn_check(card_text: str) -> bool:
        """Validate a card number using the Luhn algorithm."""
        digits = [int(c) for c in card_text if c.isdigit()]
        if not digits or len(digits) < 13 or len(digits) > 19:
            return False

        checksum = 0
        for i, d in enumerate(reversed(digits)):
            if i % 2 == 1:
                d *= 2
                if d > 9:
                    d -= 9
            checksum += d
        return checksum % 10 == 0
