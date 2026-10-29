"""
PrivacyLens — Local Privacy Gateway & Full-Stack Orchestration Server.
Coordinates Browser Automation, Core Privacy Engine, AI Model Adapter, and UI Dashboard.
"""

import os
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from Core.contracts import (
    PageObservation,
    SanitizedObservation,
    FirewallDecision,
    ProposedAction,
    AuditEvent,
)
from Core.detector import SensitiveDataDetector
from Core.sanitizer import DataSanitizer, SessionSecretStore
from Core.firewall import PrivacyFirewall
from Core.ai_client import AIModelClient
from browser.extractor import PlaywrightDOMExtractor
from database.models import AuditDatabase

# Initialize Core Services
app = FastAPI(
    title="PrivacyLens Gateway",
    description="Local privacy gateway between browser agents and AI models.",
    version="1.0.0"
)

# Enable CORS for local Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Persistent metadata repository & in-memory session vaults
audit_db = AuditDatabase()
vault = SessionSecretStore()
detector = SensitiveDataDetector()
sanitizer = DataSanitizer(detector=detector, secret_store=vault)
firewall = PrivacyFirewall(detector=detector)
ai_client = AIModelClient()
browser_extractor = PlaywrightDOMExtractor(headless=True)

# Cache latest task states in memory: {task_id: {"raw": ..., "sanitized": ...}}
task_state_cache: Dict[str, Dict[str, Any]] = {}


# --- Request Models ---
class CreateTaskRequest(BaseModel):
    task_id: str
    task_label: str = "Flight Booking & Checkout"


class ObserveRequest(BaseModel):
    url: Optional[str] = None
    use_sample_page: bool = True


class FirewallCheckRequest(BaseModel):
    sanitized_observation: Dict[str, Any]
    canaries: Optional[List[str]] = None


class ProposeActionRequest(BaseModel):
    task_prompt: str = "Complete booking details and proceed to payment"


class ExecuteActionRequest(BaseModel):
    action_type: str
    target_element_id: str
    value_purpose: Optional[str] = None
    public_value: Optional[str] = None


# --- API Routes ---

@app.get("/health")
def health_check():
    """Health status and privacy engine verification."""
    return {
        "status": "online",
        "gateway": "PrivacyLens Local Gateway",
        "version": "1.0.0",
        "mode": "Offline Mock & Live Provider Ready",
        "firewall": "ARMED_FAIL_CLOSED",
    }


@app.post("/api/tasks")
def create_task(req: CreateTaskRequest):
    """Initializes a new task session and audits the event."""
    audit_db.create_task(req.task_id, req.task_label)
    audit_db.record_privacy_event(AuditEvent(
        task_id=req.task_id,
        timestamp=time.strftime("%H:%M:%S"),
        event_type="task_created",
        category="TASK_SESSION",
        item_count=1,
        decision="INITIALIZED",
    ))
    return {"task_id": req.task_id, "status": "created"}


@app.post("/api/tasks/{task_id}/observe")
async def observe_and_sanitize(task_id: str, req: ObserveRequest = Body(...)):
    """
    1. Extracts DOM observation from Playwright or sample page.
    2. Runs multi-tier sensitive data detection.
    3. Replaces sensitive spans with semantic placeholders.
    4. Caches raw values in the local in-memory session vault.
    5. Audits outbound payload through the Privacy Firewall.
    """
    sample_page_path = str(Path(__file__).parent / "demo" / "sample_page.html")

    if req.use_sample_page or not req.url:
        raw_obs = browser_extractor.extract_from_html_file(task_id, sample_page_path)
    else:
        raw_obs = await browser_extractor.observe(task_id)

    # Sanitize observation locally
    sanitized_obs, detections = sanitizer.sanitize_observation(raw_obs)

    # Outbound Firewall Pre-flight audit
    active_secrets = vault.get_active_secrets(task_id)
    firewall_decision = firewall.inspect(sanitized_obs, active_secrets=active_secrets)

    # Record non-sensitive audit events
    audit_db.record_privacy_event(AuditEvent(
        task_id=task_id,
        timestamp=time.strftime("%H:%M:%S"),
        event_type="observation_sanitized",
        category="PII_TRANSFORMATION",
        item_count=len(detections),
        decision="PLACEHOLDERS_SUBSTITUTED",
    ))

    audit_db.record_privacy_event(AuditEvent(
        task_id=task_id,
        timestamp=time.strftime("%H:%M:%S"),
        event_type="firewall_inspection",
        category="OUTBOUND_EGRESS",
        item_count=len(sanitized_obs.elements),
        decision="APPROVED" if firewall_decision.is_allowed else "BLOCKED",
    ))

    # Cache state for this task
    task_state_cache[task_id] = {
        "raw": raw_obs,
        "sanitized": sanitized_obs,
        "detections": detections,
    }

    return {
        "task_id": task_id,
        "raw_observation": raw_obs.to_dict(),
        "sanitized_observation": sanitized_obs.to_dict(),
        "firewall_decision": firewall_decision.to_dict(),
        "vault_secret_count": len(active_secrets),
    }


