"""Tests for S11.4 -- .dockerignore file."""

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
DOCKERIGNORE_PATH = PROJECT_ROOT / ".dockerignore"


@pytest.fixture
def dockerignore_content() -> str:
    """Read .dockerignore content."""
    assert DOCKERIGNORE_PATH.exists(), ".dockerignore file must exist at project root"
    return DOCKERIGNORE_PATH.read_text()


@pytest.fixture
def dockerignore_lines(dockerignore_content: str) -> list[str]:
    """Parse .dockerignore into non-empty, non-comment lines."""
    return [
        line.strip()
        for line in dockerignore_content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


class TestDockerignoreExists:
    """Test that .dockerignore file exists."""

    def test_file_exists(self):
        assert DOCKERIGNORE_PATH.exists(), ".dockerignore must exist at project root"

    def test_file_is_not_empty(self, dockerignore_content: str):
        assert len(dockerignore_content.strip()) > 0, ".dockerignore must not be empty"


class TestDevVenvExclusions:
    """R1: Exclude development and virtual environment files."""

    @pytest.mark.parametrize(
        "pattern",
        [
            "venv/",
            ".venv/",
            "__pycache__/",
            "*.pyc",
            "*.pyo",
            ".pytest_cache/",
            ".ruff_cache/",
            "*.egg-info",
            ".mypy_cache/",
        ],
    )
    def test_dev_exclusion_present(self, dockerignore_lines: list[str], pattern: str):
        assert pattern in dockerignore_lines, f"Missing dev exclusion: {pattern}"


class TestSecretsExclusions:
    """R2: Exclude secrets and environment files."""

    @pytest.mark.parametrize(
        "pattern",
        [
            ".env",
            ".env.*",
        ],
    )
    def test_secrets_exclusion_present(self, dockerignore_lines: list[str], pattern: str):
        assert pattern in dockerignore_lines, f"Missing secrets exclusion: {pattern}"

    def test_env_file_excluded(self, dockerignore_lines: list[str]):
        """Security-critical: .env MUST be excluded."""
        assert ".env" in dockerignore_lines, ".env MUST be excluded (contains API keys)"


class TestVcsIdeExclusions:
    """R3: Exclude version control and IDE files."""

    @pytest.mark.parametrize(
        "pattern",
        [
            ".git/",
            ".gitignore",
            ".vscode/",
            ".idea/",
            ".claude/",
        ],
    )
    def test_vcs_ide_exclusion_present(self, dockerignore_lines: list[str], pattern: str):
        assert pattern in dockerignore_lines, f"Missing VCS/IDE exclusion: {pattern}"


class TestDocsExclusions:
    """R4: Exclude documentation and non-runtime files."""

    @pytest.mark.parametrize(
        "pattern",
        [
            "docs/",
            "notebooks/",
            "specs/",
            "*.md",
        ],
    )
    def test_docs_exclusion_present(self, dockerignore_lines: list[str], pattern: str):
        assert pattern in dockerignore_lines, f"Missing docs exclusion: {pattern}"


class TestTestExclusions:
    """R5: Exclude test and evaluation files."""

    @pytest.mark.parametrize(
        "pattern",
        [
            "tests/",
            "evaluation/",
        ],
    )
    def test_test_exclusion_present(self, dockerignore_lines: list[str], pattern: str):
        assert pattern in dockerignore_lines, f"Missing test exclusion: {pattern}"


class TestDataFrontendExclusions:
    """R6: Exclude data and frontend files."""

    @pytest.mark.parametrize(
        "pattern",
        [
            "data/*.db",
            "frontend/node_modules/",
        ],
    )
    def test_data_frontend_exclusion_present(self, dockerignore_lines: list[str], pattern: str):
        assert pattern in dockerignore_lines, f"Missing data/frontend exclusion: {pattern}"


class TestDockerCiExclusions:
    """R7: Exclude Docker and CI/CD files."""

    @pytest.mark.parametrize(
        "pattern",
        [
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose*.yml",
            ".dockerignore",
            ".github/",
        ],
    )
    def test_docker_ci_exclusion_present(self, dockerignore_lines: list[str], pattern: str):
        assert pattern in dockerignore_lines, f"Missing Docker/CI exclusion: {pattern}"
