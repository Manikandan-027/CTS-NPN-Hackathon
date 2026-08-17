import json
import re
from typing import Any

from .groq_client import create_groq_client
from .prompts import RCA_SYSTEM_PROMPT


GROQ_MODEL = "openai/gpt-oss-20b"


RCA_SCHEMA = {
    "type": "object",
    "properties": {
        "root_cause": {"type": "string"},
        "evidence": {
            "type": "array",
            "items": {"type": "string"},
        },
        "resolution": {"type": "string"},
        "prevention": {"type": "string"},
        "summary": {"type": "string"},
    },
    "required": [
        "root_cause",
        "evidence",
        "resolution",
        "prevention",
        "summary",
    ],
    "additionalProperties": False,
}


def _normalize_json_text(raw_content: str) -> str:
    """Strip markdown fences when the model wraps JSON in triple backticks."""
    if not isinstance(raw_content, str):
        raise ValueError("Groq response content is not a string.")

    candidate = raw_content.strip()

    if candidate.startswith("```"):
        match = re.search(
            r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```",
            candidate,
            re.DOTALL | re.IGNORECASE,
        )
        if match:
            candidate = match.group(1)

    return candidate


def _validate_response_shape(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise ValueError("Groq returned a non-object JSON response.")

    required_fields = {
        "root_cause",
        "evidence",
        "resolution",
        "prevention",
        "summary",
    }

    missing = sorted(required_fields - set(result.keys()))
    if missing:
        raise ValueError(
            "Groq response missing required RCA fields: "
            f"{missing}"
        )

    if not isinstance(result["evidence"], list):
        raise ValueError("Groq evidence field must be a list of evidence IDs.")

    if not all(isinstance(item, str) for item in result["evidence"]):
        raise ValueError(
            "Groq evidence field must contain only string evidence IDs."
        )

    return result


def validate_evidence_ids(
    result: dict,
    allowed_evidence_ids: set[str],
) -> dict:
    """Ensure every returned evidence ID is drawn from the supplied historical context."""
    returned_ids = set(result.get("evidence", []))
    invalid_ids = returned_ids - allowed_evidence_ids

    if invalid_ids:
        raise ValueError(
            f"Invalid evidence IDs returned by Groq: {sorted(invalid_ids)}"
        )

    return result


def generate_structured_rca(
    incident: str,
    historical_evidence: list[dict],
    repository_evidence: dict | None = None,
    stack_trace: str | None = None,
) -> dict:
    """
    Generate a structured RCA from the current incident and retrieved historical evidence.

    Repository evidence is optional; if not available, it is passed as a lightweight
    placeholder object instead of breaking the LLM call.
    """
    if not incident or not incident.strip():
        raise ValueError("Incident description cannot be empty.")

    historical_evidence = historical_evidence or []
    repository_evidence = repository_evidence or {
        "available": False,
        "message": "Repository evidence was not supplied in this runtime.",
    }

    allowed_evidence_ids = {
        str(item.get("id"))
        for item in historical_evidence
        if isinstance(item, dict) and item.get("id") is not None
    }

    user_prompt = {
        "current_incident": incident,
        "stack_trace": stack_trace,
        "historical_evidence": historical_evidence,
        "repository_evidence": repository_evidence,
        "allowed_evidence_ids": sorted(allowed_evidence_ids),
    }

    client = create_groq_client()

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": RCA_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": json.dumps(user_prompt, ensure_ascii=False),
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "incident_rca",
                    "schema": RCA_SCHEMA,
                },
            },
        )
    except Exception as exc:
        raise RuntimeError(f"Groq request failed: {exc}") from exc

    try:
        content = response.choices[0].message.content
    except Exception as exc:
        raise RuntimeError("Groq returned no usable message content.") from exc

    if not content:
        raise RuntimeError("Groq returned an empty response.")

    try:
        parsed = json.loads(_normalize_json_text(content))
    except json.JSONDecodeError as exc:
        raise ValueError("Groq returned malformed JSON.") from exc

    result = _validate_response_shape(parsed)
    result = validate_evidence_ids(result, allowed_evidence_ids)
    return result