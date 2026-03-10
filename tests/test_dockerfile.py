"""Tests for S11.1 -- Multi-stage Dockerfile structure validation."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = ROOT / "Dockerfile"


@pytest.fixture
def dockerfile_content():
    """Read and return the Dockerfile content."""
    assert DOCKERFILE.exists(), "Dockerfile must exist at project root"
    return DOCKERFILE.read_text()


@pytest.fixture
def dockerfile_lines(dockerfile_content):
    """Return Dockerfile lines (stripped, non-empty, non-comment)."""
    return [
        line
        for line in dockerfile_content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


# --- Stage existence ---


class TestStages:
    """Verify all 3 build stages exist."""

    def test_has_base_stage(self, dockerfile_content):
        assert re.search(
            r"FROM\s+python:3\.12-slim\s+AS\s+base", dockerfile_content, re.IGNORECASE
        ), "Must have base stage FROM python:3.12-slim AS base"

    def test_has_dev_stage(self, dockerfile_content):
        assert re.search(
            r"FROM\s+base\s+AS\s+dev", dockerfile_content, re.IGNORECASE
        ), "Must have dev stage FROM base AS dev"

    def test_has_prod_stage(self, dockerfile_content):
        assert re.search(
            r"FROM\s+base\s+AS\s+prod", dockerfile_content, re.IGNORECASE
        ), "Must have prod stage FROM base AS prod"

    def test_exactly_three_from_instructions(self, dockerfile_content):
        froms = re.findall(r"^FROM\s+", dockerfile_content, re.MULTILINE)
        assert len(froms) == 3, f"Expected 3 FROM instructions, got {len(froms)}"


# --- Base stage ---


class TestBaseStage:
    """Verify base stage configuration."""

    def test_python_312_slim(self, dockerfile_content):
        assert "python:3.12-slim" in dockerfile_content

    def test_pythondontwritebytecode(self, dockerfile_content):
        assert "PYTHONDONTWRITEBYTECODE=1" in dockerfile_content

    def test_pythonunbuffered(self, dockerfile_content):
        assert "PYTHONUNBUFFERED=1" in dockerfile_content

    def test_workdir_app(self, dockerfile_content):
        assert re.search(
            r"WORKDIR\s+/app", dockerfile_content
        ), "Must set WORKDIR /app"

    def test_copies_pyproject_toml(self, dockerfile_content):
        assert re.search(
            r"COPY\s+.*pyproject\.toml", dockerfile_content
        ), "Must COPY pyproject.toml"

    def test_no_requirements_txt_copy(self, dockerfile_content):
        assert not re.search(
            r"COPY\s+.*requirements\.txt", dockerfile_content
        ), "Must NOT copy requirements.txt -- deps come from pyproject.toml"

    def test_pip_no_cache_dir(self, dockerfile_content):
        pip_installs = re.findall(r"pip install.*", dockerfile_content)
        assert len(pip_installs) >= 1, "Must have at least one pip install"
        for cmd in pip_installs:
            assert "--no-cache-dir" in cmd, f"pip install must use --no-cache-dir: {cmd}"


# --- Dev stage ---


class TestDevStage:
    """Verify dev stage configuration."""

    def test_dev_installs_dev_deps(self, dockerfile_content):
        # After the dev FROM, should install .[dev]
        dev_section = self._get_stage_content(dockerfile_content, "dev")
        assert re.search(
            r'pip install.*\.\[dev\]', dev_section
        ), "Dev stage must install .[dev] dependencies"

    def test_dev_default_cmd_runs_pytest(self, dockerfile_content):
        dev_section = self._get_stage_content(dockerfile_content, "dev")
        assert re.search(
            r"CMD.*pytest", dev_section
        ), "Dev stage CMD must run pytest"

    @staticmethod
    def _get_stage_content(content, stage_name):
        """Extract content between a stage's FROM and the next FROM (or EOF)."""
        pattern = rf"(FROM\s+\S+\s+AS\s+{stage_name}.*?)(?=FROM\s+|$)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        return match.group(1) if match else ""


# --- Prod stage ---


class TestProdStage:
    """Verify prod stage configuration."""

    def test_creates_nonroot_user(self, dockerfile_content):
        prod_section = self._get_stage_content(dockerfile_content, "prod")
        assert re.search(
            r"(useradd|adduser).*appuser", prod_section
        ), "Prod stage must create appuser"

    def test_switches_to_nonroot_user(self, dockerfile_content):
        prod_section = self._get_stage_content(dockerfile_content, "prod")
        assert re.search(
            r"USER\s+appuser", prod_section
        ), "Prod stage must switch to appuser"

    def test_exposes_port_8080(self, dockerfile_content):
        prod_section = self._get_stage_content(dockerfile_content, "prod")
        assert re.search(
            r"EXPOSE\s+8080", prod_section
        ), "Prod stage must EXPOSE 8080"

    def test_healthcheck_exists(self, dockerfile_content):
        prod_section = self._get_stage_content(dockerfile_content, "prod")
        assert "HEALTHCHECK" in prod_section, "Prod stage must have HEALTHCHECK"

    def test_healthcheck_pings_health_endpoint(self, dockerfile_content):
        prod_section = self._get_stage_content(dockerfile_content, "prod")
        assert re.search(
            r"HEALTHCHECK.*(/health|localhost.*8080)", prod_section, re.DOTALL
        ), "HEALTHCHECK must ping /health endpoint"

    def test_cmd_uses_uvicorn(self, dockerfile_content):
        prod_section = self._get_stage_content(dockerfile_content, "prod")
        assert re.search(
            r"CMD.*uvicorn.*app:app", prod_section
        ), "Prod CMD must run uvicorn app:app"

    def test_cmd_binds_to_all_interfaces(self, dockerfile_content):
        prod_section = self._get_stage_content(dockerfile_content, "prod")
        assert re.search(
            r"CMD.*0\.0\.0\.0", prod_section
        ), "Prod CMD must bind to 0.0.0.0"

    def test_cmd_uses_port_8080(self, dockerfile_content):
        prod_section = self._get_stage_content(dockerfile_content, "prod")
        assert re.search(
            r"CMD.*8080", prod_section
        ), "Prod CMD must use port 8080"

    def test_user_directive_before_cmd(self, dockerfile_content):
        prod_section = self._get_stage_content(dockerfile_content, "prod")
        user_match = re.search(r"^USER\s+appuser", prod_section, re.MULTILINE)
        cmd_match = re.search(r"^CMD\s+", prod_section, re.MULTILINE)
        assert user_match and cmd_match, "Must have both USER and CMD"
        assert user_match.start() < cmd_match.start(), "USER appuser must come before CMD"

    @staticmethod
    def _get_stage_content(content, stage_name):
        """Extract content between a stage's FROM and the next FROM (or EOF)."""
        pattern = rf"(FROM\s+\S+\s+AS\s+{stage_name}.*?)(?=FROM\s+|$)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        return match.group(1) if match else ""


# --- Port environment variable ---


class TestEnvironment:
    """Verify environment variable setup."""

    def test_port_env_var(self, dockerfile_content):
        assert re.search(
            r"ENV\s+PORT\s*=?\s*8080", dockerfile_content
        ) or re.search(
            r"EXPOSE\s+8080", dockerfile_content
        ), "Must set PORT=8080 or EXPOSE 8080"
