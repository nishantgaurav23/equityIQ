"""Tests for S11.3 -- Agent Launch/Stop Scripts."""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAUNCH_SCRIPT = ROOT / "scripts" / "launch_agents.sh"
STOP_SCRIPT = ROOT / "scripts" / "stop_agents.sh"


class TestLaunchScriptExists:
    """Test that launch script exists and is executable."""

    def test_launch_script_exists(self):
        assert LAUNCH_SCRIPT.exists(), "scripts/launch_agents.sh must exist"

    def test_launch_script_is_executable(self):
        assert os.access(LAUNCH_SCRIPT, os.X_OK), "launch_agents.sh must be executable"


class TestStopScriptExists:
    """Test that stop script exists and is executable."""

    def test_stop_script_exists(self):
        assert STOP_SCRIPT.exists(), "scripts/stop_agents.sh must exist"

    def test_stop_script_is_executable(self):
        assert os.access(STOP_SCRIPT, os.X_OK), "stop_agents.sh must be executable"


class TestLaunchScriptContent:
    """Test launch script content and structure."""

    def test_launch_script_has_shebang(self):
        content = LAUNCH_SCRIPT.read_text()
        assert content.startswith("#!/usr/bin/env bash"), "Must have bash shebang"

    def test_launch_script_has_set_flags(self):
        content = LAUNCH_SCRIPT.read_text()
        assert "set -euo pipefail" in content, "Must use set -euo pipefail"

    def test_launch_script_defines_all_agents(self):
        content = LAUNCH_SCRIPT.read_text()
        expected_ports = ["8000", "8001", "8002", "8003", "8004", "8005", "8006", "8007"]
        for port in expected_ports:
            assert port in content, f"Must define port {port}"

    def test_launch_script_creates_pid_dir(self):
        content = LAUNCH_SCRIPT.read_text()
        assert ".pids" in content, "Must reference .pids/ directory"
        assert "mkdir" in content, "Must create .pids/ directory"

    def test_launch_script_has_health_check(self):
        content = LAUNCH_SCRIPT.read_text()
        assert "curl" in content, "Must have curl health check"
        assert "/health" in content or "health" in content.lower(), "Must check health endpoint"

    def test_launch_script_has_no_health_check_flag(self):
        content = LAUNCH_SCRIPT.read_text()
        assert "--no-health-check" in content, "Must support --no-health-check flag"


class TestStopScriptContent:
    """Test stop script content and structure."""

    def test_stop_script_has_shebang(self):
        content = STOP_SCRIPT.read_text()
        assert content.startswith("#!/usr/bin/env bash"), "Must have bash shebang"

    def test_stop_script_has_set_flags(self):
        content = STOP_SCRIPT.read_text()
        assert "set -euo pipefail" in content, "Must use set -euo pipefail"

    def test_stop_script_handles_missing_pids_dir(self):
        content = STOP_SCRIPT.read_text()
        assert ".pids" in content, "Must reference .pids/ directory"
        # Should check if directory exists before trying to read it
        assert "! -d" in content or "-d" in content, "Must check if .pids/ exists"

    def test_stop_script_sends_sigterm(self):
        content = STOP_SCRIPT.read_text()
        assert "SIGTERM" in content or "kill " in content or "kill -15" in content, (
            "Must send SIGTERM to processes"
        )

    def test_stop_script_has_force_flag(self):
        content = STOP_SCRIPT.read_text()
        assert "--force" in content, "Must support --force flag"


class TestScriptHelpFlags:
    """Test that both scripts support -h/--help."""

    def test_launch_script_help_flag(self):
        result = subprocess.run(
            [str(LAUNCH_SCRIPT), "-h"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0, "Help flag should exit 0"
        assert "usage" in result.stdout.lower() or "help" in result.stdout.lower(), (
            "Should show usage info"
        )

    def test_stop_script_help_flag(self):
        result = subprocess.run(
            [str(STOP_SCRIPT), "-h"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0, "Help flag should exit 0"
        assert "usage" in result.stdout.lower() or "help" in result.stdout.lower(), (
            "Should show usage info"
        )
