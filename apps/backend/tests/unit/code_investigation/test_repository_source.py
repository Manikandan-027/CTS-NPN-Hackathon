from pathlib import Path

from backend.core.code_investigation import LocalRepositorySource


def test_local_source_discovers_supported_files():
    root = Path("apps/sample_code_project")
    source = LocalRepositorySource(root)
    files = source.files()

    paths = {item.path for item in files}
    assert "src/app.py" in paths
    assert "src/rate_limiter.py" in paths
    assert "src/config.py" in paths
