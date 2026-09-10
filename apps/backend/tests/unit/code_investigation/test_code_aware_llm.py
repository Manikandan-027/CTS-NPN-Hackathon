from unittest.mock import MagicMock, patch

from backend.core.code_investigation import LocalRepositorySource, RepositoryInvestigator
from backend.core.llm.code_aware_rca import generate_code_aware_rca


def test_code_aware_llm_rejects_location_not_found():
    evidence = RepositoryInvestigator(
        LocalRepositorySource("apps/sample_code_project")
    ).investigate("HTTP 429 Too Many Requests")

    fake_response = MagicMock()
    fake_response.choices[0].message.content = (
        '{"root_cause":"x","file_path":"src/not_real.py",'
        '"line_start":1,"line_end":1,"evidence":["x"],'
        '"suggested_fix":"x","prevention":"x","confidence":0.9,"summary":"x"}'
    )

    with patch("backend.core.llm.code_aware_rca.create_groq_client") as factory:
        factory.return_value.chat.completions.create.return_value = fake_response
        try:
            generate_code_aware_rca("HTTP 429", [], evidence.to_dict())
        except ValueError as exc:
            assert "code location" in str(exc)
        else:
            raise AssertionError("Expected invalid code location to be rejected")
