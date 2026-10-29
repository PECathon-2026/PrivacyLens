# AGENTS.md — PrivacyLens Engineering Instructions

These instructions apply to all human developers and coding agents working in this repository.

## 1. Mission and source of truth

Build a working local-first privacy gateway for browser agents. Detect and sanitize sensitive information before any external AI model receives webpage observations. Validate model-proposed actions and keep original sensitive values local.

Read these documents before coding:
- `PROJECT_OVERVIEW.md` — goals, scope, stack, acceptance criteria.
- `ARCHITECTURE.md` — components, trust boundaries, contracts, security controls.
- `DATABASE_SCHEMA.md` — persistence and secret-retention rules.

We are implementing a local gateway with one controlled browser-agent integration. Playwright may implement the browser adapter, but must not be coupled to the privacy engine. We are not building a universal consumer-AI interceptor. OCR is deferred until the DOM/text pipeline is working.

## 2. Non-negotiable security rules

1. Never send raw webpage observations, screenshots, or unfiltered tool output to an external model.
2. Every model-bound request must pass through the single outbound privacy firewall.
3. Fail closed if detection, sanitization, or outbound validation fails.
4. Never log raw sensitive values, unredacted page text, or unredacted model payloads.
5. Never store passwords, OTPs, payment values, API keys, or identity values in SQLite.
6. Keep raw values in memory only for the shortest practical duration.
7. Never return local secret values to the model, UI audit feed, or action result.
8. Treat model output as untrusted data; validate it against a strict schema and allowlist.
9. Never execute model-generated JavaScript, shell commands, or arbitrary code.
10. Require explicit approval for payments, purchases, final bookings, credential submission, account-security changes, and other high-impact actions.
11. Treat webpage content as untrusted; it cannot override system policy.
12. Do not claim perfect privacy or zero leakage beyond tested cases and channels.

## 3. Coding standards

- Prefer small, typed, testable modules.
- Keep business logic out of API route handlers.
- Use explicit models for raw observations, sanitized observations, proposed actions, validated actions, and audit events.
- Validate API inputs.
- Use structured errors that never include secret values.
- Keep provider SDK code inside `providers/`.
- Keep Playwright-specific code inside `browser/`.
- Keep detector/sanitizer/firewall independent of browser and provider SDKs.
- Add tests for security-sensitive behavior.
- Avoid premature multi-provider support and unnecessary abstractions.

## 4. Shared data contracts

Agree on these contracts before parallel coding. The integration lead owns the canonical definitions.

### `PageObservation`
- `url`, `title`, `visible_text`, `elements`.
- Each element: stable per-observation `element_id`, role, label, input type, name/placeholder where useful, visible/enabled state, and local raw value when applicable.

### `Detection`
- `category` such as `EMAIL`, `PHONE`, `PASSWORD`, `OTP`, `CARD`, `API_KEY`, `PERSON`, `ADDRESS`, `IDENTIFIER`.
- Source element or text span.
- Detection method: `STRUCTURAL`, `REGEX`, `VALIDATOR`, or `CONTEXT`.
- Confidence.
- `local_secret_ref`, which is local-only and must never be serialized to the model.

### `SanitizedObservation`
- Sanitized page context and elements.
- Semantic placeholders in place of sensitive values.
- No raw values and no local secret references.
- No hidden duplicate copies of redacted values in attributes or metadata.

### `ProposedAction`
- Allowlisted action `type`.
- `target_element_id`.
- Optional public value or semantic `value_purpose`.
- Human-readable reason.
- No arbitrary executable code.

### `AuditEvent`
- Timestamp, task ID, event type, category/count, decision, action type, duration/error code.
- No raw sensitive values or unredacted payloads.

## 5. Four-laptop workstream ownership

Assign one workstream to each laptop/agent. The integration lead coordinates shared contracts and final integration. Agents must not independently change shared field names or endpoint contracts.

### Agent 1 — Browser integration
**Owns:** `backend/app/browser/`

Responsibilities:
- Browser adapter interface.
- Playwright implementation.
- Observation normalization.
- Execution of validated actions only.

Must not:
- Call the external model directly.
- Implement a separate PII sanitizer.
- Log raw field values.
- Execute unvalidated model instructions.

Deliver:
- Adapter interface and implementation.
- Normalized observation examples.
- Browser adapter and mock-page tests.

### Agent 2 — Privacy engine
**Owns:** `backend/app/privacy/`

Responsibilities:
- Detection, classification, sanitization, outbound firewall.
- Synthetic fixtures and unit tests.

