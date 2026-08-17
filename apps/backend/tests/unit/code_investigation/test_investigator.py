from backend.core.code_investigation import LocalRepositorySource, RepositoryInvestigator


def test_rate_limit_incident_finds_intentional_defect():
    investigator = RepositoryInvestigator(
        LocalRepositorySource("apps/sample_code_project")
    )

    result = investigator.investigate(
        "GET /products returns HTTP 429 Too Many Requests immediately for a new user"
    )

    assert result.scanned_files == 3
    assert "src/rate_limiter.py" in result.relevant_files
    assert result.findings

    top = result.findings[0]
    assert top.file_path == "src/rate_limiter.py"
    assert top.line_start == 7
    assert "suspicious-limit-value" in top.matched_terms
    assert "2" in top.context


def test_empty_error_is_rejected():
    investigator = RepositoryInvestigator(
        LocalRepositorySource("apps/sample_code_project")
    )

    try:
        investigator.investigate("")
    except ValueError as exc:
        assert "error cannot be empty" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
