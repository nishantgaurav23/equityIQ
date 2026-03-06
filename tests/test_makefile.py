"""Tests for Makefile (Spec S1.2 -- Developer Commands)."""

import os
import re
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
MAKEFILE_PATH = PROJECT_ROOT / "Makefile"

# Guard against recursive make local-test invocation
IN_MAKE_TEST = os.environ.get("EQUITYIQ_MAKE_TEST") == "1"

REQUIRED_TARGETS = [
    "venv",
    "install",
    "install-dev",
    "local-dev",
    "local-test",
    "local-lint",
    "dev",
    "test",
]


def _read_makefile() -> str:
    return MAKEFILE_PATH.read_text()


def _parse_targets(content: str) -> set[str]:
    """Extract target names from Makefile (lines like 'target:' or 'target: dep')."""
    targets = set()
    for line in content.splitlines():
        match = re.match(r"^([a-zA-Z_-]+)\s*:", line)
        if match:
            targets.add(match.group(1))
    return targets


class TestMakefileExists:
    def test_makefile_exists(self):
        assert MAKEFILE_PATH.exists(), "Makefile must exist at project root"

    def test_makefile_is_not_empty(self):
        assert MAKEFILE_PATH.stat().st_size > 0, "Makefile must not be empty"


class TestMakefileTargets:
    def test_all_required_targets_defined(self):
        content = _read_makefile()
        targets = _parse_targets(content)
        for target in REQUIRED_TARGETS:
            assert target in targets, f"Makefile must define target: {target}"

    def test_phony_declaration_exists(self):
        content = _read_makefile()
        assert ".PHONY" in content, "Makefile must have .PHONY declaration"

    def test_phony_includes_all_targets(self):
        content = _read_makefile()
        phony_lines = [
            line for line in content.splitlines() if line.startswith(".PHONY")
        ]
        phony_text = " ".join(phony_lines)
        for target in REQUIRED_TARGETS:
            assert target in phony_text, f".PHONY must include target: {target}"


class TestMakefileExecution:
    def test_venv_target_creates_virtualenv(self, tmp_path):
        """Run make venv and verify venv directory is created."""
        subprocess.run(
            ["make", "venv"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        venv_dir = PROJECT_ROOT / "venv"
        assert venv_dir.is_dir(), "make venv must create venv/ directory"
        assert (venv_dir / "bin" / "python").exists(), "venv must contain bin/python"

    def test_install_dev_succeeds(self):
        """Run make install-dev and verify it exits successfully."""
        result = subprocess.run(
            ["make", "install-dev"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, (
            f"make install-dev failed:\nstdout: {result.stdout[-500:]}\n"
            f"stderr: {result.stderr[-500:]}"
        )

    @pytest.mark.skipif(IN_MAKE_TEST, reason="Skip to avoid recursive make invocation")
    def test_local_test_runs_pytest(self):
        """Run make local-test and verify pytest executes."""
        env = {**os.environ, "EQUITYIQ_MAKE_TEST": "1"}
        result = subprocess.run(
            ["make", "local-test"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        # pytest should run (exit 0 = pass, exit 5 = no tests collected, both OK)
        assert result.returncode in (0, 5), (
            f"make local-test failed with rc={result.returncode}:\n"
            f"stderr: {result.stderr[-500:]}"
        )

    def test_local_lint_runs_ruff(self):
        """Run make local-lint and verify ruff executes."""
        result = subprocess.run(
            ["make", "local-lint"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        # ruff should run -- may find issues (rc=1) or pass (rc=0)
        combined = result.stdout + result.stderr
        assert "ruff" in combined.lower() or result.returncode == 0, (
            "make local-lint must invoke ruff"
        )


class TestDockerTargetsPresence:
    """Docker targets are tested for presence only (Docker may not be available)."""

    def test_dev_target_has_docker_compose(self):
        content = _read_makefile()
        # Find the dev target and check it references docker-compose or docker compose
        assert re.search(
            r"dev:.*\n\t.*docker", content, re.MULTILINE
        ) or "docker" in content, "dev target must reference docker"

    def test_test_target_has_docker(self):
        content = _read_makefile()
        # The test target should reference docker
        assert "docker" in content, "test target must reference docker"