@app.post("/api/tasks/{task_id}/firewall-check")
def firewall_check(task_id: str, req: FirewallCheckRequest):
    """
    Inspects an outbound payload against known secrets and planted canaries.
    Fails closed if a canary or unredacted secret is found.
    """
    try:
        sanitized_obs = SanitizedObservation(**req.sanitized_observation)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid SanitizedObservation schema: {str(e)}")

    active_secrets = vault.get_active_secrets(task_id)
    decision = firewall.inspect(sanitized_obs, active_secrets=active_secrets, canaries=req.canaries)

    audit_db.record_privacy_event(AuditEvent(
        task_id=task_id,
        timestamp=time.strftime("%H:%M:%S"),
        event_type="firewall_audit_request",
        category="EGRESS_PAYLOAD",
        item_count=1 if decision.canary_leaked else 0,
        decision="BLOCKED" if not decision.is_allowed else "APPROVED",
        error_code="CANARY_LEAK" if decision.canary_leaked else None,
    ))

    return decision.to_dict()


@app.post("/api/tasks/{task_id}/propose-action")
async def propose_action(task_id: str, req: ProposeActionRequest):
    """
    Sends the sanitized context to the AI reasoning engine (or offline mock)
    and receives structured action proposals.
    """
    cached = task_state_cache.get(task_id)
    if not cached:
        raise HTTPException(status_code=404, detail="Task observation not found. Run observe first.")

    sanitized_obs: SanitizedObservation = cached["sanitized"]
    actions = await ai_client.propose_actions(req.task_prompt, sanitized_obs)

    for action in actions:
        audit_db.record_privacy_event(AuditEvent(
            task_id=task_id,
            timestamp=time.strftime("%H:%M:%S"),
            event_type="action_proposed",
            category=action.action_type,
            item_count=1,
            decision=action.reasoning[:50],
        ))

    return {"actions": [a.to_dict() for a in actions]}


@app.post("/api/tasks/{task_id}/execute-action")
async def execute_action(task_id: str, req: ExecuteActionRequest):
    """
    Executes an action via Playwright.
    When local value injection is requested, resolves the real secret from
    the in-memory vault and fills the webpage directly without exposing it to AI.
    """
    cached = task_state_cache.get(task_id)
    resolved_secret = None

    if req.action_type == "fill_local_value":
        # Resolve real secret from in-memory session vault
        active_secrets = vault.get_active_secrets(task_id)
        if active_secrets:
            # Match by category if available, otherwise take the matched secret for target
            resolved_secret = active_secrets[0]
            if cached:
                for det in cached.get("detections", []):
                    if det.target_element_id == req.target_element_id and det.secret_ref:
                        resolved_secret = vault.resolve(task_id, det.secret_ref, det.category)
                        break

    action_obj = ProposedAction(
        action_type=req.action_type,
        target_element_id=req.target_element_id,
        value_purpose=req.value_purpose or "",
        public_value=req.public_value or "",
    )

    result = await browser_extractor.execute_action(action_obj, resolved_secret=resolved_secret)

    audit_db.record_privacy_event(AuditEvent(
        task_id=task_id,
        timestamp=time.strftime("%H:%M:%S"),
        event_type="action_executed_locally",
        category=req.action_type,
        item_count=1,
        decision=f"injected_into_{req.target_element_id}",
    ))

    return result


@app.get("/api/tasks/{task_id}/audit")
def get_task_audit(task_id: str):
    """Returns non-sensitive audit timeline records for a task."""
    events = audit_db.get_task_events(task_id)
    return {"task_id": task_id, "events": events}


@app.get("/demo-page", response_class=HTMLResponse)
def get_demo_page():
    """Serves the synthetic flight checkout demo HTML page."""
    sample_page_path = Path(__file__).parent / "demo" / "sample_page.html"
    if sample_page_path.exists():
        with open(sample_page_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Sample Demo Page Not Found</h1>"


# --- Serve React Frontend Static Assets ---
dist_path = Path(__file__).parent / "frontend" / "dist"
if dist_path.exists():
    app.mount("/assets", StaticFiles(directory=str(dist_path / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        file_path = dist_path / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(dist_path / "index.html")


if __name__ == "__main__":
    import uvicorn
    print("=" * 65)
    print("🚀 PrivacyLens Local Privacy Gateway Starting...")
    print("   Principle: Compute locally. Reason on sanitized data.")
    print("   Gateway URL: http://127.0.0.1:8000")
    print("   Demo Page:   http://127.0.0.1:8000/demo-page")
    print("=" * 65)
    uvicorn.run(app, host="127.0.0.1", port=8000)

