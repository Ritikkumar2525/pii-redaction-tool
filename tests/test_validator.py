"""Tests for validators: Luhn, IP octet, SSN range, phone."""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.validator import luhn_check, validate_ip_octet, validate_ssn, validate_phone, validate_email


class TestLuhnCheck:
    def test_valid_visa(self):
        assert luhn_check("4111111111111111") is True

    def test_valid_mastercard(self):
        assert luhn_check("5500000000000004") is True

    def test_valid_amex(self):
        assert luhn_check("378282246310005") is True

    def test_invalid_number(self):
        assert luhn_check("1234567890123456") is False

    def test_too_short(self):
        assert luhn_check("123456") is False

    def test_empty(self):
        assert luhn_check("") is False


class TestIPValidation:
    def test_valid_ip(self):
        assert validate_ip_octet("192.168.1.1") is True

    def test_valid_ip_zeros(self):
        assert validate_ip_octet("0.0.0.0") is True

    def test_valid_ip_max(self):
        assert validate_ip_octet("255.255.255.255") is True

    def test_invalid_octet_over(self):
        assert validate_ip_octet("256.1.1.1") is False

    def test_too_few_octets(self):
        assert validate_ip_octet("192.168.1") is False

    def test_too_many_octets(self):
        assert validate_ip_octet("192.168.1.1.1") is False


class TestSSNValidation:
    def test_valid_ssn(self):
        assert validate_ssn("312-45-6789") is True

    def test_invalid_area_000(self):
        assert validate_ssn("000-12-3456") is False

    def test_invalid_area_666(self):
        assert validate_ssn("666-12-3456") is False

    def test_invalid_area_900(self):
        assert validate_ssn("900-12-3456") is False

    def test_invalid_group_00(self):
        assert validate_ssn("123-00-4567") is False

    def test_invalid_serial_0000(self):
        assert validate_ssn("123-45-0000") is False


class TestPhoneValidation:
    def test_indian_with_country_code(self):
        assert validate_phone("+919876543210") is True

    def test_ten_digit_indian(self):
        assert validate_phone("9876543210") is True

    def test_starts_with_wrong_digit(self):
        assert validate_phone("1234567890") is False

    def test_too_short(self):
        assert validate_phone("12345") is False


class TestEmailValidation:
    def test_valid_email(self):
        assert validate_email("john.doe@example.com") is True

    def test_valid_corporate(self):
        assert validate_email("priya.sharma@nexusfintech.co.in") is True

    def test_no_at_sign(self):
        assert validate_email("johndoe.example.com") is False

    def test_no_domain(self):
        assert validate_email("john@") is False
