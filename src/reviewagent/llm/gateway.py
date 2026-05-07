import json
import logging
from typing import Any

import httpx
from pydantic import ValidationError

from reviewagent.config import Settings, get_settings
from reviewagent.llm.calibration import calibrate_confidence
from reviewagent.llm.prompts.decision_v1 import DECISION_SYSTEM_PROMPT, build_decision_user_prompt
from reviewagent.schemas.decision import DecisionLabel, DecisionResult

logger = logging.getLogger(__name__)


class LLMGatewayError(Exception):
    pass


class LLMGateway:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client: httpx.AsyncClient | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self._settings.llm.api_key)

    def _build_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._settings.llm.openrouter_base_url,
            timeout=httpx.Timeout(self._settings.llm.timeout_seconds),
            headers={
                "Authorization": f"Bearer {self._settings.llm.api_key}",
                "Content-Type": "application/json",
            },
        )

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = self._build_client()
        return self._client

    async def _call_openrouter(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self._settings.llm.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        try:
            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            # OpenRouter free model may wrap JSON in markdown fences
            content = content.strip()
            if content.startswith("```"):
                content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return content
        except httpx.HTTPStatusError as exc:
            raise LLMGatewayError(f"OpenRouter HTTP {exc.response.status_code}: {exc.response.text}") from exc
        except httpx.RequestError as exc:
            raise LLMGatewayError(f"OpenRouter network error: {exc}") from exc
        except (KeyError, IndexError) as exc:
            raise LLMGatewayError(f"Unexpected OpenRouter response format: {exc}") from exc

    async def generate_decision(self, prompt: str, input_data: dict[str, Any]) -> DecisionResult:
        if not self.is_configured:
            return self._review_result("OpenRouter API key is not configured.")

        user_prompt = build_decision_user_prompt(input_data)
        raw_response = await self._call_openrouter(prompt, user_prompt)
        return self._parse_decision(raw_response)

    async def generate_decision_v1(self, input_data: dict[str, Any]) -> DecisionResult:
        return await self.generate_decision(DECISION_SYSTEM_PROMPT, input_data)

    def _parse_decision(self, raw_response: str) -> DecisionResult:
        try:
            data = json.loads(raw_response)
            if "confidence_raw" in data:
                data["confidence_calibrated"] = calibrate_confidence(float(data["confidence_raw"]))
            return DecisionResult.model_validate(data)
        except (json.JSONDecodeError, TypeError, ValueError, ValidationError) as exc:
            raise LLMGatewayError(f"Invalid decision response: {exc}") from exc

    def _review_result(self, rationale: str) -> DecisionResult:
        return DecisionResult(
            decision=DecisionLabel.REVIEW,
            confidence_raw=0.0,
            confidence_calibrated=calibrate_confidence(0.0),
            rationale=rationale,
            flags=["LLM_NOT_CONFIGURED"],
            sub_scores={"metadata_completeness": 0.0, "source_reliability": 0.0},
        )

    async def aclose(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
