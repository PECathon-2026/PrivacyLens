"""
End-to-End Integration and Security Verification Suite for PrivacyLens.
Tests the complete lifecycle:
Observation Extraction -> Sensitive Detection -> Placeholder Sanitization ->
Firewall Pre-Flight -> AI Mock Reasoning -> Consequential Action Policy -> Local Injection.
"""

import asyncio
import pytest
from pathlib import Path
from Core.contracts import (
    PageObservation,
    SanitizedObservation,
    SensitiveCategory,
    ProposedAction,
    AuditEvent,
)
from Core.detector import SensitiveDataDetector
from Core.sanitizer import DataSanitizer, SessionSecretStore
from Core.firewall import PrivacyFirewall
from Core.ai_client import AIModelClient
from browser.extractor import PlaywrightDOMExtractor
from database.models import AuditDatabase


@pytest.fixture
def sample_page_path():
    path = Path(__file__).parent.parent / "demo" / "sample_page.html"
    assert path.exists(), "demo/sample_page.html must exist for E2E tests"
    return str(path)


def test_full_privacy_preserving_lifecycle(sample_page_path, tmp_path):
    async def _run():
        # 1. Initialize components
        task_id = "task_e2e_flight_001"
        db_file = str(tmp_path / "test_audit.sqlite3")
        audit_db = AuditDatabase(db_path=db_file)
        vault = SessionSecretStore()
        detector = SensitiveDataDetector()
        sanitizer = DataSanitizer(detector=detector, secret_store=vault)
        firewall = PrivacyFirewall(detector=detector)
        ai_client = AIModelClient()
        extractor = PlaywrightDOMExtractor(headless=True)

        # 2. Extract raw observation from demo flight checkout page
        raw_obs = extractor.extract_from_html_file(task_id, sample_page_path)
        assert raw_obs is not None
        assert len(raw_obs.elements) >= 7

        # Verify raw elements contain sensitive test values before sanitization
        raw_card_elem = next(e for e in raw_obs.elements if "card_number" in e.element_id)
        assert raw_card_elem.value == "4532015112830366"

        # 3. Local Detection & Sanitization
        sanitized_obs, detections = sanitizer.sanitize_observation(raw_obs)
        assert len(detections) >= 5

        # Verify all sensitive values were replaced with semantic placeholders
        sanitized_card_elem = next(e for e in sanitized_obs.elements if "card_number" in e.element_id)
        assert sanitized_card_elem.value == "[REDACTED:CREDIT_CARD]"
        assert "4532015112830366" not in sanitized_card_elem.value
        assert "rahul.sharma@example.test" not in sanitized_obs.sanitized_text

        # Verify secrets are safely locked inside the local in-memory vault
        active_secrets = vault.get_active_secrets(task_id)
        assert "4532015112830366" in active_secrets
        assert "rahul.sharma@example.test" in active_secrets

        # 4. Outbound Privacy Firewall Enforcement
        # Clean sanitized payload MUST pass
        clean_decision = firewall.inspect(sanitized_obs, active_secrets=active_secrets)
        assert clean_decision.is_allowed is True
        assert clean_decision.canary_leaked is False

        # 5. Outbound Firewall Adversarial Canary Attack Test (Fail-Closed)
        planted_canary = "CANARY_SECRET_LEAK_TOKEN_9999"
        adversarial_obs = SanitizedObservation(
            task_id=task_id,
            url=sanitized_obs.url,
            title=sanitized_obs.title,
            sanitized_text=f"Legitimate text leaking secret: {planted_canary}",
            elements=sanitized_obs.elements,
            redaction_summary=sanitized_obs.redaction_summary,
        )
        leak_decision = firewall.inspect(adversarial_obs, canaries=[planted_canary])
        assert leak_decision.is_allowed is False
        assert leak_decision.canary_leaked is True

        # 6. AI Reasoning & Structured Action Proposals
        actions = await ai_client.propose_actions("Book flight for passenger", sanitized_obs)
        assert len(actions) >= 2

        # Model proposes fill_local_value with semantic purpose
        local_fill_action = next((a for a in actions if a.action_type == "fill_local_value"), None)
        assert local_fill_action is not None
        assert local_fill_action.value_purpose != ""

        # Consequential action (e.g. payment/booking confirmation) requires approval
        approval_action = next((a for a in actions if a.action_type == "request_approval"), None)
        assert approval_action is not None

        # 7. Local Secret Injection Execution
        # Find detection for the target element
        target_det = next(d for d in detections if d.target_element_id == local_fill_action.target_element_id)
        # Resolve real value from local vault
        resolved_val = vault.resolve(task_id, target_det.secret_ref, target_det.category)
        assert resolved_val is not None
        assert not resolved_val.startswith("[REDACTED")

        # Execute action via extractor
        exec_result = await extractor.execute_action(local_fill_action, resolved_secret=resolved_val)
        assert exec_result["success"] is True

        # 8. Non-Sensitive Audit Trail Logging
        audit_db.record_privacy_event(AuditEvent(
            task_id=task_id,
            timestamp="12:00:00",
            event_type="e2e_test_completed",
            category="INTEGRATION_TEST",
            item_count=len(detections),
            decision="ZERO_LEAKAGE_VERIFIED",
        ))
        logged_events = audit_db.get_task_events(task_id)
        assert len(logged_events) >= 1

        # Verify zero secrets appear in SQLite audit log
        for event in logged_events:
            for val in active_secrets:
                assert val not in str(event.values()), "Raw secret leaked into audit database!"

    asyncio.run(_run())
