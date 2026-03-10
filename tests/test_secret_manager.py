"""Tests for S12.4 -- GCP Secret Manager setup script."""

import os
import re
import stat
import subprocess

import pytest
import yaml

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "deploy", "setup-secrets.sh")
CLOUDRUN_PATH = os.path.join(os.path.dirname(__file__), "..", "deploy", "cloudrun.yaml")

REQUIRED_SECRETS = [
    "GOOGLE_API_KEY",
    "POLYGON_API_KEY",
    "FRED_API_KEY",
    "NEWS_API_KEY",
    "SERPER_API_KEY",
    "TAVILY_API_KEY",
]


@pytest.fixture
def script_content():
    """Read the setup-secrets.sh script content."""
    with open(SCRIPT_PATH) as f:
        return f.read()


class TestSetupSecretsScriptExists:
    def test_script_exists(self):
        assert os.path.isfile(SCRIPT_PATH), "deploy/setup-secrets.sh must exist"

    def test_script_is_executable(self):
        mode = os.stat(SCRIPT_PATH).st_mode
        assert mode & stat.S_IXUSR, "deploy/setup-secrets.sh must be executable"

    def test_script_has_bash_shebang(self, script_content):
        assert script_content.startswith("#!/"), "Script must start with a shebang"
        first_line = script_content.split("\n")[0]
        assert "bash" in first_line, "Script must use bash"


class TestSetupSecretsShellcheck:
    def test_shellcheck_passes(self):
        try:
            result = subprocess.run(
                ["shellcheck", SCRIPT_PATH],
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            pytest.skip("shellcheck not installed")
        if result.returncode == 127:
            pytest.skip("shellcheck not installed")
        assert result.returncode == 0, f"shellcheck errors:\n{result.stdout}\n{result.stderr}"


class TestSetupSecretsRequiredSecrets:
    def test_all_required_secrets_in_script(self, script_content):
        for secret in REQUIRED_SECRETS:
            assert secret in script_content, f"Secret {secret} must be referenced in script"

    def test_secrets_defined_as_array_or_list(self, script_content):
        # Script should define secrets in a list/array for maintainability
        assert "SECRETS=" in script_content or "SECRETS=(" in script_content, (
            "Script should define a SECRETS array"
        )


class TestSetupSecretsIdempotentCheck:
    def test_checks_existing_secrets(self, script_content):
        # Script should check if secret exists before creating
        assert "secrets describe" in script_content or "secrets list" in script_content, (
            "Script must check for existing secrets before creating"
        )

    def test_skip_existing_pattern(self, script_content):
        # Should have logic to skip already-existing secrets
        assert re.search(r"(already exists|skipping|exists)", script_content, re.IGNORECASE), (
            "Script must handle already-existing secrets gracefully"
        )


class TestSetupSecretsProjectIdRequired:
    def test_project_id_validation(self, script_content):
        # Script must validate GCP_PROJECT_ID is set
        assert "GCP_PROJECT_ID" in script_content, (
            "Script must reference GCP_PROJECT_ID"
        )
        assert re.search(r'(if.*GCP_PROJECT_ID|-z.*GCP_PROJECT_ID|PROJECT_ID)', script_content), (
            "Script must validate GCP_PROJECT_ID is set"
        )


class TestSetupSecretsGcloudCheck:
    def test_checks_gcloud_availability(self, script_content):
        assert re.search(r"(command -v gcloud|which gcloud|gcloud version)", script_content), (
            "Script must check gcloud CLI is available"
        )


class TestSetupSecretsFromEnvFlag:
    def test_from_env_flag_supported(self, script_content):
        assert "--from-env" in script_content, "Script must support --from-env flag"

    def test_help_mentions_from_env(self):
        result = subprocess.run(
            ["bash", SCRIPT_PATH, "--help"],
            capture_output=True,
            text=True,
        )
        assert "--from-env" in result.stdout or "--from-env" in result.stderr, (
            "--help output must mention --from-env"
        )


class TestSetupSecretsIamBinding:
    def test_iam_binding_command(self, script_content):
        assert "secretmanager.secretAccessor" in script_content, (
            "Script must grant secretmanager.secretAccessor role"
        )

    def test_service_account_reference(self, script_content):
        pattern = r"(service-account|compute@developer|iam\.gserviceaccount)"
        assert re.search(pattern, script_content), (
            "Script must reference the Cloud Run service account"
        )


class TestSecretsMatchCloudrunYaml:
    def test_secret_names_match(self, script_content):
        with open(CLOUDRUN_PATH) as f:
            cloudrun = yaml.safe_load(f.read().replace("PROJECT_ID", "test-project"))

        # Extract secret names from cloudrun.yaml
        containers = cloudrun["spec"]["template"]["spec"]["containers"]
        cloudrun_secrets = set()
        for container in containers:
            for env_entry in container.get("env", []):
                value_from = env_entry.get("valueFrom", {})
                secret_ref = value_from.get("secretKeyRef", {})
                if "name" in secret_ref:
                    cloudrun_secrets.add(secret_ref["name"])

        # Verify every cloudrun secret is in the script
        for secret in cloudrun_secrets:
            assert secret in script_content, (
                f"Secret {secret} from cloudrun.yaml must be in setup-secrets.sh"
            )


class TestSetupSecretsHelpFlag:
    def test_help_flag_exits_zero(self):
        result = subprocess.run(
            ["bash", SCRIPT_PATH, "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"--help should exit 0, got {result.returncode}"

    def test_help_shows_usage(self):
        result = subprocess.run(
            ["bash", SCRIPT_PATH, "--help"],
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr
        assert re.search(r"(usage|Usage|USAGE)", output), "--help must show usage info"

    def test_help_lists_options(self):
        result = subprocess.run(
            ["bash", SCRIPT_PATH, "--help"],
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr
        assert "--from-env" in output, "--help must list --from-env option"
        assert "--service-account" in output or "service account" in output.lower(), (
            "--help must mention service account option"
        )
