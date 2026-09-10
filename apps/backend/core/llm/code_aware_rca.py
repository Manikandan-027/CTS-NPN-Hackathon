from __future__ import annotations

import json
import re
from typing import Any

from .groq_client import create_groq_client


# ============================================================
# MODEL
# ============================================================

CODE_RCA_MODEL = "qwen/qwen3.6-27b"


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are a production Code-Aware Root Cause Analysis engine.

Analyze the current incident using ONLY the supplied:
1. Current incident
2. Historical incidents
3. Repository findings
4. Repository code context

Your task:
- Identify the most likely root cause.
- Identify the exact repository file and line supplied in the findings.
- Explain the evidence.
- Give a practical developer fix.
- Give prevention guidance.
- Calculate a confidence score between 0 and 1.

STRICT RULES:

1. NEVER invent a file.
2. NEVER invent a line number.
3. NEVER invent code.
4. file_path MUST come from repository findings.
5. line_start MUST correspond to a supplied repository finding.
6. line_end MUST correspond to a supplied repository finding.
7. Historical incidents are supporting evidence only.
8. Repository evidence has priority.
9. If evidence is weak, reduce confidence.
10. Do not guess.

Return ONLY valid JSON.

Required JSON:

{
  "root_cause": "string",
  "file_path": "string",
  "line_start": 1,
  "line_end": 1,
  "evidence": ["string"],
  "suggested_fix": "string",
  "prevention": "string",
  "confidence": 0.0,
  "summary": "string"
}

Do not return markdown.
Do not return ```json.
Do not return explanations outside the JSON.
""".strip()


# ============================================================
# JSON EXTRACTION
# ============================================================

def _extract_json(text: str) -> dict[str, Any]:

    if not text:
        raise ValueError("Qwen returned an empty response.")

    text = text.strip()

    # Remove <think> blocks if the model returned them.
    text = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    ).strip()

    # Remove markdown fences.
    text = re.sub(
        r"^```json\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"^```\s*",
        "",
        text,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    # Direct JSON.
    try:
        result = json.loads(text)

        if isinstance(result, dict):
            return result

    except json.JSONDecodeError:
        pass

    # Find JSON object inside response.
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError(
            "Qwen response did not contain a valid JSON object."
        )

    candidate = text[start:end + 1]

    try:
        result = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Qwen returned malformed JSON: {exc}"
        ) from exc

    if not isinstance(result, dict):
        raise ValueError(
            "Qwen JSON response is not an object."
        )

    return result


# ============================================================
# REPOSITORY LOCATION VALIDATION
# ============================================================

