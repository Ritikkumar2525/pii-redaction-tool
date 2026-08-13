import random
import logging
from datetime import datetime, timedelta
from faker import Faker
from src.core.entity import PIIType
from src.core.registry import PIIRegistry

logger = logging.getLogger(__name__)

# Predefined names for PERSON replacement
FAKE_NAMES = [
    'John Doe', 'Jane Smith', 'Peter Parker', 'Mary Johnson', 'James Brown',
    'Patricia Garcia', 'Robert Miller', 'Linda Davis', 'Michael Rodriguez',
    'Elizabeth Martinez', 'William Hernandez', 'Barbara Lopez', 'David Gonzalez',
    'Susan Wilson', 'Richard Anderson', 'Jessica Thomas', 'Joseph Taylor',
    'Sarah Moore', 'Charles Jackson', 'Karen Martin'
]

FAKE_COMPANIES = [
    'Acme Corp', 'Globex Corporation', 'Soylent Corp', 'Initech',
    'Umbrella Corporation', 'Stark Industries', 'Wayne Enterprises',
    'Cyberdyne Systems', 'Massive Dynamic', 'Hooli'
]

FAKE_ADDRESSES = [
    '123 Fake St, Springfield, SP 12345',
    '456 Mockingbird Ln, Faketown, FK 67890',
    '789 Null Ave, Void City, VC 11111',
    '321 Test Blvd, Sampleville, SV 22222',
    '654 Demo Rd, Exampleton, EX 33333'
]

IP_RANGES = ['192.0.2.', '198.51.100.', '203.0.113.']

class ReplacementGenerator:
    """Generates consistent fake replacements for PII."""
    
    def __init__(self, registry: PIIRegistry):
        self.registry = registry
        self.faker = Faker()
        Faker.seed(42)
        random.seed(42)
        self._name_index = 0
        self._company_index = 0
        self._address_index = 0
        
    def _get_next_name(self) -> str:
        name = FAKE_NAMES[self._name_index % len(FAKE_NAMES)]
        self._name_index += 1
        return name
        
    def _get_next_company(self, original: str) -> str:
        base = FAKE_COMPANIES[self._company_index % len(FAKE_COMPANIES)]
        self._company_index += 1
        
        # Preserve suffix if possible
        lower_orig = original.lower()
        suffix = ""
        for suf in ['pvt ltd', 'llp', 'limited', 'inc', 'corp', 'llc']:
            if lower_orig.endswith(suf):
                # match case of original suffix if possible, but simplicity rules
                suffix = " " + original[-len(suf):]
                break
        return base + suffix
        
    def _get_next_address(self) -> str:
        addr = FAKE_ADDRESSES[self._address_index % len(FAKE_ADDRESSES)]
        self._address_index += 1
        return addr
        
    def generate(self, original_text: str, normalized_value: str, entity_type: PIIType) -> str:
        """Generate or retrieve a replacement for the given PII."""
        existing = self.registry.get_replacement(normalized_value, entity_type)
        if existing is not None:
            return existing
            
        replacement = self._generate_new(original_text, normalized_value, entity_type)
        self.registry.register(normalized_value, entity_type, replacement)
        return replacement
        
    def _generate_new(self, original_text: str, normalized_value: str, entity_type: PIIType) -> str:
        if entity_type == PIIType.PERSON:
            name = self._get_next_name()
            # Match case pattern roughly
            if original_text.isupper():
                return name.upper()
            elif original_text.islower():
                return name.lower()
            return name
            
        elif entity_type == PIIType.EMAIL:
            # Try to derive from name if we know it
            local_part = original_text.split('@')[0]
            
            # Normalize local part by replacing dots and underscores with spaces
            # so 'rashi.patil' matches 'rashi patil' in the registry
            normalized_local = local_part.replace('.', ' ').replace('_', ' ')
            
            person_replacement = self.registry.get_person_replacement(normalized_local)
            if not person_replacement:
                # Also try original local_part just in case
                person_replacement = self.registry.get_person_replacement(local_part)
            
            if person_replacement:
                base = person_replacement.lower().replace(' ', '.')
            else:
                base = self._get_next_name().lower().replace(' ', '.')
            return f"{base}@example.com"
            
        elif entity_type == PIIType.PHONE:
            digits = "".join([str(random.randint(0, 9)) for _ in range(9)])
            return f"+91 9{digits}"
            
        elif entity_type == PIIType.COMPANY:
            return self._get_next_company(original_text)
            
        elif entity_type == PIIType.ADDRESS:
            return self._get_next_address()
            
        elif entity_type == PIIType.SSN:
            # Generate valid format fake SSN 
            area = str(random.randint(101, 665)).zfill(3)
            group = str(random.randint(1, 99)).zfill(2)
            serial = str(random.randint(1, 9999)).zfill(4)
            return f"{area}-{group}-{serial}"
            
        elif entity_type == PIIType.CREDIT_CARD:
            return self.faker.credit_card_number()
            
        elif entity_type == PIIType.DOB:
            start_date = datetime(1960, 1, 1)
            end_date = datetime(2000, 12, 31)
            random_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
            return random_date.strftime("%Y-%m-%d")
            
        elif entity_type == PIIType.IP_ADDRESS:
            prefix = random.choice(IP_RANGES)
            return f"{prefix}{random.randint(1, 254)}"
            
        return "[REDACTED]"
