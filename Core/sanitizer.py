"""
Data Sanitization Engine and In-Memory Session Secret Store for PrivacyLens.
Replaces sensitive spans with semantic placeholders and stores secrets locally.
"""

import secrets
import time
from typing import Dict, List, Tuple, Optional
from Core.contracts import (
    PageObservation,
    SanitizedObservation,
    SanitizedPageElement,
    Detection,
)
from Core.detector import SensitiveDataDetector


class SessionSecretStore:
    """
    In-memory task-scoped secret store.
    Holds sensitive values locally during task execution.
    Raw secrets are NEVER written to disk, database, or returned to the AI model.
    """

    def __init__(self, ttl_seconds: int = 1800):
        # Structure: {task_id: {secret_ref: {"category": str, "value": str, "created_at": float}}}
        self._vault: Dict[str, Dict[str, Dict[str, any]]] = {}
        self._ttl_seconds = ttl_seconds

    def put(self, task_id: str, category: str, value: str) -> str:
        """Stores a sensitive value in memory and returns an unguessable local token."""
        if not value:
            return ""

        if task_id not in self._vault:
            self._vault[task_id] = {}

        # Generate a cryptographically random, unguessable token
        secret_ref = f"sec_{secrets.token_hex(8)}"
        self._vault[task_id][secret_ref] = {
            "category": category,
            "value": value,
            "created_at": time.time(),
        }
        return secret_ref

    def resolve(self, task_id: str, secret_ref: str, expected_category: Optional[str] = None) -> Optional[str]:
        """
        Retrieves a secret for local action execution.
        Fails closed if task_id does not exist, secret is expired, or category does not match.
        """
        task_store = self._vault.get(task_id)
        if not task_store or secret_ref not in task_store:
            return None

        entry = task_store[secret_ref]
        # Check TTL
        if time.time() - entry["created_at"] > self._ttl_seconds:
            del task_store[secret_ref]
            return None

        # Category mismatch check (Fail-Closed)
        if expected_category and entry["category"].upper() != expected_category.upper():
            return None

        return entry["value"]

    def get_active_secrets(self, task_id: str) -> List[str]:
        """Returns all registered raw values for a task. Used by the outbound firewall to detect leaks."""
        task_store = self._vault.get(task_id, {})
        return [entry["value"] for entry in task_store.values() if entry.get("value")]

    def clear_task(self, task_id: str) -> None:
        """Wipes all secrets associated with a task."""
        if task_id in self._vault:
            self._vault[task_id].clear()
            del self._vault[task_id]


class DataSanitizer:
    """Sanitizes PageObservation objects by substituting sensitive values with placeholders."""

    def __init__(self, detector: Optional[SensitiveDataDetector] = None, secret_store: Optional[SessionSecretStore] = None):
        self.detector = detector or SensitiveDataDetector()
        self.secret_store = secret_store or SessionSecretStore()

    def sanitize_observation(
        self, observation: PageObservation
    ) -> Tuple[SanitizedObservation, List[Detection]]:
        """
        Sanitizes observation in place:
        1. Identifies all sensitive elements and text spans.
        2. Replaces values with `[REDACTED:<CATEGORY>]`.
        3. Stores raw originals in the local SessionSecretStore.
        4. Returns the SanitizedObservation and metadata Detections.
        """
        detections = self.detector.detect_observation(observation)
        redaction_summary: Dict[str, int] = {}
        sanitized_elements: List[SanitizedPageElement] = []

        # Map detections by target_element_id for fast lookup
        elem_detection_map: Dict[str, Detection] = {
            d.target_element_id: d for d in detections if d.target_element_id != "visible_text"
        }

        for elem in observation.elements:
            det = elem_detection_map.get(elem.element_id)
            if det:
                category = det.category.upper()
                raw_val = elem.value

                # Store in ephemeral vault if there is a real value
                if raw_val and not raw_val.startswith("["):
                    secret_ref = self.secret_store.put(observation.task_id, category, raw_val)
                    det.secret_ref = secret_ref

                placeholder = f"[REDACTED:{category}]"
                redaction_summary[category] = redaction_summary.get(category, 0) + 1

                sanitized_elem = SanitizedPageElement(
                    element_id=elem.element_id,
                    role=elem.role,
                    label=elem.label,
                    input_type=elem.input_type,
                    name=elem.name,
                    placeholder=placeholder if elem.placeholder else "",
                    value=placeholder,
                    visible=elem.visible,
                    enabled=elem.enabled,
                )
            else:
                sanitized_elem = SanitizedPageElement(
                    element_id=elem.element_id,
                    role=elem.role,
                    label=elem.label,
                    input_type=elem.input_type,
                    name=elem.name,
                    placeholder=elem.placeholder,
                    value=elem.value,
                    visible=elem.visible,
                    enabled=elem.enabled,
                )
            sanitized_elements.append(sanitized_elem)

        # Sanitize visible_text
        sanitized_text = observation.visible_text or ""
        text_detections = [d for d in detections if d.target_element_id == "visible_text"]

        # Sort spans by length descending to replace larger spans first and avoid sub-string collisions
        text_detections.sort(key=lambda d: len(d.matched_text), reverse=True)

        for d in text_detections:
            if d.matched_text and d.matched_text in sanitized_text:
                category = d.category.upper()
                secret_ref = self.secret_store.put(observation.task_id, category, d.matched_text)
                d.secret_ref = secret_ref
                placeholder = f"[REDACTED:{category}]"
                sanitized_text = sanitized_text.replace(d.matched_text, placeholder)
                redaction_summary[category] = redaction_summary.get(category, 0) + 1

        sanitized_obs = SanitizedObservation(
            task_id=observation.task_id,
            url=observation.url,
            title=observation.title,
            sanitized_text=sanitized_text,
            elements=sanitized_elements,
            redaction_summary=redaction_summary,
        )

        return sanitized_obs, detections

