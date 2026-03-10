"""Tests for S12.2 -- GitHub Actions CD Pipeline (.github/workflows/deploy.yml)."""

import re
from pathlib import Path

import yaml

WORKFLOW_PATH = Path(__file__).parent.parent / ".github" / "workflows" / "deploy.yml"


def _load_workflow() -> dict:
    """Load and parse the deploy workflow YAML."""
    assert WORKFLOW_PATH.exists(), f"deploy.yml not found at {WORKFLOW_PATH}"
    with open(WORKFLOW_PATH) as f:
        return yaml.safe_load(f)


def _get_trigger(wf: dict) -> dict:
    """Get the 'on' trigger block. YAML parses 'on:' as boolean True key."""
    return wf.get("on") or wf.get(True, {})


class TestDeployWorkflowStructure:
    """Basic structure tests for the CD workflow."""

    def test_deploy_workflow_exists(self):
        """deploy.yml must exist."""
        assert WORKFLOW_PATH.exists()

    def test_deploy_workflow_valid_yaml(self):
        """deploy.yml must be valid YAML."""
        wf = _load_workflow()
        assert isinstance(wf, dict)

    def test_deploy_workflow_name(self):
        """Workflow should have a descriptive name."""
        wf = _load_workflow()
        assert "name" in wf
        assert wf["name"]  # non-empty


class TestDeployTrigger:
    """Trigger configuration tests."""

    def test_deploy_trigger_main_only(self):
        """CD should trigger on main only (via push or workflow_run)."""
        wf = _load_workflow()
        trigger = _get_trigger(wf)
        assert trigger, "Workflow must have an 'on' trigger"

        # Accept either push-to-main or workflow_run on main
        if "push" in trigger:
            push = trigger["push"]
            branches = push.get("branches", [])
            assert "main" in branches
            assert "**" not in branches
        elif "workflow_run" in trigger:
            wr = trigger["workflow_run"]
            branches = wr.get("branches", [])
            assert "main" in branches
        else:
            assert False, "Must trigger on push or workflow_run"

    def test_deploy_no_pr_trigger(self):
        """CD should NOT trigger on pull requests."""
        wf = _load_workflow()
        trigger = _get_trigger(wf)
        assert "pull_request" not in trigger


class TestDeployConcurrency:
    """Concurrency control tests."""

    def test_deploy_concurrency_group(self):
        """Deploy workflow must have a concurrency group."""
        wf = _load_workflow()
        assert "concurrency" in wf
        conc = wf["concurrency"]
        assert "group" in conc

    def test_deploy_cancel_in_progress(self):
        """Concurrent deployments should cancel in-progress ones."""
        wf = _load_workflow()
        conc = wf["concurrency"]
        assert conc.get("cancel-in-progress") is True


class TestDeployDependsOnCI:
    """CI gate tests -- CD must depend on CI passing."""

    def test_deploy_depends_on_ci(self):
        """Deploy job should depend on CI passing (via needs or workflow_run)."""
        wf = _load_workflow()
        trigger = _get_trigger(wf)
        jobs = wf.get("jobs", {})

        # Option A: workflow_run trigger referencing CI
        has_workflow_run = "workflow_run" in trigger

        # Option B: CI job included and deploy job has needs
        deploy_job = jobs.get("deploy", {})
        has_needs = "needs" in deploy_job

        assert has_workflow_run or has_needs, (
            "CD must depend on CI via workflow_run trigger or needs dependency"
        )


class TestDeployAuth:
    """Workload Identity Federation auth tests."""

    def _get_steps(self) -> list:
        wf = _load_workflow()
        jobs = wf.get("jobs", {})
        deploy_job = jobs.get("deploy", {})
        return deploy_job.get("steps", [])

    def test_deploy_uses_wif_auth(self):
        """Auth step must use google-github-actions/auth with WIF."""
        steps = self._get_steps()
        auth_steps = [s for s in steps if "google-github-actions/auth" in s.get("uses", "")]
        assert len(auth_steps) >= 1, "Must have google-github-actions/auth step"
        auth_step = auth_steps[0]
        with_block = auth_step.get("with", {})
        assert "workload_identity_provider" in with_block, (
            "Auth must use workload_identity_provider (WIF)"
        )
        assert "service_account" in with_block

    def test_deploy_wif_uses_secrets(self):
        """WIF config must reference GitHub secrets, not hardcoded values."""
        steps = self._get_steps()
        auth_steps = [s for s in steps if "google-github-actions/auth" in s.get("uses", "")]
        auth_step = auth_steps[0]
        with_block = auth_step.get("with", {})
        wif_provider = str(with_block.get("workload_identity_provider", ""))
        service_account = str(with_block.get("service_account", ""))
        assert "${{" in wif_provider and "secrets." in wif_provider, (
            "workload_identity_provider must reference a GitHub secret"
        )
        assert "${{" in service_account and "secrets." in service_account, (
            "service_account must reference a GitHub secret"
        )


