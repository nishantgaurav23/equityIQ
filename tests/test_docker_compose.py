"""Tests for docker-compose.yml structure and configuration (S11.2)."""

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"


@pytest.fixture(scope="module")
def compose_data():
    """Parse docker-compose.yml and return as dict."""
    assert COMPOSE_FILE.exists(), "docker-compose.yml not found at repo root"
    with open(COMPOSE_FILE) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def app_service(compose_data):
    """Return the 'app' service config."""
    assert "services" in compose_data, "No 'services' key in docker-compose.yml"
    assert "app" in compose_data["services"], "No 'app' service defined"
    return compose_data["services"]["app"]


class TestComposeSpec:
    """Verify modern Compose Specification compliance."""

    def test_no_deprecated_version_key(self, compose_data):
        """Modern Compose spec should not have a 'version' key."""
        assert "version" not in compose_data, (
            "Remove deprecated 'version:' key -- use modern Compose Specification"
        )


class TestAppService:
    """Verify the 'app' service configuration."""

    def test_service_exists(self, compose_data):
        """Service 'app' must be defined."""
        assert "app" in compose_data["services"]

    def test_build_context(self, app_service):
        """Build context should be repo root (.)."""
        build = app_service.get("build", {})
        if isinstance(build, str):
            assert build == "."
        else:
            assert build.get("context") == "."

    def test_build_target_dev(self, app_service):
        """Build target should be 'dev' stage from Dockerfile."""
        build = app_service.get("build", {})
        assert isinstance(build, dict), "build must be a mapping with target"
        assert build.get("target") == "dev"

    def test_container_name(self, app_service):
        """Container name should be equityiq-dev."""
        assert app_service.get("container_name") == "equityiq-dev"


class TestPortMapping:
    """Verify port configuration."""

    def test_port_mapping_8000_to_8080(self, app_service):
        """Host 8000 -> container 8080."""
        ports = app_service.get("ports", [])
        port_strings = [str(p) for p in ports]
        assert any("8000:8080" in p for p in port_strings), (
            f"Expected port mapping '8000:8080', got {port_strings}"
        )


class TestEnvironment:
    """Verify environment configuration."""

    def test_env_file_includes_dotenv(self, app_service):
        """env_file should include .env."""
        env_file = app_service.get("env_file", [])
        if isinstance(env_file, str):
            env_file = [env_file]
        assert ".env" in env_file, f"Expected '.env' in env_file, got {env_file}"

    def test_environment_development(self, app_service):
        """ENVIRONMENT should default to 'development'."""
        env = app_service.get("environment", {})
        if isinstance(env, list):
            assert any("ENVIRONMENT=development" in e for e in env), (
                f"Expected ENVIRONMENT=development in {env}"
            )
        else:
            assert env.get("ENVIRONMENT") == "development"

    def test_port_env_var(self, app_service):
        """PORT env var should be 8080."""
        env = app_service.get("environment", {})
        if isinstance(env, list):
            assert any("PORT=8080" in e for e in env), f"Expected PORT=8080 in {env}"
        else:
            assert str(env.get("PORT")) == "8080"


class TestVolumes:
    """Verify volume mount for hot reload."""

    def test_source_volume_mount(self, app_service):
        """Current directory should be mounted to /app."""
        volumes = app_service.get("volumes", [])
        vol_strings = [str(v) for v in volumes]
        assert any(".:/app" in v for v in vol_strings), (
            f"Expected volume '.:/app', got {vol_strings}"
        )


class TestCommand:
    """Verify development command override."""

    def test_command_uses_uvicorn(self, app_service):
        """Command should use uvicorn."""
        command = app_service.get("command", "")
        if isinstance(command, list):
            command = " ".join(command)
        assert "uvicorn" in command, f"Expected 'uvicorn' in command, got {command}"

    def test_command_has_reload(self, app_service):
        """Command should include --reload for hot reload."""
        command = app_service.get("command", "")
        if isinstance(command, list):
            command = " ".join(command)
        assert "--reload" in command, f"Expected '--reload' in command, got {command}"


class TestRestartPolicy:
    """Verify restart configuration."""

    def test_restart_unless_stopped(self, app_service):
        """Restart policy should be 'unless-stopped'."""
        assert app_service.get("restart") == "unless-stopped"
