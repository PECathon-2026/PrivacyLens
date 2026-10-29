"""
AI Model Provider Adapter and Offline Mock Reasoning Engine for PrivacyLens.
Interfaces with external LLMs or provides deterministic offline action proposals.
Treats all model output as untrusted and enforces strict structured output validation.
"""

import os
import json
import re
from typing import List, Optional, Dict, Any
from Core.contracts import SanitizedObservation, ProposedAction


class AIModelClient:
    """
    Model-independent AI client adapter.
    Operates strictly on SanitizedObservations.
    Provides offline mock reasoning when external APIs are unconfigured.
    """

    ALLOWED_ACTIONS = {
        "click",
        "fill_local_value",
        "fill_public_value",
        "select_option",
        "scroll",
        "request_approval",
    }

    CONSEQUENTIAL_KEYWORDS = re.compile(
        r"pay|checkout|confirm|book|purchase|authorize|delete|submit",
        re.IGNORECASE
    )

    def __init__(self, api_key: Optional[str] = None, provider: str = "auto"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.provider = provider
        self.is_offline_mode = not bool(self.api_key)

    async def propose_actions(
        self,
        task: str,
        sanitized_obs: SanitizedObservation
    ) -> List[ProposedAction]:
        """
        Receives sanitized page context and generates structured action proposals.
        Automatically falls back to offline mock reasoning if no API key is available.
        """
        if self.is_offline_mode:
            return self._mock_reasoning_pipeline(task, sanitized_obs)

        try:
            # If API key is available, query remote model with JSON schema
            return await self._call_remote_provider(task, sanitized_obs)
        except Exception:
            # Fail gracefully to offline mock on network/API failure
            return self._mock_reasoning_pipeline(task, sanitized_obs)

    def _mock_reasoning_pipeline(
        self,
        task: str,
        sanitized_obs: SanitizedObservation
    ) -> List[ProposedAction]:
        """
        Deterministic, offline reasoning engine for demo and test environments.
        Analyzes sanitized fields and forms a logical action plan.
        """
        actions: List[ProposedAction] = []

        # 1. Inspect elements needing local value injection
        for elem in sanitized_obs.elements:
            if not elem.visible or not elem.enabled:
                continue

            val = elem.value or ""
            # If value was redacted, model proposes fill_local_value with semantic purpose
            if val.startswith("[REDACTED:"):
                category = val.replace("[REDACTED:", "").replace("]", "").strip()
                actions.append(ProposedAction(
                    action_type="fill_local_value",
                    target_element_id=elem.element_id,
                    value_purpose=category,
                    reasoning=f"Task requires entering authorized {category} into field '{elem.label}' via local vault.",
                ))

        # 2. Inspect buttons and form submissions
        for elem in sanitized_obs.elements:
            if elem.role == "button" or elem.input_type == "submit":
                label = elem.label or elem.name or "Submit"
                if self.CONSEQUENTIAL_KEYWORDS.search(label):
                    # Flag consequential action for mandatory Human-in-the-Loop approval
                    actions.append(ProposedAction(
                        action_type="request_approval",
                        target_element_id=elem.element_id,
                        public_value=label,
                        reasoning=f"CONSEQUENTIAL ACTION: Triggering '{label}' on '{elem.element_id}' is irreversible and requires explicit human approval.",
                    ))
                else:
                    actions.append(ProposedAction(
                        action_type="click",
                        target_element_id=elem.element_id,
                        reasoning=f"Navigate or continue form via '{label}'.",
                    ))

        return self.validate_actions(actions, sanitized_obs)

    async def _call_remote_provider(
        self,
        task: str,
        sanitized_obs: SanitizedObservation
    ) -> List[ProposedAction]:
        """Calls remote model provider using standard JSON schema format."""
        import urllib.request

        system_prompt = (
            "You are an AI browser assistant. You receive a sanitized observation of a webpage. "
            "All sensitive values have been replaced by [REDACTED:CATEGORY]. "
            "Propose a JSON array of actions from ['click', 'fill_local_value', 'fill_public_value', 'request_approval']. "
            "Never guess or hallucinate raw sensitive data. Return pure JSON."
        )

        user_content = json.dumps({
            "task": task,
            "url": sanitized_obs.url,
            "title": sanitized_obs.title,
            "sanitized_text": sanitized_obs.sanitized_text,
            "elements": [e.to_dict() for e in sanitized_obs.elements]
        })

        # Example generic request formatting for OpenAI-compatible endpoint
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "response_format": {"type": "json_object"}
        }

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            content = res_data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            raw_actions = parsed.get("actions", [])
            actions = [ProposedAction(**a) for a in raw_actions]
            return self.validate_actions(actions, sanitized_obs)

    def validate_actions(
        self,
        actions: List[ProposedAction],
        sanitized_obs: SanitizedObservation
    ) -> List[ProposedAction]:
        """
        Validates proposed actions against schema and target bounds.
        Rejects unknown actions or target elements that do not exist.
        """
        valid_element_ids = {e.element_id for e in sanitized_obs.elements}
        validated: List[ProposedAction] = []

        for action in actions:
            # 1. Action type allowlist check
            if action.action_type not in self.ALLOWED_ACTIONS:
                continue

            # 2. Target element existence check
            if action.target_element_id not in valid_element_ids:
                continue

            # 3. Code injection prevention (reject arbitrary scripts)
            if any(danger in (action.public_value or "").lower() for danger in ("<script", "javascript:", "eval(")):
                continue

            validated.append(action)

        return validated

