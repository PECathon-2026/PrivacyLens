"""
Browser Adapter and DOM Observation Extractor for PrivacyLens.
Interfaces with Playwright to extract structured PageObservations
and securely executes validated actions (including local secret injection).
"""

import re
from typing import Optional, List, Dict, Any
from pathlib import Path
from Core.contracts import PageElement, PageObservation, ProposedAction


class PlaywrightDOMExtractor:
    """
    Playwright-based browser controller and DOM normalizer.
    Responsible for extracting structured PageObservations and executing local actions.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    async def initialize(self):
        """Initializes the Playwright Chromium instance if available."""
        try:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"]
            )
            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 800}
            )
            self._page = await self._context.new_page()
            return True
        except Exception as e:
            # Fallback to simulated offline extractor if browser binaries are unavailable
            self._page = None
            return False

    async def navigate(self, url: str) -> bool:
        """Navigates to a given web URL or local file path."""
        if not self._page:
            return False
        try:
            await self._page.goto(url, wait_until="domcontentloaded")
            return True
        except Exception:
            return False

    async def observe(self, task_id: str) -> PageObservation:
        """
        Extracts a normalized PageObservation from the active page.
        Assigns stable element IDs and extracts input values.
        """
        if not self._page:
            # Fallback to demo page parser
            return self.extract_from_html_file(
                task_id=task_id,
                file_path=str(Path(__file__).parent.parent / "demo" / "sample_page.html")
            )

        title = await self._page.title()
        url = self._page.url
        visible_text = await self._page.inner_text("body")

        # Extract interactive form fields and buttons
        raw_elements = await self._page.evaluate("""() => {
            const items = [];
            let counter = 1;
            const nodes = document.querySelectorAll('input, select, textarea, button, form');

            for (const el of nodes) {
                // Determine label
                let label = '';
                if (el.id) {
                    const labelElem = document.querySelector(`label[for="${el.id}"]`);
                    if (labelElem) label = labelElem.innerText.trim();
                }
                if (!label && el.getAttribute('aria-label')) {
                    label = el.getAttribute('aria-label');
                }
                if (!label && el.placeholder) {
                    label = el.placeholder;
                }
                if (!label && (el.tagName === 'BUTTON' || el.type === 'submit')) {
                    label = el.innerText || el.value || 'Button';
                }

                const elemId = el.id ? `el_${el.id}` : `el_${counter++}`;
                items.push({
                    element_id: elemId,
                    role: el.tagName.toLowerCase() === 'button' ? 'button' : 'textbox',
                    label: label,
                    input_type: el.type || 'text',
                    name: el.name || '',
                    placeholder: el.placeholder || '',
                    value: el.value || '',
                    visible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length),
                    enabled: !el.disabled
                });
            }
            return items;
        }""")

        elements = [
            PageElement(
                element_id=item["element_id"],
                role=item["role"],
                label=item["label"],
                input_type=item["input_type"],
                name=item["name"],
                placeholder=item["placeholder"],
                value=item["value"],
                visible=item["visible"],
                enabled=item["enabled"],
            )
            for item in raw_elements
        ]

        return PageObservation(
            task_id=task_id,
            url=url,
            title=title,
            visible_text=visible_text,
            elements=elements,
        )

    async def execute_action(
        self,
        action: ProposedAction,
        resolved_secret: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes an action directly on the active web page.
        Local secrets are injected securely into the target element.
        NEVER logs or returns the secret value.
        """
        if not self._page:
            return {
                "success": True,
                "action": action.action_type,
                "target": action.target_element_id,
                "message": "Executed successfully (Simulated mode)."
            }

        # Convert element_id back to DOM selector
        dom_id = action.target_element_id.replace("el_", "")
        selector = f"#{dom_id}"

        try:
            if action.action_type in ("fill_local_value", "fill_public_value"):
                fill_value = resolved_secret if action.action_type == "fill_local_value" else action.public_value
                if fill_value is not None:
                    await self._page.fill(selector, fill_value)
                return {
                    "success": True,
                    "action": action.action_type,
                    "target": action.target_element_id,
                    "message": f"Field '{action.target_element_id}' filled successfully."
                }

            elif action.action_type in ("click", "request_approval"):
                await self._page.click(selector)
                return {
                    "success": True,
                    "action": action.action_type,
                    "target": action.target_element_id,
                    "message": f"Clicked element '{action.target_element_id}'."
                }

            return {
                "success": False,
                "error": f"Unsupported action type: {action.action_type}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to execute action on {action.target_element_id}: {str(e)}"
            }

    async def close(self):
        """Closes the Playwright browser session."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    @staticmethod
    def extract_from_html_file(task_id: str, file_path: str) -> PageObservation:
        """
        Parses a local HTML file without requiring active browser rendering.
        Guarantees reliable fallback testing and deterministic fixtures.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        title_match = re.search(r"<title>(.*?)</title>", content, re.IGNORECASE)
        title = title_match.group(1) if title_match else "Local Page"

        # Strip HTML tags for visible text approximation
        visible_text = re.sub(r"<[^>]+>", " ", content)
        visible_text = re.sub(r"\s+", " ", visible_text).strip()

        # Extract input and button elements using regex patterns
        elements: List[PageElement] = []
        input_pattern = re.compile(
            r'<input\s+([^>]*?)(?:/?>|>(?:</input>)?)',
            re.IGNORECASE
        )

        for match in input_pattern.finditer(content):
            attrs_str = match.group(1)
            attrs = dict(re.findall(r'(\w+)=["\']([^"\']*)["\']', attrs_str))
            
            el_id = attrs.get("id") or attrs.get("name") or f"input_{len(elements)+1}"
            input_type = attrs.get("type", "text")
            name = attrs.get("name", "")
            placeholder = attrs.get("placeholder", "")
            value = attrs.get("value", "")

            # Look for corresponding label in HTML
            label = ""
            if attrs.get("id"):
                lbl_match = re.search(
                    rf'<label\s+for=["\']{attrs["id"]}["\'][^>]*>(.*?)</label>',
                    content,
                    re.IGNORECASE
                )
                if lbl_match:
                    label = re.sub(r"<[^>]+>", "", lbl_match.group(1)).strip()

            elements.append(PageElement(
                element_id=f"el_{el_id}",
                role="textbox",
                label=label or placeholder or name,
                input_type=input_type,
                name=name,
                placeholder=placeholder,
                value=value,
                visible=True,
                enabled=True,
            ))

        # Also extract submit button
        btn_match = re.search(
            r'<button\s+[^>]*id=["\']([^"\']*)["\'][^>]*>(.*?)</button>',
            content,
            re.IGNORECASE | re.DOTALL
        )
        if btn_match:
            btn_id = btn_match.group(1)
            btn_text = re.sub(r"<[^>]+>", "", btn_match.group(2)).strip()
            elements.append(PageElement(
                element_id=f"el_{btn_id}",
                role="button",
                label=btn_text,
                input_type="submit",
                name="submit",
                value="",
                visible=True,
                enabled=True,
            ))

        return PageObservation(
            task_id=task_id,
            url=f"file:///{file_path.replace('\\', '/')}",
            title=title,
            visible_text=visible_text,
            elements=elements,
        )
