"""Provider-independent AI service with graceful degradation.

Talks to any OpenAI-compatible chat-completions API over HTTP. When AI is not
configured (no OPENAI_API_KEY), calls raise AIError which routers convert into a
clear 503 response rather than crashing the app.
"""

import json
import logging
import re
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger("legalconnect.ai")

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


class AIError(Exception):
    """Raised when the AI provider is unavailable or unconfigured."""


class AIService:
    @property
    def is_configured(self) -> bool:
        return settings.is_ai_configured

    def _configure(self) -> dict[str, str]:
        if not self.is_configured:
            raise AIError(
                "AI is not configured. Set OPENAI_API_KEY in your .env file "
                "to enable AI features."
            )
        base_url = (settings.openai_base_url or DEFAULT_OPENAI_BASE_URL).rstrip("/")
        model = settings.openai_model or DEFAULT_OPENAI_MODEL
        return {
            "base_url": base_url,
            "model": model,
            "api_key": settings.openai_api_key,
        }

    async def _complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 1000,
        temperature: float = 0.4,
    ) -> str:
        cfg = self._configure()
        payload = {
            "model": cfg["model"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        url = f"{cfg['base_url']}/chat/completions"
        headers = {"Authorization": f"Bearer {cfg['api_key']}"}
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(url, json=payload, headers=headers)
                break
            except Exception as exc:  # noqa: BLE001
                if attempt == 1:
                    logger.warning("AI request failed (%s): %s", type(exc).__name__, exc)
                    raise AIError("Could not reach the AI provider. Please try again later.") from exc
                logger.info(
                    "AI request transient failure (%s), retrying: %s", type(exc).__name__, exc
                )
        if resp.status_code == 429:
            logger.warning("AI provider rate-limited: HTTP 429")
            raise AIError(
                "The AI provider is rate-limiting requests or the API key's quota is exhausted "
                "(HTTP 429). Try again later or check your API key's quota."
            )
        if resp.status_code >= 400:
            logger.warning("AI provider error: HTTP %s", resp.status_code)
            raise AIError(
                f"The AI provider returned an error (HTTP {resp.status_code}). "
                "Check your API key and model configuration in .env."
            )
        try:
            data = resp.json()
        except Exception:  # noqa: BLE001
            logger.warning("AI provider returned an unparsable response")
            raise AIError("The AI provider returned an unparsable response.") from None
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return (content or "").strip()

    async def _json(self, *, system: str, user: str, max_tokens: int = 1000) -> Any:
        text = await self._complete(
            system=system + "\nRespond with valid JSON only.",
            user=user,
            max_tokens=max_tokens,
            temperature=0.2,
        )
        try:
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned).strip()
                cleaned = re.sub(r"\s*```$", "", cleaned).strip()
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                for i, ch in enumerate(cleaned):
                    if ch in "{[":
                        try:
                            return json.JSONDecoder().raw_decode(cleaned[i:].strip())[0]
                        except json.JSONDecodeError:
                            break
                raise
        except Exception:  # noqa: BLE001
            logger.warning("AI JSON parse failed; raw text=%s", text[:500])
            raise AIError("The AI provider returned an unparsable response.")

    async def chat(self, message: str, history: Optional[list[dict[str, str]]] = None) -> str:
        history = history or []
        system = (
            "You are Legal Connect, a helpful, concise legal assistant for non-lawyers. "
            "Explain legal concepts in plain language. Remind users that you are not a "
            "replacement for a qualified lawyer and recommend consulting a verified lawyer "
            "for specific legal advice."
        )
        turns = "\n".join(
            f"{'User' if t.get('role')=='user' else 'Assistant'}: {t.get('content','')}"
            for t in history[-6:]
        )
        combined = f"Conversation so far:\n{turns}\n\nUser: {message}" if turns else message
        return await self._complete(system=system, user=combined, max_tokens=1200, temperature=0.5)

    async def summarize(self, text: str) -> str:
        system = (
            "You are a legal document summarizer. Produce a concise plain-English summary "
            "with key points and any important dates, amounts, or obligations."
        )
        return await self._complete(
            system=system, user=f"Summarize the following:\n\n{text}", max_tokens=600
        )

    async def answer_faq(self, question: str) -> dict[str, Any]:
        system = (
            "Answer common legal questions in plain language. Return JSON with keys: "
            '"answer" (string), "related_categories" (list of strings), '
            '"suggested_action" (string).'
        )
        return await self._json(system=system, user=question, max_tokens=2048)

    async def predict_category(self, description: str, categories: list[str]) -> dict[str, Any]:
        system = (
            "Classify a legal issue into one of the provided categories. Return JSON with keys: "
            '"category" (one string from the provided list), "confidence" (number 0-1), '
            '"explanation" (string, <=2 sentences).'
        )
        user = (
            f"Provided categories: {', '.join(categories)}\n\n"
            f'Issue description: "{description}"'
        )
        return await self._json(system=system, user=user, max_tokens=1024)

    async def translate(self, text: str, target_language: str) -> str:
        system = (
            "Translate the user's text into the requested language. Return only the "
            "translation, preserving legal terminology accurately."
        )
        return await self._complete(
            system=system,
            user=f"Translate into {target_language}:\n\n{text}",
            max_tokens=2048,
            temperature=0.3,
        )


ai_service = AIService()