def _validate_location(
    result: dict[str, Any],
    repository_evidence: dict[str, Any],
) -> dict[str, Any]:

    findings = repository_evidence.get(
        "findings",
        [],
    )

    allowed = []

    for finding in findings:

        if not isinstance(finding, dict):
            continue

        try:
            path = str(
                finding["file_path"]
            )

            start = int(
                finding["line_start"]
            )

            end = int(
                finding["line_end"]
            )

            allowed.append(
                {
                    "file_path": path,
                    "line_start": start,
                    "line_end": end,
                }
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            continue

    if not allowed:
        raise ValueError(
            "Repository evidence contains no valid code locations."
        )

    qwen_path = str(
        result.get("file_path", "")
    )

    try:
        qwen_start = int(
            result.get("line_start", 0)
        )

        qwen_end = int(
            result.get("line_end", 0)
        )

    except (
        TypeError,
        ValueError,
    ):
        qwen_start = 0
        qwen_end = 0

    # --------------------------------------------------------
    # EXACT MATCH
    # --------------------------------------------------------

    for item in allowed:

        if (
            item["file_path"] == qwen_path
            and item["line_start"] == qwen_start
            and item["line_end"] == qwen_end
        ):
            return result

    # --------------------------------------------------------
    # SAME FILE
    #
    # Qwen may return a nearby line from the supplied context.
    # Normalize it to the actual repository finding.
    # --------------------------------------------------------

    same_file = [
        item
        for item in allowed
        if item["file_path"] == qwen_path
    ]

    if same_file:

        closest = min(
            same_file,
            key=lambda item: abs(
                item["line_start"] - qwen_start
            ),
        )

        result["line_start"] = closest["line_start"]
        result["line_end"] = closest["line_end"]

        return result

    # --------------------------------------------------------
    # UNKNOWN FILE
    # --------------------------------------------------------

    raise ValueError(
        "Qwen selected a file that is not present in "
        "repository evidence."
    )


# ============================================================
# NORMALIZE RESULT
# ============================================================

def _normalize_result(
    result: dict[str, Any],
    repository_evidence: dict[str, Any],
) -> dict[str, Any]:

    required = [
        "root_cause",
        "file_path",
        "line_start",
        "line_end",
        "evidence",
        "suggested_fix",
        "prevention",
        "confidence",
        "summary",
    ]

    for field in required:

        if field not in result:
            raise ValueError(
                f"Qwen response missing required field: {field}"
            )

    result["root_cause"] = str(
        result["root_cause"]
    )

    result["file_path"] = str(
        result["file_path"]
    )

    result["line_start"] = int(
        result["line_start"]
    )

    result["line_end"] = int(
        result["line_end"]
    )

    result["suggested_fix"] = str(
        result["suggested_fix"]
    )

    result["prevention"] = str(
        result["prevention"]
    )

    result["summary"] = str(
        result["summary"]
    )

    evidence = result["evidence"]

    if isinstance(evidence, str):
        evidence = [evidence]

    if not isinstance(evidence, list):
        raise ValueError(
            "Qwen evidence must be a list."
        )

    result["evidence"] = [
        str(item)
        for item in evidence
    ]

    try:
        confidence = float(
            result["confidence"]
        )
    except (
        TypeError,
        ValueError,
    ):
        confidence = 0.0

    confidence = max(
        0.0,
        min(1.0, confidence),
    )

    result["confidence"] = round(
        confidence,
        4,
    )

    # Validate against actual repository evidence.
    result = _validate_location(
        result,
        repository_evidence,
    )

    return result


# ============================================================
# COMPACT PROMPT
# ============================================================

def _build_prompt(
    incident: str,
    historical_evidence: list[dict[str, Any]],
    repository_evidence: dict[str, Any],
    stack_trace: str | None,
) -> str:

    # --------------------------------------------------------
    # Repository findings
    #
    # Limit context to prevent Groq TPM problems.
    # --------------------------------------------------------

    findings = repository_evidence.get(
        "findings",
        [],
    )

    compact_findings = []

    for finding in findings[:8]:

        if not isinstance(finding, dict):
            continue

        compact_findings.append(
            {
                "file_path": finding.get(
                    "file_path"
                ),
                "line_start": finding.get(
                    "line_start"
                ),
                "line_end": finding.get(
                    "line_end"
                ),
                "score": finding.get(
                    "score"
                ),
                "matched_terms": finding.get(
                    "matched_terms",
                    [],
                )[:8],
                "evidence": finding.get(
                    "evidence",
                    [],
                )[:3],
                "context": str(
                    finding.get(
                        "context",
                        "",
                    )
                )[:1200],
            }
        )

    # --------------------------------------------------------
    # Historical incidents
    # --------------------------------------------------------

    compact_history = []

    for item in historical_evidence[:5]:

        if not isinstance(item, dict):
            continue

        compact_history.append(
            {
                "incident_id": item.get(
                    "incident_id"
                ),
                "incident": str(
                    item.get(
                        "incident",
                        "",
                    )
                )[:500],
                "root_cause": str(
                    item.get(
                        "root_cause",
                        "",
                    )
                )[:500],
                "resolution": str(
                    item.get(
                        "resolution",
                        "",
                    )
                )[:500],
                "confidence": item.get(
                    "confidence"
                ),
            }
        )

    payload = {
        "CURRENT_INCIDENT": incident[:2000],

        "STACK_TRACE": (
            stack_trace[-2500:]
            if stack_trace
            else ""
        ),

        "HISTORICAL_INCIDENTS":
            compact_history,

        "REPOSITORY_FINDINGS":
            compact_findings,

        "TASK": (
            "Find the most likely root cause from the supplied "
            "repository evidence. Select an exact supplied "
            "repository location. Explain why the code caused "
            "the incident and provide the developer fix."
        ),
    }

    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    )


