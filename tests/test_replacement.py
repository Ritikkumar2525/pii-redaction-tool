"""Tests for deterministic replacement and entity merging."""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.entity import PIIEntity, PIIType
from src.core.registry import PIIRegistry
from src.core.replacement import ReplacementGenerator
from src.core.merger import EntityMerger


class TestDeterministicReplacement:
    """Verify that the same PII always gets the same fake replacement."""

    def test_same_person_same_replacement(self):
        registry = PIIRegistry()
        gen = ReplacementGenerator(registry)
        r1 = gen.generate("Rashi Patil", "rashi patil", PIIType.PERSON)
        r2 = gen.generate("Rashi Patil", "rashi patil", PIIType.PERSON)
        assert r1 == r2

    def test_different_persons_different_replacements(self):
        registry = PIIRegistry()
        gen = ReplacementGenerator(registry)
        r1 = gen.generate("Rashi Patil", "rashi patil", PIIType.PERSON)
        r2 = gen.generate("Rohan Dey", "rohan dey", PIIType.PERSON)
        assert r1 != r2

    def test_same_email_same_replacement(self):
        registry = PIIRegistry()
        gen = ReplacementGenerator(registry)
        r1 = gen.generate("test@example.com", "test@example.com", PIIType.EMAIL)
        r2 = gen.generate("test@example.com", "test@example.com", PIIType.EMAIL)
        assert r1 == r2

    def test_same_phone_same_replacement(self):
        registry = PIIRegistry()
        gen = ReplacementGenerator(registry)
        r1 = gen.generate("+91 9876543210", "+919876543210", PIIType.PHONE)
        r2 = gen.generate("+91 9876543210", "+919876543210", PIIType.PHONE)
        assert r1 == r2

    def test_replacement_type_appropriate(self):
        registry = PIIRegistry()
        gen = ReplacementGenerator(registry)

        person = gen.generate("John Doe", "john doe", PIIType.PERSON)
        assert len(person.split()) >= 2  # Should be a full name

        email = gen.generate("test@example.com", "test@example.com", PIIType.EMAIL)
        assert "@" in email  # Should contain @
        assert "example.com" in email  # Should use example.com

        phone = gen.generate("+91 9876543210", "+919876543210", PIIType.PHONE)
        assert phone.startswith("+91")  # Should preserve format

        ip = gen.generate("192.168.1.1", "192.168.1.1", PIIType.IP_ADDRESS)
        assert ip.count(".") == 3  # Should be valid IP format

    def test_multiple_occurrences_consistent(self):
        """If a name appears 5 times, all should get the same replacement."""
        registry = PIIRegistry()
        gen = ReplacementGenerator(registry)
        replacements = []
        for _ in range(5):
            r = gen.generate("Priya Sharma", "priya sharma", PIIType.PERSON)
            replacements.append(r)
        assert len(set(replacements)) == 1


class TestEntityMerger:
    def test_non_overlapping_kept(self):
        entities = [
            PIIEntity("John Doe", PIIType.PERSON, 0, 8, "NER", 0.90),
            PIIEntity("test@example.com", PIIType.EMAIL, 20, 36, "Regex", 0.99),
        ]
        merged = EntityMerger.merge_entities(entities)
        assert len(merged) == 2

    def test_overlapping_resolved_by_confidence(self):
        entities = [
            PIIEntity("John Doe", PIIType.PERSON, 0, 8, "NER", 0.90),
            PIIEntity("John Doe", PIIType.PERSON, 0, 8, "Regex", 0.95),
        ]
        merged = EntityMerger.merge_entities(entities)
        assert len(merged) == 1
        assert merged[0].confidence >= 0.95  # Boosted due to multi-detection

    def test_overlapping_resolved_by_specificity(self):
        """More specific type (EMAIL > PERSON) should win when overlapping."""
        entities = [
            PIIEntity("john.doe@example.com", PIIType.EMAIL, 0, 20, "Regex", 0.99),
            PIIEntity("john.doe", PIIType.PERSON, 0, 8, "NER", 0.88),
        ]
        merged = EntityMerger.merge_entities(entities)
        assert len(merged) == 1
        assert merged[0].entity_type == PIIType.EMAIL

    def test_overlapping_longer_span_preferred(self):
        """When confidence and type are similar, longer span wins."""
        entities = [
            PIIEntity("Rajesh Kumar Agarwal", PIIType.PERSON, 0, 19, "NER", 0.90),
            PIIEntity("Rajesh Kumar", PIIType.PERSON, 0, 12, "NER", 0.88),
        ]
        merged = EntityMerger.merge_entities(entities)
        assert len(merged) == 1
        assert merged[0].text == "Rajesh Kumar Agarwal"

    def test_empty_list(self):
        assert EntityMerger.merge_entities([]) == []

    def test_single_entity(self):
        entities = [PIIEntity("Test", PIIType.PERSON, 0, 4, "NER", 0.90)]
        merged = EntityMerger.merge_entities(entities)
        assert len(merged) == 1