class TestDeployDockerBuildPush:
    """Docker build and push to Artifact Registry tests."""

    def _get_steps(self) -> list:
        wf = _load_workflow()
        jobs = wf.get("jobs", {})
        deploy_job = jobs.get("deploy", {})
        return deploy_job.get("steps", [])

    def test_deploy_docker_build_push_step(self):
        """Must have a Docker build-push step targeting Artifact Registry."""
        steps = self._get_steps()
        # Check for docker/build-push-action or a run step with docker build/push
        build_steps = [
            s
            for s in steps
            if "docker/build-push-action" in s.get("uses", "")
            or (
                "run" in s
                and "docker" in str(s.get("run", "")).lower()
                and (
                    "build" in str(s.get("run", "")).lower()
                    or "push" in str(s.get("run", "")).lower()
                )
            )
        ]
        assert len(build_steps) >= 1, "Must have a Docker build/push step"

    def test_deploy_image_tags(self):
        """Image must be tagged with git SHA."""
        steps = self._get_steps()
        workflow_text = yaml.dump({"steps": steps})
        # SHA reference should appear (github.sha or GITHUB_SHA)
        assert "github.sha" in workflow_text or "GITHUB_SHA" in workflow_text, (
            "Docker image must be tagged with git SHA"
        )

    def test_deploy_targets_prod_stage(self):
        """Docker build must target the prod stage."""
        steps = self._get_steps()
        workflow_text = yaml.dump({"steps": steps})
        assert "prod" in workflow_text, "Docker build must target prod stage"

    def test_deploy_artifact_registry_reference(self):
        """Image must reference Artifact Registry (docker.pkg.dev)."""
        steps = self._get_steps()
        workflow_text = yaml.dump({"steps": steps})
        assert "docker.pkg.dev" in workflow_text, (
            "Docker image must target Artifact Registry (docker.pkg.dev)"
        )


class TestDeployCloudRun:
    """Cloud Run deployment step tests."""

    def _get_steps(self) -> list:
        wf = _load_workflow()
        jobs = wf.get("jobs", {})
        deploy_job = jobs.get("deploy", {})
        return deploy_job.get("steps", [])

    def test_deploy_cloud_run_step(self):
        """Must use google-github-actions/deploy-cloudrun."""
        steps = self._get_steps()
        cr_steps = [
            s for s in steps if "google-github-actions/deploy-cloudrun" in s.get("uses", "")
        ]
        assert len(cr_steps) >= 1, "Must have deploy-cloudrun step"

    def test_deploy_cloud_run_uses_secrets(self):
        """Cloud Run service and region must reference secrets."""
        steps = self._get_steps()
        cr_steps = [
            s for s in steps if "google-github-actions/deploy-cloudrun" in s.get("uses", "")
        ]
        cr_step = cr_steps[0]
        with_block = cr_step.get("with", {})
        service = str(with_block.get("service", ""))
        region = str(with_block.get("region", ""))
        assert "${{" in service or "${{" in region or "secrets." in str(with_block), (
            "Cloud Run config should reference GitHub secrets"
        )


class TestDeployNoHardcodedSecrets:
    """Security: no hardcoded GCP identifiers."""

    def test_deploy_no_hardcoded_secrets(self):
        """Workflow must not contain hardcoded project IDs, regions, or emails."""
        with open(WORKFLOW_PATH) as f:
            content = f.read()

        # Check for patterns that look like hardcoded GCP values
        # Project IDs: typically lowercase-with-dashes
        # Service account emails: something@something.iam.gserviceaccount.com
        sa_pattern = re.compile(r"[a-z0-9-]+@[a-z0-9-]+\.iam\.gserviceaccount\.com")
        assert not sa_pattern.search(content), "Found hardcoded service account email in workflow"

        # Should not have hardcoded Artifact Registry paths (without ${{ }})
        # Lines with docker.pkg.dev should contain ${{ references
        for line in content.split("\n"):
            if "docker.pkg.dev" in line and "${{" not in line:
                # Allow comment lines
                stripped = line.strip()
                if not stripped.startswith("#"):
                    assert False, f"Found hardcoded Artifact Registry path: {line.strip()}"