# ============================================================
# MAIN FUNCTION
# ============================================================

def generate_code_aware_rca(
    incident: str,
    historical_evidence: list[dict[str, Any]],
    repository_evidence: dict[str, Any],
    stack_trace: str | None = None,
) -> dict[str, Any]:

    if not incident or not incident.strip():
        raise ValueError(
            "Incident description cannot be empty."
        )

    if not repository_evidence.get(
        "available"
    ):
        raise ValueError(
            "Repository evidence is required."
        )

    if not repository_evidence.get(
        "findings"
    ):
        raise ValueError(
            "Repository evidence contains no findings."
        )

    # --------------------------------------------------------
    # Build compact request
    # --------------------------------------------------------

    prompt = _build_prompt(
        incident=incident,
        historical_evidence=historical_evidence,
        repository_evidence=repository_evidence,
        stack_trace=stack_trace,
    )

    print()
    print("=" * 72)
    print("  PHASE 7/8 | Qwen Code-Aware Resolution")
    print("=" * 72)
    print("  RUNNING")
    print(
        f"  Model              : {CODE_RCA_MODEL}"
    )
    print(
        f"  Prompt size        : {len(prompt)} characters"
    )
    print(
        f"  Historical         : {len(historical_evidence[:5])}"
    )
    print(
        f"  Repository findings: "
        f"{len(repository_evidence.get('findings', [])[:8])}"
    )
    print(
        "  Output mode        : JSON Object"
    )

    # --------------------------------------------------------
    # Groq
    # --------------------------------------------------------

    client = create_groq_client()

    try:

        response = client.chat.completions.create(

            model=CODE_RCA_MODEL,

            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],

            # Qwen 3.6 supports JSON Object Mode.
            response_format={
                "type": "json_object"
            },

            # Non-thinking mode keeps this fast and small.
            reasoning_effort="none",

            temperature=0.2,

            max_completion_tokens=1000,

            stream=False,
        )

    except Exception as exc:

        print("  ✗ QWEN REQUEST FAILED")

        raise RuntimeError(
            "Qwen code-aware RCA failed: "
            f"{exc}"
        ) from exc

    # --------------------------------------------------------
    # Extract content
    # --------------------------------------------------------

    try:

        message = response.choices[0].message

        content = message.content

    except Exception as exc:

        raise RuntimeError(
            "Qwen returned no usable response."
        ) from exc

    if not content:

        raise RuntimeError(
            "Qwen returned empty content."
        )

    print(
        f"  Response size      : {len(content)} characters"
    )

    # --------------------------------------------------------
    # Parse
    # --------------------------------------------------------

    try:

        result = _extract_json(
            content
        )

    except Exception as exc:

        raise RuntimeError(
            f"Qwen JSON parsing failed: {exc}"
        ) from exc

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    try:

        result = _normalize_result(
            result,
            repository_evidence,
        )

    except Exception as exc:

        raise RuntimeError(
            f"Qwen RCA validation failed: {exc}"
        ) from exc

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    confidence_percent = (
        result["confidence"] * 100
    )

    print("  ✓ COMPLETED")
    print(
        f"  Root cause : {result['root_cause']}"
    )
    print(
        f"  Location   : "
        f"{result['file_path']}:"
        f"{result['line_start']}-"
        f"{result['line_end']}"
    )
    print(
        f"  Confidence : {confidence_percent:.1f}%"
    )
    print("=" * 72)
    print()

    return result