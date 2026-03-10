"""Tests for scripts/health_check.sh -- S11.5 Health Check Script."""

import os
import stat
import subprocess

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT_PATH = os.path.join(PROJECT_ROOT, "scripts", "health_check.sh")


class TestHealthCheckScriptExists:
    """Test that the health check script exists and has correct permissions."""

    def test_health_check_script_exists(self):
        """scripts/health_check.sh must exist."""
        assert os.path.isfile(SCRIPT_PATH), f"Missing: {SCRIPT_PATH}"

    def test_health_check_script_is_executable(self):
        """scripts/health_check.sh must be executable."""
        mode = os.stat(SCRIPT_PATH).st_mode
        assert mode & stat.S_IXUSR, "Script is not executable by owner"


class TestHealthCheckScriptStructure:
    """Test script structure: shebang, set flags, agent definitions."""

    @pytest.fixture(autouse=True)
    def _read_script(self):
        with open(SCRIPT_PATH) as f:
            self.content = f.read()
            self.lines = self.content.splitlines()

    def test_health_check_script_has_shebang(self):
        """First line must be #!/usr/bin/env bash."""
        assert self.lines[0] == "#!/usr/bin/env bash"

    def test_health_check_script_has_set_flags(self):
        """Script must contain set -euo pipefail."""
        assert "set -euo pipefail" in self.content

    def test_health_check_script_defines_all_agents(self):
        """Script must define all 8 agents on ports 8000-8007."""
        for port in range(8000, 8008):
            assert str(port) in self.content, f"Port {port} not found in script"

    def test_health_check_script_has_curl_health(self):
        """Script must use curl to check /health endpoints."""
        assert "curl" in self.content
        assert "/health" in self.content

    def test_health_check_script_has_color_codes(self):
        """Script must define GREEN and RED color codes."""
        assert "GREEN=" in self.content
        assert "RED=" in self.content


class TestHealthCheckScriptFlags:
    """Test that required flags are handled in the script."""

    @pytest.fixture(autouse=True)
    def _read_script(self):
        with open(SCRIPT_PATH) as f:
            self.content = f.read()

    def test_health_check_script_has_timeout_flag(self):
        """Script must support --timeout flag."""
        assert "--timeout" in self.content

    def test_health_check_script_has_port_flag(self):
        """Script must support --port flag."""
        assert "--port" in self.content

    def test_health_check_script_has_json_flag(self):
        """Script must support --json flag."""
        assert "--json" in self.content

    def test_health_check_script_has_summary_line(self):
        """Script must output a summary line (X/N agents healthy)."""
        assert "agents healthy" in self.content.lower() or "healthy" in self.content.lower()

    def test_health_check_script_exit_code_logic(self):
        """Script must exit 1 when agents are down."""
        assert "exit 1" in self.content


class TestHealthCheckScriptHelp:
    """Test the -h / --help flag behavior."""

    def test_health_check_script_help_flag(self):
        """Running with -h should exit 0 and show usage."""
        result = subprocess.run(
            [SCRIPT_PATH, "-h"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "Usage" in result.stdout
