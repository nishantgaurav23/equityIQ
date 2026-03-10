"""Tests for S12.5 -- Firestore Database Setup script."""

import os
import re
import stat
import subprocess

import pytest

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "deploy", "setup-firestore.sh")
FIRESTORE_VAULT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "memory", "firestore_vault.py"
)


@pytest.fixture
def script_content():
    """Read the setup-firestore.sh script content."""
    with open(SCRIPT_PATH) as f:
        return f.read()


@pytest.fixture
def firestore_vault_content():
    """Read the firestore_vault.py source content."""
    with open(FIRESTORE_VAULT_PATH) as f:
        return f.read()


class TestSetupFirestoreScriptExists:
    def test_script_exists(self):
        assert os.path.isfile(SCRIPT_PATH), "deploy/setup-firestore.sh must exist"

    def test_script_is_executable(self):
        mode = os.stat(SCRIPT_PATH).st_mode
        assert mode & stat.S_IXUSR, "deploy/setup-firestore.sh must be executable"

    def test_script_has_bash_shebang(self, script_content):
        assert script_content.startswith("#!/"), "Script must start with a shebang"
        first_line = script_content.split("\n")[0]
        assert "bash" in first_line, "Script must use bash"


class TestSetupFirestoreShellcheck:
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


class TestSetupFirestoreProjectIdRequired:
    def test_project_id_validation(self, script_content):
        assert "GCP_PROJECT_ID" in script_content, "Script must reference GCP_PROJECT_ID"
        assert re.search(
            r'(if.*GCP_PROJECT_ID|-z.*GCP_PROJECT_ID|PROJECT_ID)', script_content
        ), "Script must validate GCP_PROJECT_ID is set"


class TestSetupFirestoreGcloudCheck:
    def test_checks_gcloud_availability(self, script_content):
        assert re.search(
            r"(command -v gcloud|which gcloud|gcloud version)", script_content
        ), "Script must check gcloud CLI is available"


class TestSetupFirestoreNativeMode:
    def test_native_mode_database_creation(self, script_content):
        assert re.search(
            r"(FIRESTORE_NATIVE|firestore.*native|--type=FIRESTORE_NATIVE)", script_content
        ), "Script must create Firestore database in Native mode"

    def test_firestore_database_create_command(self, script_content):
        assert re.search(
            r"firestore databases create", script_content
        ), "Script must use 'firestore databases create' command"


class TestSetupFirestoreCollectionName:
    def test_verdicts_collection_referenced(self, script_content):
        assert "verdicts" in script_content, (
            "Script must reference 'verdicts' collection"
        )

    def test_collection_matches_firestore_vault(self, script_content, firestore_vault_content):
        # Extract collection name from firestore_vault.py
        match = re.search(r'_COLLECTION\s*=\s*["\'](\w+)["\']', firestore_vault_content)
        assert match, "firestore_vault.py must define _COLLECTION"
        vault_collection = match.group(1)
        assert vault_collection in script_content, (
            f"Collection '{vault_collection}' from firestore_vault.py must be in script"
        )


class TestSetupFirestoreCompositeIndex:
    def test_composite_index_on_ticker(self, script_content):
        assert "ticker" in script_content, (
            "Script must reference 'ticker' field for composite index"
        )

    def test_composite_index_on_created_at(self, script_content):
        assert "created_at" in script_content, (
            "Script must reference 'created_at' field for composite index"
        )

    def test_index_creation_command(self, script_content):
        assert re.search(
            r"firestore indexes composite create|indexes.*create", script_content
        ), "Script must create composite indexes"


class TestSetupFirestoreApiEnablement:
    def test_enables_firestore_api(self, script_content):
        assert "firestore.googleapis.com" in script_content, (
            "Script must enable firestore.googleapis.com API"
        )

    def test_services_enable_command(self, script_content):
        assert re.search(
            r"gcloud services enable.*firestore", script_content
        ), "Script must use 'gcloud services enable' for Firestore API"


class TestSetupFirestoreIamBinding:
    def test_datastore_user_role(self, script_content):
        assert "datastore.user" in script_content, (
            "Script must grant roles/datastore.user role"
        )

    def test_service_account_reference(self, script_content):
        pattern = r"(service-account|compute@developer|iam\.gserviceaccount)"
        assert re.search(pattern, script_content), (
            "Script must reference the Cloud Run service account"
        )


class TestSetupFirestoreIdempotent:
    def test_checks_existing_database(self, script_content):
        assert re.search(
            r"(databases describe|databases list|already exists)", script_content, re.IGNORECASE
        ), "Script must check for existing database before creating"

    def test_skip_existing_pattern(self, script_content):
        assert re.search(
            r"(already exists|skipping|exists|SKIP)", script_content, re.IGNORECASE
        ), "Script must handle already-existing resources gracefully"


class TestSetupFirestoreHelpFlag:
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
        assert "--region" in output, "--help must list --region option"
        assert "--project" in output, "--help must list --project option"


class TestSetupFirestoreRegionDefault:
    def test_default_region_us_central1(self, script_content):
        assert "us-central1" in script_content, (
            "Script must use us-central1 as default region"
        )

    def test_region_flag_supported(self, script_content):
        assert "--region" in script_content, "Script must support --region flag"
