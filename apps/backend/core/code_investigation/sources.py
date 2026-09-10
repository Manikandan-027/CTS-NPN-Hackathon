from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse

from .models import SourceFile


DEFAULT_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".cs": "csharp",
    ".php": "php",
    ".rb": "ruby",
    ".kt": "kotlin",
    ".swift": "swift",
    ".sql": "sql",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".ini": "ini",
    ".env": "dotenv",
    ".xml": "xml",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
}

IGNORED_FILES = {
    "README.md",
    "README",
    "LICENSE",
    "CHANGELOG.md",
}

IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    "coverage",
    ".next",
    ".turbo",
}

MAX_FILE_SIZE_BYTES = 1_000_000


def _safe_read(path: Path) -> str | None:
    try:
        if path.stat().st_size > MAX_FILE_SIZE_BYTES:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeError):
        return None


def iter_source_files(root: Path) -> Iterator[SourceFile]:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"Repository path is not a directory: {root}")

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name in IGNORED_FILES:
            continue
        if any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
            continue

        language = DEFAULT_EXTENSIONS.get(path.suffix.lower())
        if language is None:
            continue

        content = _safe_read(path)
        if content is None:
            continue

        relative = path.relative_to(root).as_posix()
        yield SourceFile(
            path=relative,
            language=language,
            size_bytes=path.stat().st_size,
            line_count=content.count("\n") + (1 if content else 0),
            content=content,
        )


class LocalRepositorySource:
    """Read a repository from a local directory for deterministic testing."""

    source_type = "local"

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        if not self.root.is_dir():
            raise FileNotFoundError(f"Local repository does not exist: {self.root}")

    def files(self) -> list[SourceFile]:
        return list(iter_source_files(self.root))

    def describe(self) -> str:
        return str(self.root)


class GitHubRepositorySource:
    """Clone a public GitHub repository into a temporary directory and expose it as source files."""

    source_type = "github"

    _GITHUB_RE = re.compile(r"^https?://github\.com/([^/]+)/([^/#]+?)(?:\.git)?/?$", re.I)

    def __init__(self, url: str, timeout_seconds: int = 60) -> None:
        self.url = url.strip()
        self.timeout_seconds = timeout_seconds
        self._temp_dir: Path | None = None
        self._validate_url()

    def _validate_url(self) -> None:
        parsed = urlparse(self.url)
        if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != "github.com":
            raise ValueError("Only public GitHub repository URLs are supported.")
        if not self._GITHUB_RE.match(self.url):
            raise ValueError("Expected a repository URL such as https://github.com/owner/repository")

    def _clone(self) -> Path:
        if self._temp_dir is not None:
            return self._temp_dir

        temp_dir = Path(tempfile.mkdtemp(prefix="rca-github-"))
        command = ["git", "clone", "--depth", "1", self.url, str(temp_dir)]
        try:
            subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError as exc:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError("Git is required for GitHub repository scanning.") from exc
        except subprocess.CalledProcessError as exc:
            shutil.rmtree(temp_dir, ignore_errors=True)
            detail = (exc.stderr or "").strip()
            raise RuntimeError(f"Unable to clone GitHub repository: {detail}") from exc
        except subprocess.TimeoutExpired as exc:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise RuntimeError("GitHub repository clone timed out.") from exc

        self._temp_dir = temp_dir
        return temp_dir

    def files(self) -> list[SourceFile]:
        return list(iter_source_files(self._clone()))

    def describe(self) -> str:
        return self.url

    def cleanup(self) -> None:
        if self._temp_dir is not None:
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            self._temp_dir = None

    def __enter__(self) -> "GitHubRepositorySource":
        return self

    def __exit__(self, *_args: object) -> None:
        self.cleanup()
