import re

def luhn_check(card_number: str) -> bool:
    """Validate credit card number using Luhn algorithm.
    Input: digits-only string.
    """
    if not card_number.isdigit():
        return False
    digits = [int(c) for c in card_number]
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0

def validate_ip_octet(ip: str) -> bool:
    """Validate IPv4 address: each octet 0-255, exactly 4 octets."""
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    for part in parts:
        if not part.isdigit():
            return False
        num = int(part)
        if num < 0 or num > 255:
            return False
        if str(num) != part:  # Prevent leading zeros from bypassing validation
            return False
    return True

def validate_ssn(ssn: str) -> bool:
    """Validate US SSN: area not 000/666/900-999, group not 00, serial not 0000."""
    ssn = ssn.replace("-", "").replace(" ", "")
    if len(ssn) != 9 or not ssn.isdigit():
        return False
    area = ssn[:3]
    group = ssn[3:5]
    serial = ssn[5:]
    if area == "000" or area == "666" or int(area) >= 900:
        return False
    if group == "00":
        return False
    if serial == "0000":
        return False
    return True

def validate_phone(phone: str) -> bool:
    """Validate phone number:
    - If starts with +91 or 91, remaining should be 10 digits starting with 6-9
    - If 10 digits, should start with 6-9
    - General: 10-15 digits total
    """
    phone = re.sub(r'[^0-9+]', '', phone)
    if phone.startswith('+91'):
        phone = phone[3:]
        if len(phone) == 10 and phone[0] in '6789':
            return True
        return False
    elif phone.startswith('91') and len(phone) > 10:
        phone = phone[2:]
        if len(phone) == 10 and phone[0] in '6789':
            return True
        return False
    
    if len(phone) == 10:
        return phone[0] in '6789'
    
    return 10 <= len(phone) <= 15

def validate_email(email: str) -> bool:
    """Basic email validation: has @, valid domain structure."""
    if '@' not in email:
        return False
    try:
        local, domain = email.rsplit('@', 1)
    except ValueError:
        return False
        
    if not local or not domain:
        return False
    if '.' not in domain:
        return False
    domain_parts = domain.split('.')
    for part in domain_parts:
        if not part:
            return False
    return True
