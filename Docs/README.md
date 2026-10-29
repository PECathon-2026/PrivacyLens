# PrivacyLens — Project Overview

**Problem statement:** PS-004 — PrivacyLens: Building a Privacy-Preserving AI Browser Agent  
**Project principle:** *Compute what is sensitive locally. Reason globally only on sanitized data.*

## 1. Summary

PrivacyLens is a local privacy gateway between a browser agent and an external AI model. It inspects browser observations locally, detects sensitive information, replaces sensitive values with semantic placeholders, and blocks unsafe model-bound payloads. The AI receives enough sanitized context to reason about the task and proposes structured actions. A local validator checks those actions before a browser adapter executes them.

When a website legitimately requires a sensitive value, the local executor may retrieve an approved value from a local, task-scoped store and enter it into the website. The value must not be returned to the AI. PrivacyLens protects information from unnecessary exposure to the external model; it does not prevent the website from receiving information required to perform the requested task.

## 2. Problem

AI agents automate shopping, form filling, account management, and website navigation. Their observations may contain identity numbers, passwords, OTPs, financial details, API keys, medical records, personal messages, and other sensitive information. Sending raw screenshots or webpage data to cloud AI models can expose this information.

The goal is to enable useful AI-driven interaction while reducing disclosure of sensitive user information.

## 3. Product goals

### MVP requirements
1. Detect common sensitive information using patterns, validation, and page structure.
2. Sanitize text and structured webpage observations locally.
3. Preserve useful non-sensitive context and interface structure.
4. Validate every model-bound payload through one outbound privacy firewall.
5. Fail closed when detection, sanitization, or validation fails.
6. Integrate one AI model through a provider adapter.
7. Require structured model actions; never execute arbitrary model-generated code.
8. Validate proposed actions before browser execution.
9. Keep original sensitive values local and support controlled local value injection.
10. Require user approval for sensitive or irreversible actions.
11. Provide a before/after privacy preview and non-sensitive audit events.
12. Include reproducible tests and measured evaluation results.

### Non-goals for the hackathon MVP
- Building a browser or full Chrome extension.
- Intercepting arbitrary traffic from every existing consumer AI application.
- Supporting every model provider and browser-agent framework immediately.
- Claiming universal or perfect privacy protection.
- Advanced OCR/computer vision before DOM/text processing works.
- Persisting raw passwords, OTPs, payment data, API keys, or identity values.
- Completing real purchases/payments/bookings without user approval.

## 4. Chosen approach

Build the **local privacy gateway first**, with one controlled browser-agent integration. The gateway is the core product; browser automation is an adapter. Do not build a separate simulated-browser product or a universal interception layer for the MVP.

Playwright may be used to implement the browser adapter, but it must remain replaceable and separate from the privacy engine. The first integration controls its own agent-to-model communication. It does not assume that an ordinary consumer AI application can be transparently intercepted.

## 5. Main components

| Component | Responsibility |
|---|---|
| React UI | Task entry, privacy preview, approval, status, audit view |
| Local FastAPI gateway | Task/session API and orchestration |
| Browser adapter | Observe pages and execute validated actions |
| Observation normalizer | Convert page data into a bounded common format |
| Sensitive-data detector | Find PII/secrets using structure, patterns, validators, context |
| Sanitizer | Replace sensitive values; preserve useful context |
| Local session secret store | Hold original values only for the task duration |
| Outbound privacy firewall | Inspect final model-bound payload and block unsafe data |
| Model provider adapter | Send sanitized context and parse structured model output |
| Action validator | Enforce schema, targets, permissions, and approval policy |
| Local executor | Execute approved actions and inject local values |
| Audit/evaluation | Record non-sensitive events and calculate metrics |

## 6. Proposed stack

These are project choices, not requirements imposed by the problem statement.

| Area | Initial choice |
|---|---|
| Frontend | React |
| Local backend | Python + FastAPI |
| Browser integration | Playwright adapter (or another controlled browser adapter) |
| Detection/sanitization | Python |
| Pattern matching | Python regex plus format/checksum validators |
| Database | SQLite for metadata only; optional for MVP |
| Secret storage | In-memory task-scoped store initially |
| Screenshot redaction | Pillow/OpenCV if screenshot path is implemented |
| OCR | Deferred optional enhancement |
| AI | One provider API behind a provider interface |
| Tests | pytest and synthetic fixtures |

## 7. Trust and privacy principles

- Inspect raw observations locally before any model call.
- Minimize the data sent to the model.
- Use semantic placeholders such as `[REDACTED:EMAIL]`.
- Do not persist raw values or raw page content.
- Route every model call through one outbound firewall.
- Fail closed on uncertainty or pipeline errors.
- Treat webpages and model outputs as untrusted.
- Restrict actions to an allowlist and require human approval for consequential actions.
- Report measured results only for tested scenarios and channels.

## 8. MVP acceptance criteria

The MVP is ready when a reviewer can:
1. Start the local application and run a task through the supported browser adapter.
2. See detected sensitive fields and a sanitized preview.
3. Verify that the model-bound request contains placeholders, not planted synthetic originals.
4. See a structured action proposal from the model.
5. See the validator approve or reject the proposal.
6. See an authorized local value filled into a webpage without being returned to the model.
7. Approve or reject a consequential action.
8. Trigger an unsafe-payload test and see the firewall block it before model transmission.
9. Run the evaluation tests and inspect actual results.

## 9. Evaluation scenarios and metrics

Use synthetic sensitive data and annotated test cases.

| Scenario | Data types |
|---|---|
| E-commerce checkout | Card-like values, addresses, phone |
| Authentication | Email, password, OTP |
| Customer support | Phone numbers, private messages |
| Video conferencing | Faces and participant information |
| Developer settings | API keys, tokens, IP addresses |

Metrics:
- Detection recall = `TP / (TP + FN)`
- Redaction precision = `TP / (TP + FP)`
- Leakage rate = tested model-bound payloads containing a planted canary / total tested payloads
- Context preservation = relevant non-sensitive fields retained / relevant non-sensitive fields expected
- Task success rate = successful tasks / attempted tasks
- Latency = local inspection time and end-to-end task time
- Action validation rate = invalid actions correctly rejected / invalid actions tested

Do not claim “zero leakage” globally. Qualify results by the exact test cases and channels tested.

## 10. Delivery priorities

1. Agree on shared interfaces and data contracts.
2. Implement observation normalization, detection, sanitization, and firewall.
3. Add one model adapter and structured action schema.
4. Add action validation and browser execution.
5. Add task-scoped local value injection and human approval.
6. Add UI and non-sensitive audit trail.
7. Add leakage/adversarial tests and record metrics.
8. Consider screenshot redaction/OCR only after the core path works.

## 11. Documentation map

- `ARCHITECTURE.md` — components, trust boundaries, data flow, API contracts, security controls.
- `AGENTS.md` — four workstreams, coding rules, integration protocol.
- `DATABASE_SCHEMA.md` — optional SQLite metadata schema and secret-retention rules.
- `PROJECT_OVERVIEW.md` — scope, goals, stack, acceptance criteria, evaluation.
