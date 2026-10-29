"""
Comprehensive Unit and Integration Security Tests for PrivacyLens Core Privacy Engine.
Verifies multi-tier detection, format validators, sanitization, secret store, and fail-closed firewall.
"""

import pytest
from Core.contracts import (
    PageElement,
    PageObservation,
    SanitizedObservation,
    SensitiveCategory,
)
from Core.detector import SensitiveDataDetector, LuhnValidator, VerhoeffValidator
from Core.sanitizer import DataSanitizer, SessionSecretStore
from Core.firewall import PrivacyFirewall


# ============================================================================
# 1. VALIDATOR TESTS (Luhn, Verhoeff, PAN)
# ============================================================================

def test_luhn_validator():
    # Valid Visa card
    assert LuhnValidator.validate("4532015112830366") is True
    # Valid Mastercard
    assert LuhnValidator.validate("5425233430109903") is True
    # Invalid card (checksum failure)
    assert LuhnValidator.validate("4532015112830367") is False
    # Too short
    assert LuhnValidator.validate("123456") is False


def test_verhoeff_aadhaar_validator():
    # Valid Aadhaar numbers generated via Verhoeff
    assert VerhoeffValidator.validate("234567890124") is True
    # Invalid Aadhaar (last digit altered)
    assert VerhoeffValidator.validate("234567890125") is False
    # Non-12 digits
    assert VerhoeffValidator.validate("23456789012") is False


def test_pan_validator():
    # Valid Indian PAN with 4th char 'P' (Person)
    assert SensitiveDataDetector.validate_pan("ABCPD1234F") is True
    # Valid Indian PAN with 4th char 'C' (Company)
    assert SensitiveDataDetector.validate_pan("XYZCK9876Q") is True
    # Invalid 4th char 'Z'
    assert SensitiveDataDetector.validate_pan("XYZZE1234F") is False
    # Invalid format (only 4 chars)
    assert SensitiveDataDetector.validate_pan("ABCD12345") is False


# ============================================================================
# 2. SENSITIVE DATA DETECTOR TESTS
# ============================================================================

@pytest.fixture
def detector():
    return SensitiveDataDetector()


def test_detect_password_field(detector):
    elem = PageElement(
        element_id="el_pwd",
        input_type="password",
        name="user_password",
        value="Secret123!",
    )
    det = detector.detect_in_element(elem)
    assert det is not None
    assert det.category == SensitiveCategory.PASSWORD


def test_detect_email_element_and_text(detector):
    # Field detection
    elem = PageElement(
        element_id="el_email",
        input_type="text",
        name="email",
        label="Email Address",
        value="rahul.sharma@example.test",
    )
    det = detector.detect_in_element(elem)
    assert det is not None
    assert det.category == SensitiveCategory.EMAIL

    # Text detection
    text_dets = detector.detect_in_text("Please reach out at agent.support@internal.domain for queries.")
    assert len(text_dets) == 1
    assert text_dets[0].category == SensitiveCategory.EMAIL
    assert text_dets[0].matched_text == "agent.support@internal.domain"


def test_detect_credit_card(detector):
    valid_card = "4532-0151-1283-0366"
    elem = PageElement(
        element_id="el_card",
        input_type="text",
        label="Credit Card Number",
        value=valid_card,
    )
    det = detector.detect_in_element(elem)
    assert det is not None
    assert det.category == SensitiveCategory.CREDIT_CARD


def test_detect_api_key(detector):
    sample_key = "bearer mock_synthetic_api_secret_key_8899aabbcc"
    text = f"Header: {sample_key}"
    dets = detector.detect_in_text(text)
    assert len(dets) >= 1
    assert any(d.category == SensitiveCategory.API_KEY for d in dets)


def test_false_positive_suppression(detector):
    # Normal non-sensitive words should not be flagged
    normal_text = "Flight 6E-204 from Delhi to Mumbai departing at 14:30. Total fare is INR 4500."
    dets = detector.detect_in_text(normal_text)
    # Ensure no false credit cards or emails
    categories = [d.category for d in dets]
    assert SensitiveCategory.CREDIT_CARD not in categories
    assert SensitiveCategory.EMAIL not in categories


# ============================================================================
# 3. SESSION SECRET STORE TESTS
# ============================================================================

