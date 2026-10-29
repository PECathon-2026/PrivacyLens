"""
Core Data Contracts and Schema Definitions for PrivacyLens.
Canonical models shared across all workstreams.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum


class SensitiveCategory(str, Enum):
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    PASSWORD = "PASSWORD"
    OTP = "OTP"
    CREDIT_CARD = "CREDIT_CARD"
    AADHAAR = "AADHAAR"
    PAN = "PAN"
    API_KEY = "API_KEY"
    PERSON_NAME = "PERSON_NAME"
    ADDRESS = "ADDRESS"
    UNKNOWN = "SENSITIVE_DATA"


class DetectionMethod(str, Enum):
    DOM_METADATA = "DOM_METADATA"
    REGEX = "REGEX"
    VALIDATOR = "VALIDATOR"
    CONTEXT = "CONTEXT"


@dataclass
class PageElement:
    """Represents a DOM element extracted locally from a webpage."""
    element_id: str
    role: str = "element"
    label: str = ""
    input_type: str = "text"
    name: str = ""
    placeholder: str = ""
    value: str = ""
    visible: bool = True
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PageObservation:
    """Complete observation of an active web page captured locally."""
    task_id: str
    url: str
    title: str = ""
    visible_text: str = ""
    elements: List[PageElement] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Detection:
    """A detected sensitive data instance found during local inspection."""
    category: str
    target_element_id: str  # Element ID or "visible_text"
    matched_text: str       # Raw sensitive value (LOCAL ONLY - NEVER SERIALIZE TO AI)
    detection_method: str
    confidence: float = 1.0
    secret_ref: str = ""    # Local pointer to in-memory vault


@dataclass
class SanitizedPageElement:
    """Sanitized DOM element representation safe for external AI models."""
    element_id: str
    role: str
    label: str
    input_type: str
    name: str
    placeholder: str
    value: str  # Semantic placeholder e.g. [REDACTED:EMAIL]
    visible: bool
    enabled: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SanitizedObservation:
    """Sanitized observation payload with all sensitive data replaced by placeholders."""
    task_id: str
    url: str
    title: str
    sanitized_text: str
    elements: List[SanitizedPageElement] = field(default_factory=list)
    redaction_summary: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FirewallDecision:
    """Decision output of the outbound privacy firewall before network egress."""
    is_allowed: bool
    reason: str
    blocked_categories: List[str] = field(default_factory=list)
    canary_leaked: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProposedAction:
    """Structured action proposed by AI or mock model."""
    action_type: str  # e.g., 'click', 'fill_local_value', 'fill_public_value'
    target_element_id: str
    value_purpose: str = ""  # e.g. 'email', 'card_number'
    public_value: str = ""
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AuditEvent:
    """Non-sensitive audit event record for local persistence and UI."""
    task_id: str
    timestamp: str
    event_type: str
    category: str = ""
    item_count: int = 0
    decision: str = ""
    error_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

