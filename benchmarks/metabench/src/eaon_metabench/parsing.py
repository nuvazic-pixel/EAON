from __future__ import annotations

import json
import re

from pydantic import ValidationError

from eaon_metabench.models import ModelAnswer


_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def parse_model_answer(text: str) -> tuple[ModelAnswer | None, str | None]:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(r"\s*```$", "", candidate)

    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        match = _JSON_OBJECT.search(candidate)
        if not match:
            return None, "No JSON object found in model response."
        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            return None, f"Invalid JSON: {exc}"

    try:
        return ModelAnswer.model_validate(payload), None
    except ValidationError as exc:
        return None, f"Response schema validation failed: {exc}"
