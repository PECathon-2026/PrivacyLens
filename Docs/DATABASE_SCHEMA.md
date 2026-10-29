# PrivacyLens — Database Schema

## 1. Is a database required?

A database is **not required for storing sensitive values**.

For the MVP:
- Use an in-memory, task-scoped store for original sensitive values and local references.
- Optionally use SQLite for non-sensitive task metadata, audit events, and privacy settings.
- The core privacy pipeline must work without a database.

This separation is deliberate. SQLite must never contain raw passwords, OTPs, payment details, API keys, identity numbers, raw webpage observations, or placeholder-to-secret mappings.

## 2. Storage policy

| Data | Storage | Persist? |
|---|---|---|
| Original sensitive values | In-memory task store | No |
| Placeholder-to-secret mapping | In-memory task store | No |
| Raw webpage text/DOM values | Process memory during inspection | No |
| Sanitized preview | Current task/session memory | Prefer no |
| Task ID and status | SQLite | Optional |
| Detection category/count | SQLite | Optional |
| Firewall allow/block decision | SQLite | Optional |
| Action type/validation result | SQLite | Optional |
| Approval decision | SQLite | Optional |
| Privacy preferences | SQLite | Optional |
| Provider API key | Environment/OS secret store | Never SQLite |
| Full prompts/responses | Do not persist by default | No |

## 3. Minimal SQLite schema

The schema stores metadata only.

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS tasks (
    task_id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK (
        status IN (
            'created', 'running', 'awaiting_approval',
            'completed', 'failed', 'cancelled'
        )
    ),
    task_label TEXT,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT,
    error_code TEXT
);

CREATE TABLE IF NOT EXISTS privacy_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (
        event_type IN (
            'observation_processed',
            'detection_completed',
            'sanitization_completed',
            'outbound_allowed',
            'outbound_blocked',
            'action_rejected',
            'action_validated',
            'approval_requested',
            'approval_granted',
            'approval_denied',
            'secret_injected',
            'task_cancelled',
            'error'
        )
    ),
    category TEXT,
    item_count INTEGER NOT NULL DEFAULT 0 CHECK (item_count >= 0),
    decision TEXT,
    duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
    error_code TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_privacy_events_task_created
    ON privacy_events(task_id, created_at);

CREATE INDEX IF NOT EXISTS idx_privacy_events_type
    ON privacy_events(event_type);

CREATE TABLE IF NOT EXISTS action_events (
    action_event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    target_element_id TEXT,
    validation_status TEXT NOT NULL CHECK (
        validation_status IN ('approved', 'rejected', 'pending')
    ),
    approval_required INTEGER NOT NULL DEFAULT 0
        CHECK (approval_required IN (0, 1)),
    approval_status TEXT CHECK (
        approval_status IS NULL OR
        approval_status IN ('not_required', 'pending', 'approved', 'denied')
    ),
    reason_code TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_action_events_task_created
    ON action_events(task_id, created_at);

CREATE TABLE IF NOT EXISTS privacy_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

## 4. Never add raw-secret columns

Do not add columns such as:
- `raw_value`, `password`, `otp`, `card_number`, `api_key`, `secret_value`
- `raw_page_html`, `raw_page_text`, `raw_screenshot_path`
- `full_prompt`, `full_model_response`
- `placeholder_to_value_mapping`

Do not store reversible encrypted secrets in SQLite merely for convenience. If persistent secret storage becomes necessary, use OS-backed secure storage or a vetted secrets-management mechanism and document its threat model. Do not invent custom cryptography.

## 5. In-memory session store interface

```python
class SessionSecretStore:
    def put(self, task_id: str, category: str, value: str) -> str:
        # Store in memory; return an unguessable local-only reference.
        ...

    def resolve(
        self,
        task_id: str,
        secret_ref: str,
        expected_category: str
    ) -> str:
        # Return only to the local executor after policy checks.
        ...

    def clear_task(self, task_id: str) -> None:
        # Remove all values for the task.
        ...

    def clear_expired(self) -> None:
        # Remove expired task values.
        ...
```

Requirements:
- Generate references with a cryptographically secure random generator.
- Keep references local; never include them in model prompts or model tool output.
- Check task ID and category during resolution.
- Apply session expiry.
- Clear values on task completion, cancellation, timeout, and shutdown.
- Never log resolved values.
- Do not claim reliable memory zeroization in a garbage-collected runtime.

## 6. Retention policy

Suggested defaults:
- Raw values: memory only, task-scoped.
- Sanitized preview: current task/session only.
- Audit metadata: retain only as long as required for the demo/evaluation; provide a reset/clear option.
- Provider request/response bodies: do not persist.
- Browser profile/downloads: use a dedicated temporary profile and clean it up after the task.

The README must describe the behavior actually implemented, not only intended behavior.

## 7. Safe audit examples

```json
{
  "task_id": "task_demo_001",
  "event_type": "detection_completed",
  "category": "EMAIL",
  "item_count": 1,
  "decision": "redacted"
}
```

```json
{
  "task_id": "task_demo_001",
  "event_type": "outbound_blocked",
  "category": "SECRET_CANARY",
  "item_count": 1,
  "decision": "blocked",
  "error_code": "OUTBOUND_SENSITIVE_VALUE"
}
```

Unsafe — never do this:

```json
{
  "event_type": "detection_completed",
  "category": "EMAIL",
  "raw_value": "person@example.test"
}
```

## 8. Initialization and SQL safety

- Initialize the schema once during application startup.
- Use parameterized SQL for all values.
- Never build SQL by concatenating user input.
- SQLite is sufficient for the hackathon. A remote database is unnecessary and would create another trust boundary.
