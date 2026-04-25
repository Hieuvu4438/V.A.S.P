import json
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import ValidationError

from reviewagent.config import Settings, get_settings
from reviewagent.llm.calibration import calibrate_confidence
from reviewagent.llm.prompts.decision_v1 import DECISION_SYSTEM_PROMPT, build_decision_user_prompt
from reviewagent.schemas.decision import DecisionLabel, DecisionResult

LLMCompletion = Callable[[str, str, str], Awaitable[str]]


class LLMGatewayError(Exception):
    pass


class LLMGateway:
    def __init__(self, settings: Settings | None = None, completion: LLMCompletion | None = None) -> None:
        self._settings = settings or get_settings()
        self._completion = completion

    async def generate_decision(self, prompt: str, input_data: dict[str, Any]) -> DecisionResult:
        if self._completion is None:
            return self._review_result("LLM provider is not configured for Phase 1 PoC.")

        user_prompt = build_decision_user_prompt(input_data)
        raw_response = await self._completion(self._settings.llm.model, prompt, user_prompt)
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
