"""
Sensitive Information Detection Engine for PrivacyLens.
Combines DOM metadata heuristics, regex patterns, and checksum validators.
"""

import re
from typing import List, Optional
from Core.contracts import (
    PageElement,
    PageObservation,
    Detection,
    SensitiveCategory,
    DetectionMethod,
)


class VerhoeffValidator:
    """Verhoeff algorithm implementation for validating Indian Aadhaar numbers."""
    
    _d = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
        [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
        [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
        [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
        [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
        [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
        [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
        [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
        [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
    ]

    _p = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
        [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
        [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
        [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
        [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
        [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
        [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
    ]

    @classmethod
    def validate(cls, num_str: str) -> bool:
        digits = [int(c) for c in num_str if c.isdigit()]
        if len(digits) != 12:
            return False
        c = 0
        for i, digit in enumerate(reversed(digits)):
            c = cls._d[c][cls._p[i % 8][digit]]
        return c == 0


class LuhnValidator:
    """Luhn algorithm implementation for validating credit and debit cards."""

    @staticmethod
    def validate(num_str: str) -> bool:
        cleaned = re.sub(r"\D", "", num_str)
        if not (13 <= len(cleaned) <= 19):
            return False
        digits = [int(d) for d in cleaned]
        checksum = 0
        reverse_digits = digits[::-1]
        for i, d in enumerate(reverse_digits):
            if i % 2 == 1:
                doubled = d * 2
                checksum += doubled - 9 if doubled > 9 else doubled
            else:
                checksum += d
        return checksum % 10 == 0


class SensitiveDataDetector:
    """Multi-tiered sensitive data detector for DOM elements and visible text."""

    # Pre-compiled high-confidence regular expressions
    EMAIL_PATTERN = re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    )
    PHONE_PATTERN = re.compile(
        r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
        r"|(?:\+91[-.\s]?)?[6-9]\d{9}\b"
    )
    PAN_PATTERN = re.compile(
        r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"
    )
    AADHAAR_PATTERN = re.compile(
        r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b"
    )
    CREDIT_CARD_PATTERN = re.compile(
        r"\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{13,19}\b"
    )
    API_KEY_PATTERN = re.compile(
        r"\b(?:sk_[a-zA-Z0-9_\-]{20,}|ghp_[a-zA-Z0-9]{36}|AIza[0-9A-Za-z-_]{35}|bearer\s+[a-zA-Z0-9._\-]{20,})\b",
        re.IGNORECASE
    )
    OTP_PATTERN = re.compile(
        r"\b\d{4,8}\b"
    )

    # Keyword mappings for DOM semantic context inspection
    DOM_HINTS = {
        SensitiveCategory.PASSWORD: re.compile(r"password|pwd|passcode|secret", re.I),
        SensitiveCategory.OTP: re.compile(r"otp|one[-_\s]?time[-_\s]?password|verification[-_\s]?code|2fa", re.I),
        SensitiveCategory.CREDIT_CARD: re.compile(r"card[-_\s]?number|credit[-_\s]?card|cvv|cvc|card[-_\s]?code|security[-_\s]?code|card[-_\s]?exp", re.I),
        SensitiveCategory.PAN: re.compile(r"pan[-_\s]?card|pan[-_\s]?number|pancard", re.I),
        SensitiveCategory.AADHAAR: re.compile(r"aadhaar|aadhar|uidai", re.I),
        SensitiveCategory.API_KEY: re.compile(r"api[-_\s]?key|access[-_\s]?token|secret[-_\s]?key|auth[-_\s]?token", re.I),
        SensitiveCategory.EMAIL: re.compile(r"email|e-mail", re.I),
        SensitiveCategory.PHONE: re.compile(r"phone|mobile|tel|contact[-_\s]?number", re.I),
        SensitiveCategory.PERSON_NAME: re.compile(r"full[-_\s]?name|first[-_\s]?name|last[-_\s]?name|passenger[-_\s]?name", re.I),
        SensitiveCategory.ADDRESS: re.compile(r"billing[-_\s]?address|shipping[-_\s]?address|street[-_\s]?address", re.I),
    }

    def detect_in_element(self, element: PageElement) -> Optional[Detection]:
        """Inspects a single DOM element for sensitive information using multiple tiers."""
        val = (element.value or "").strip()
        metadata_str = f"{element.label} {element.name} {element.placeholder} {element.input_type}".lower()

        # Tier 1: Strict input type inspection
        if element.input_type == "password":
            return Detection(
                category=SensitiveCategory.PASSWORD,
                target_element_id=element.element_id,
                matched_text=val or "[PASSWORD_FIELD]",
                detection_method=DetectionMethod.DOM_METADATA,
                confidence=1.0,
            )

        # Tier 2: Field metadata keyword analysis
        for category, regex in self.DOM_HINTS.items():
            if regex.search(metadata_str):
                # If field has a value or even if it is currently empty, it is a sensitive target
                matched = val if val else f"[{category.value}_FIELD]"
                
                # Check validation if it matches a specific format
                method = DetectionMethod.DOM_METADATA
                if val:
                    if category == SensitiveCategory.CREDIT_CARD and LuhnValidator.validate(val):
                        method = DetectionMethod.VALIDATOR
                    elif category == SensitiveCategory.PAN and self.validate_pan(val):
                        method = DetectionMethod.VALIDATOR
                    elif category == SensitiveCategory.AADHAAR and VerhoeffValidator.validate(val):
                        method = DetectionMethod.VALIDATOR

                return Detection(
                    category=category.value,
                    target_element_id=element.element_id,
                    matched_text=matched,
                    detection_method=method,
                    confidence=0.95,
                )

        # Tier 3: Value-level format inspection if element contains user input
        if val:
            val_detection = self.detect_in_text(val, target_id=element.element_id)
            if val_detection:
                return val_detection[0]

        return None

    def detect_in_text(self, text: str, target_id: str = "visible_text") -> List[Detection]:
        """Scans arbitrary text for structured sensitive entities."""
        detections: List[Detection] = []
        if not text:
            return detections

        # 1. API Keys
        for match in self.API_KEY_PATTERN.finditer(text):
            detections.append(Detection(
                category=SensitiveCategory.API_KEY,
                target_element_id=target_id,
                matched_text=match.group(0),
                detection_method=DetectionMethod.REGEX,
                confidence=0.99,
            ))

        # 2. Credit Cards (Regex + Luhn Validation)
        for match in self.CREDIT_CARD_PATTERN.finditer(text):
            candidate = match.group(0)
            if LuhnValidator.validate(candidate):
                detections.append(Detection(
                    category=SensitiveCategory.CREDIT_CARD,
                    target_element_id=target_id,
                    matched_text=candidate,
                    detection_method=DetectionMethod.VALIDATOR,
                    confidence=0.98,
                ))

        # 3. Indian PAN Card (Regex + Structural 4th character check)
        for match in self.PAN_PATTERN.finditer(text):
            candidate = match.group(0)
            if self.validate_pan(candidate):
                detections.append(Detection(
                    category=SensitiveCategory.PAN,
                    target_element_id=target_id,
                    matched_text=candidate,
                    detection_method=DetectionMethod.VALIDATOR,
                    confidence=0.97,
                ))

        # 4. Indian Aadhaar Number (Regex + Verhoeff Checksum)
        for match in self.AADHAAR_PATTERN.finditer(text):
            candidate = match.group(0)
            cleaned = candidate.replace(" ", "")
            if VerhoeffValidator.validate(cleaned):
                detections.append(Detection(
                    category=SensitiveCategory.AADHAAR,
                    target_element_id=target_id,
                    matched_text=candidate,
                    detection_method=DetectionMethod.VALIDATOR,
                    confidence=0.99,
                ))

        # 5. Email Addresses
        for match in self.EMAIL_PATTERN.finditer(text):
            detections.append(Detection(
                category=SensitiveCategory.EMAIL,
                target_element_id=target_id,
                matched_text=match.group(0),
                detection_method=DetectionMethod.REGEX,
                confidence=0.95,
            ))

        # 6. Phone Numbers
        for match in self.PHONE_PATTERN.finditer(text):
            candidate = match.group(0).strip()
            # Suppress false positives for small date strings or simple integers
            digits_only = re.sub(r"\D", "", candidate)
            if len(digits_only) >= 10:
                detections.append(Detection(
                    category=SensitiveCategory.PHONE,
                    target_element_id=target_id,
                    matched_text=candidate,
                    detection_method=DetectionMethod.REGEX,
                    confidence=0.90,
                ))

        return detections

    def detect_observation(self, observation: PageObservation) -> List[Detection]:
        """Runs full multi-tier detection across all elements and visible page text."""
        all_detections: List[Detection] = []

        # 1. Elements scan
        for element in observation.elements:
            det = self.detect_in_element(element)
            if det:
                all_detections.append(det)

        # 2. Text body scan
        if observation.visible_text:
            text_detections = self.detect_in_text(observation.visible_text, target_id="visible_text")
            all_detections.extend(text_detections)

        return all_detections

    @staticmethod
    def validate_pan(pan_str: str) -> bool:
        """Validates 4th character structure for Indian PAN card."""
        if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan_str):
            return False
        entity_type = pan_str[3]
        # P: Person, C: Company, H: HUF, A: AOP, B: BOI, G: Govt, J: Juridical, L: Local, F: Firm, T: Trust
        return entity_type in "PCHABGJLFT"

