# PrivacyLens — Shared API Contracts

This document serves as the canonical contract between all four workstreams:
- **Agent 1**: Browser Integration (`browser/extractor.py`)
- **Agent 2**: Core Privacy Engine (`Core/detector.py`, `Core/sanitizer.py`, `Core/firewall.py`)
- **Agent 3**: AI & Action Safety (`Core/ai_client.py`)
- **Agent 4**: UI Dashboard & Audit (`app.py`, `database/models.py`)

---

## 1. Data Contracts

### 1.1 `PageElement`
Represents an interactive or content element extracted from the DOM.
```python
class PageElement:
    element_id: str          # Stable unique ID per observation, e.g. "el_1"
    role: str                # e.g. "textbox", "button", "link", "combobox"
    label: str               # Associated label or accessible name
    input_type: str          # "text", "password", "email", "tel", etc.
    name: str                # HTML name attribute
    placeholder: str         # HTML placeholder attribute
    value: str               # Raw field value (kept local, NEVER sent to AI)
    visible: bool            # True if element is rendered and visible
    enabled: bool            # True if element is not disabled
```

### 1.2 `PageObservation`
Normalized snapshot of the active browser tab.
```python
class PageObservation:
    task_id: str
    url: str
    title: str
    visible_text: str
    elements: list[PageElement]
```

### 1.3 `SensitiveCategory`
Standard categories for sensitive data:
- `EMAIL`
- `PHONE`
- `PASSWORD`
- `OTP`
- `CREDIT_CARD`
- `AADHAAR`
- `PAN`
- `API_KEY`
- `PERSON_NAME`
- `ADDRESS`

### 1.4 `Detection`
Result of inspecting an element or text span.
```python
class Detection:
    category: str            # From SensitiveCategory
    target_element_id: str   # Element ID or "visible_text"
    matched_text: str        # Raw sensitive value (local only!)
    detection_method: str    # "DOM_METADATA", "REGEX", "VALIDATOR", "CONTEXT"
    confidence: float        # 0.0 to 1.0
    secret_ref: str          # Ephemeral local reference token, e.g. "sec_ab12cd34"
```

### 1.5 `SanitizedPageElement`
Safe element representation sent to the AI model.
```python
class SanitizedPageElement:
    element_id: str
    role: str
    label: str
    input_type: str
    name: str
    placeholder: str
    value: str               # Semantic placeholder, e.g. "[REDACTED:EMAIL]"
    visible: bool
    enabled: bool
```

### 1.6 `SanitizedObservation`
Safe observation payload passed to external AI models.
```python
class SanitizedObservation:
    task_id: str
    url: str
    title: str
    sanitized_text: str
    elements: list[SanitizedPageElement]
    redaction_summary: dict[str, int]  # e.g. {"EMAIL": 1, "CREDIT_CARD": 1}
```

### 1.7 `FirewallDecision`
Outbound inspection report produced before any external network transmission.
```python
class FirewallDecision:
    is_allowed: bool
    reason: str
    blocked_categories: list[str]
    canary_leaked: bool
```

### 1.8 `ProposedAction`
Action proposed by the AI reasoning layer.
```python
class ProposedAction:
    action_type: str         # "click", "fill_public_value", "fill_local_value", "select_option", "request_approval"
    target_element_id: str
    value_purpose: str       # e.g. "email", "passenger_name" (for fill_local_value)
    public_value: str        # Literal non-sensitive text (for fill_public_value)
    reasoning: str
```

### 1.9 `AuditEvent`
Non-sensitive audit log entry.
```python
class AuditEvent:
    task_id: str
    timestamp: str
    event_type: str          # "detection_completed", "sanitization_completed", "outbound_allowed", "outbound_blocked", etc.
    category: str
    item_count: int
    decision: str
    error_code: str | None
```

