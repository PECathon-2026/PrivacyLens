# PrivacyLens 🔒

> **Hackathon PS-004 · Privacy-Preserving AI Browser Agent**  
> *"Compute what is sensitive locally. Reason globally only on sanitized data."*

PrivacyLens is a local privacy gateway that sits between a browser automation agent and any external AI model.  
It detects, redacts, and vaults sensitive information **before** it ever leaves your device.

---

## Architecture at a Glance

```
Browser Page
    │
    ▼
[Playwright DOM Extractor]   ← Layer 2: Browser eyes & hands
    │  raw PageObservation
    ▼
[Sensitive Data Detector]    ← Layer 3a: Regex + checksum + metadata (Tier 1-3)
    │  detections + categories
    ▼
[Data Sanitizer]             ← Layer 3b: Replace values with [REDACTED:CATEGORY]
    │  SanitizedObservation  │
    │                        └──► [SessionSecretStore]  ← In-memory vault only
    ▼
[Privacy Firewall]           ← Layer 3c: Outbound payload inspection (fail-closed)
    │  FirewallDecision (ALLOW / BLOCK)
    ▼
[AI Model Client]            ← Layer 4: Sends ONLY sanitized context
    │  ProposedAction[]
    ▼
[Human Approval Gate]        ← Layer 5: Consequential actions require user sign-off
    │
    ▼
[Playwright Action Executor] ← Real secrets injected locally, never exposed to AI
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+ (via nvm recommended)

### 1 · Clone & Install

```bash
git clone https://github.com/PECathon-2026/PrivacyLens.git
cd PrivacyLens

# Python dependencies
pip install -r requirements.txt

# Install Playwright browser binaries
python -m playwright install chromium

# Frontend dependencies & production build
cd frontend
npm install
npm run build
cd ..
```

### 2 · Configure (optional)

```bash
cp .env.example .env
# Edit .env to add an AI API key if you want live reasoning.
# Without a key the system uses the built-in offline mock — fully functional.
```

### 3 · Run

```bash
python app.py
```

Open **http://127.0.0.1:8000** in your browser.

---

## Development Mode (hot-reload)

Run the backend and frontend separately for faster iteration:

```bash
# Terminal 1 — FastAPI backend
python app.py

# Terminal 2 — Vite dev server (proxies /api → http://127.0.0.1:8000)
cd frontend
npm run dev
# Open http://localhost:5173
```

---

## Running Tests

```bash
python -m pytest tests -v
```

Expected output: **15 passed** covering validators, detector, sanitizer, firewall, and the full end-to-end pipeline.

---

## Project Structure

```
PrivacyLens/
├── app.py                  # FastAPI gateway (all REST endpoints)
├── requirements.txt
├── .env.example
│
├── Core/                   # Local Privacy Engine
│   ├── contracts.py        # Canonical typed dataclasses
│   ├── detector.py         # Multi-tier sensitive data detection
│   ├── sanitizer.py        # Placeholder substitution + in-memory vault
│   ├── firewall.py         # Outbound payload firewall (fail-closed)
│   └── ai_client.py        # Model-agnostic AI adapter + offline mock
│
├── browser/
│   └── extractor.py        # Playwright DOM extraction + action execution
│
├── database/
│   └── models.py           # SQLite audit log (zero PII columns)
│
├── frontend/               # React 18 + Vite + Tailwind + shadcn/ui
│   ├── src/
│   │   ├── api/client.ts   # Typed API client (all FastAPI endpoints)
│   │   ├── components/     # UI components
│   │   ├── lib/demoData.ts # Demo fixture data (offline fallback)
│   │   └── types/index.ts  # TypeScript types
│   └── dist/               # Production build (served by FastAPI)
│
├── demo/
│   └── sample_page.html    # Synthetic flight checkout demo page
│
├── tests/
│   ├── test_privacy_engine.py   # 14 unit tests
│   └── test_e2e_pipeline.py     # 1 end-to-end pipeline test
│
└── Docs/
    ├── ARCHITECTURE.md
    ├── API_CONTRACTS.md
    └── DATABASE_SCHEMA.md
```

---

## Key Privacy Guarantees

| Property | Implementation |
|---|---|
| **Zero cloud PII** | Sanitizer replaces all sensitive values with `[REDACTED:CATEGORY]` before AI call |
| **In-memory vault** | Real values stored in `SessionSecretStore` — never written to disk or logs |
| **Fail-closed firewall** | Any exception in `PrivacyFirewall.inspect()` → automatic BLOCK |
| **Canary detection** | Firewall plants secret tokens; if they appear in egress payload → instant block |
| **Human-in-the-loop** | Consequential actions (form submit, payment) require explicit user approval |
| **Model-agnostic** | Privacy engine is independent of OpenAI / Gemini / Claude — providers are adapters |

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Gateway status |
| `POST` | `/api/tasks` | Create task session |
| `POST` | `/api/tasks/{id}/observe` | Extract, detect, sanitize, firewall |
| `POST` | `/api/tasks/{id}/firewall-check` | Inspect arbitrary payload |
| `POST` | `/api/tasks/{id}/propose-action` | AI action proposals (sanitized context only) |
| `POST` | `/api/tasks/{id}/execute-action` | Execute action via Playwright |
| `GET` | `/api/tasks/{id}/audit` | Non-sensitive audit trail |
| `GET` | `/demo-page` | Synthetic checkout HTML page |

---

## Team

Hackathon: **PECathon 2026** · Problem Statement: **PS-004**