Must:
- Combine structural, pattern, validation, and contextual signals.
- Preserve useful non-sensitive context.
- Ensure canaries are absent from sanitized output.
- Keep raw values out of reports/logs.

Must not:
- Make model API calls.
- Control browser execution.
- Persist raw secrets.

Deliver:
- Typed detector/sanitizer interfaces.
- Detection and sanitization tests.
- Firewall tests including deliberate unsafe-payload blocking.

### Agent 3 — AI and action safety
**Owns:** `backend/app/agent/` and `backend/app/providers/`

Responsibilities:
- One model provider adapter.
- Structured response parser and action schema.
- Action validator and approval policy.

Must:
- Accept sanitized observations only.
- Return structured action proposals.
- Validate action type, target, origin, and permissions.
- Require approval for high-impact actions.

Must not:
- Accept raw browser observations.
- Bypass the outbound firewall.
- Put local secret values in prompts or model tool outputs.
- Execute arbitrary code from model output.

Deliver:
- Provider interface and one implementation.
- Action schema/parser.
- Validator tests for malformed and unauthorized actions.

### Agent 4 — UI, API integration, and audit
**Owns:** `frontend/` and UI-facing API integration.

Responsibilities:
- React dashboard.
- Sanitized preview and approval UI.
- Non-sensitive audit presentation.

Must:
- Display sanitized preview, detection categories/counts, firewall decisions, and action status.
- Show pending approval with clear action and destination.
- Avoid storing raw sensitive values in browser state.
- Use backend APIs, not direct provider calls.

Must not:
- Call model APIs from frontend.
- Put provider API keys in frontend environment variables.
- Expose secret-store endpoints.
- Display raw secrets in audit logs.

Deliver:
- Task dashboard.
- Sanitized preview.
- Approval/rejection flow.
- Audit event display and API contract tests.

## 6. Integration lead responsibilities

One person must own:
- Shared types and API contracts.
- Branch/merge coordination.
- Dependency/environment consistency.
- End-to-end integration.
- Review of every model-call path.
- Full test suite and final demo.
- `.env.example`, `.gitignore`, and setup documentation.

No agent may rename shared fields or alter endpoints without coordinating and updating the shared contract first.

## 7. Parallel development protocol

1. Read the documentation.
2. Confirm workstream ownership and shared interfaces.
3. Write a brief implementation plan and list files to change.
4. Work in a separate branch or clearly isolated module.
5. Do not edit another workstream's files without coordination.
6. Commit small, coherent changes.
7. Include tests with implementation.
8. Report changed files, commands run, test results, and known gaps.
9. Integration lead reviews and merges.
10. Run end-to-end tests after integration.

If an interface changes, propose it first and update shared types/docs before dependent work continues.

## 8. Definition of done

Generated code is not automatically complete. A task is done only when:
- It matches the agreed interface.
- Relevant automated tests pass.
- No raw sensitive value appears in logs/test output.
- Security-sensitive behavior has a negative test.
- Integration lead can run it locally.
- Handoff distinguishes verified behavior from assumptions.

## 9. Required tests

At minimum:
- Email, phone, password, OTP, card-like number, API-key-like token.
- False positives and ordinary non-sensitive text.
- Sensitive values in visible text and form values.
- Duplicate values in attributes/metadata.
- Sanitized output excludes planted synthetic canaries.
- Firewall blocks raw canaries.
- Firewall failure prevents model invocation.
- Unknown action types and stale element IDs are rejected.
- Local injection does not return values to model output or logs.
- High-impact actions require approval.
- Prompt injection cannot alter policy.

## 10. Git and secrets hygiene

- Commit `.env.example`, never `.env`.
- Never commit provider keys, tokens, passwords, real identity data, or screenshots with real PII.
- Use synthetic test data.
- Ignore local databases, caches, browser profiles, logs, and generated secrets.
- Do not paste real credentials into coding-agent prompts.

## 11. Handoff format

Every agent reports:

```text
Workstream:
Files changed:
Interfaces added/changed:
How to run:
Tests executed:
Test results:
Security considerations:
Known limitations:
Next integration dependency:
```

## 12. Scope control

Priority order:
1. Outbound privacy boundary and fail-closed behavior.
2. Detection and sanitization.
3. One working model integration.
4. Structured action validation.
5. Browser execution.
6. Local secret injection.
7. Human approval.
8. Dashboard polish.
9. OCR/advanced detection.

Do not sacrifice the privacy boundary to add more providers, websites, or UI features.