def test_session_secret_store():
    store = SessionSecretStore(ttl_seconds=60)
    task_id = "task_test_001"
    raw_secret = "4532015112830366"

    # Store secret
    token = store.put(task_id, "CREDIT_CARD", raw_secret)
    assert token.startswith("sec_")

    # Resolve with correct category
    resolved = store.resolve(task_id, token, expected_category="CREDIT_CARD")
    assert resolved == raw_secret

    # Resolve with wrong category (fail-closed)
    wrong_cat = store.resolve(task_id, token, expected_category="PASSWORD")
    assert wrong_cat is None

    # Resolve with non-existent token
    invalid_token = store.resolve(task_id, "sec_invalid12345678")
    assert invalid_token is None

    # Clear task
    store.clear_task(task_id)
    assert store.resolve(task_id, token) is None


# ============================================================================
# 4. SANITIZER TESTS
# ============================================================================

def test_sanitizer_replaces_with_placeholders():
    detector = SensitiveDataDetector()
    store = SessionSecretStore()
    sanitizer = DataSanitizer(detector=detector, secret_store=store)

    obs = PageObservation(
        task_id="task_flight_01",
        url="https://airline.test/checkout",
        title="Passenger Checkout",
        visible_text="Booking for passenger rahul@example.test with contact +919876543210.",
        elements=[
            PageElement(
                element_id="el_name",
                role="textbox",
                label="Passenger Name",
                value="Rahul Sharma",
            ),
            PageElement(
                element_id="el_card",
                role="textbox",
                label="Card Number",
                value="4532015112830366",
            ),
            PageElement(
                element_id="el_btn",
                role="button",
                label="Pay Now",
                value="",
            ),
        ],
    )

    sanitized, detections = sanitizer.sanitize_observation(obs)

    # Verify placeholders in elements
    card_elem = next(e for e in sanitized.elements if e.element_id == "el_card")
    assert card_elem.value == "[REDACTED:CREDIT_CARD]"

    # Verify non-sensitive elements are preserved
    btn_elem = next(e for e in sanitized.elements if e.element_id == "el_btn")
    assert btn_elem.label == "Pay Now"

    # Verify text sanitization
    assert "rahul@example.test" not in sanitized.sanitized_text
    assert "[REDACTED:EMAIL]" in sanitized.sanitized_text
    assert "[REDACTED:PHONE]" in sanitized.sanitized_text

    # Verify raw secrets are safely kept in the store
    active_secrets = store.get_active_secrets("task_flight_01")
    assert "4532015112830366" in active_secrets
    assert "rahul@example.test" in active_secrets


# ============================================================================
# 5. PRIVACY FIREWALL TESTS (FAIL-CLOSED)
# ============================================================================

@pytest.fixture
def firewall():
    return PrivacyFirewall()


def test_firewall_allows_clean_payload(firewall):
    clean_obs = SanitizedObservation(
        task_id="task_safe_01",
        url="https://airline.test/search",
        title="Flight Search",
        sanitized_text="Showing flights from Delhi to Mumbai on 15th Nov.",
        elements=[],
        redaction_summary={},
    )
    decision = firewall.inspect(clean_obs)
    assert decision.is_allowed is True
    assert decision.canary_leaked is False


def test_firewall_blocks_planted_canary(firewall):
    canary = "CANARY_SECRET_TOKEN_9999"
    leaked_obs = SanitizedObservation(
        task_id="task_leak_01",
        url="https://airline.test",
        title="Test Leak",
        sanitized_text=f"Some non-sensitive text with leak: {canary}",
        elements=[],
        redaction_summary={},
    )
    decision = firewall.inspect(leaked_obs, canaries=[canary])
    assert decision.is_allowed is False
    assert decision.canary_leaked is True
    assert "KNOWN_SECRET_LEAK" in decision.blocked_categories


def test_firewall_blocks_internal_secret_token_leak(firewall):
    leaked_obs = SanitizedObservation(
        task_id="task_leak_02",
        url="https://airline.test",
        title="Test Token Leak",
        sanitized_text="Internal pointer: sec_a1b2c3d4e5f60718 should not leave.",
        elements=[],
        redaction_summary={},
    )
    decision = firewall.inspect(leaked_obs)
    assert decision.is_allowed is False
    assert "INTERNAL_TOKEN_LEAK" in decision.blocked_categories


def test_firewall_blocks_unredacted_credit_card(firewall):
    valid_card = "4532015112830366"
    leaked_obs = SanitizedObservation(
        task_id="task_leak_03",
        url="https://airline.test",
        title="Card Leak",
        sanitized_text=f"Total billed to card {valid_card}",
        elements=[],
        redaction_summary={},
    )
    decision = firewall.inspect(leaked_obs)
    assert decision.is_allowed is False
    assert "CREDIT_CARD" in decision.blocked_categories
