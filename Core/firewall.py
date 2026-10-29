"""
Outbound Privacy Firewall for PrivacyLens.
Serves as the single, non-bypassable egress checkpoint before external model communication.
Enforces strict fail-closed security, canary detection, and serialized payload auditing.
"""

import json
import re
from typing import List, Optional
from Core.contracts import SanitizedObservation, FirewallDecision
from Core.detector import SensitiveDataDetector


class PrivacyFirewall:
    """
    Final egress firewall.
    Inspects the exact serialized payload destined for external AI models.
    Blocks any payload containing known secrets, planted synthetic canaries,
    local secret references, or unredacted PII patterns.
    """

    SECRET_REF_PATTERN = re.compile(r"sec_[a-f0-9]{16}", re.IGNORECASE)

    def __init__(self, detector: Optional[SensitiveDataDetector] = None):
        self.detector = detector or SensitiveDataDetector()

    def inspect(
        self,
        sanitized_obs: SanitizedObservation,
        active_secrets: Optional[List[str]] = None,
        canaries: Optional[List[str]] = None,
    ) -> FirewallDecision:
        """
        Performs exhaustive inspection of the outgoing payload.
        Fails closed on any security violation or exception.
        """
        try:
            # 1. Structural Validation
            if not sanitized_obs or not isinstance(sanitized_obs, SanitizedObservation):
                return FirewallDecision(
                    is_allowed=False,
                    reason="FIREWALL_ERROR: Malformed or missing SanitizedObservation payload.",
                )

            # 2. Complete serialization check (exactly what leaves the machine)
            serialized_payload = json.dumps(sanitized_obs.to_dict(), ensure_ascii=False)

            # 3. Known Active Secrets and Planted Canaries Check
            all_known_secrets = list(active_secrets or [])
            if canaries:
                all_known_secrets.extend(canaries)

            for secret in all_known_secrets:
                # Disallow raw secrets longer than 3 chars (avoid matching single numbers/spaces)
                if secret and len(secret.strip()) >= 4:
                    if secret in serialized_payload:
                        return FirewallDecision(
                            is_allowed=False,
                            reason="FIREWALL_BLOCKED: Planted canary or raw secret detected in outbound payload.",
                            blocked_categories=["KNOWN_SECRET_LEAK"],
                            canary_leaked=True,
                        )

            # 4. Local Secret Reference Token Leak Check
            if self.SECRET_REF_PATTERN.search(serialized_payload):
                return FirewallDecision(
                    is_allowed=False,
                    reason="FIREWALL_BLOCKED: Internal local secret reference token found in model payload.",
                    blocked_categories=["INTERNAL_TOKEN_LEAK"],
                )

            # 5. Outbound Deep Pattern Re-scan (Defensive Double Check)
            # Inspect the sanitized text and all sanitized elements
            text_violations = self.detector.detect_in_text(sanitized_obs.sanitized_text)
            if text_violations:
                blocked = list({v.category for v in text_violations})
                return FirewallDecision(
                    is_allowed=False,
                    reason=f"FIREWALL_BLOCKED: Unredacted sensitive patterns detected in sanitized text: {blocked}",
                    blocked_categories=blocked,
                )

            for elem in sanitized_obs.elements:
                # Any unredacted password field or sensitive value
                if elem.input_type == "password" and elem.value != "[REDACTED:PASSWORD]":
                    return FirewallDecision(
                        is_allowed=False,
                        reason="FIREWALL_BLOCKED: Unredacted password element present in payload.",
                        blocked_categories=["PASSWORD"],
                    )
                elem_violations = self.detector.detect_in_text(elem.value)
                if elem_violations:
                    blocked = list({v.category for v in elem_violations})
                    return FirewallDecision(
                        is_allowed=False,
                        reason=f"FIREWALL_BLOCKED: Unredacted sensitive pattern in element '{elem.element_id}': {blocked}",
                        blocked_categories=blocked,
                    )

            # All checks passed successfully
            return FirewallDecision(
                is_allowed=True,
                reason="FIREWALL_APPROVED: Outbound payload verified safe and sanitized.",
                blocked_categories=[],
                canary_leaked=False,
            )

        except Exception as e:
            # Absolute Fail-Closed Principle: Any unhandled exception blocks outbound traffic
            return FirewallDecision(
                is_allowed=False,
                reason=f"FIREWALL_FATAL_ERROR: Unexpected error during firewall evaluation: {str(e)}",
                blocked_categories=["FIREWALL_EXCEPTION"],
            )

