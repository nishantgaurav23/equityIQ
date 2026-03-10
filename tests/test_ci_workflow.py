"""Tests for S12.1 -- GitHub Actions CI workflow."""

from pathlib import Path

import yaml

WORKFLOW_PATH = Path(__file__).parent.parent / ".github" / "workflows" / "ci.yml"


def _load_workflow():
    """Load and parse the CI workflow YAML."""
    assert WORKFLOW_PATH.exists(), f"CI workflow not found at {WORKFLOW_PATH}"
    with open(WORKFLOW_PATH) as f:
        return yaml.safe_load(f)


class TestCIWorkflowStructure:
    """Validate CI workflow file exists and is valid."""

    def test_ci_workflow_exists(self):
        assert WORKFLOW_PATH.exists(), "ci.yml must exist at .github/workflows/ci.yml"

    def test_ci_workflow_valid_yaml(self):
        wf = _load_workflow()
        assert isinstance(wf, dict), "ci.yml must be a valid YAML mapping"

    def test_ci_workflow_name(self):
        wf = _load_workflow()
        assert "name" in wf, "Workflow must have a name"
        assert isinstance(wf["name"], str) and len(wf["name"]) > 0


class TestCITriggers:
    """Validate workflow triggers."""

    def test_ci_trigger_push(self):
        wf = _load_workflow()
        assert "push" in wf.get(True, {}), "Workflow must trigger on push"

    def test_ci_trigger_pull_request(self):
        wf = _load_workflow()
        on = wf.get(True, {})
        assert "pull_request" in on, "Workflow must trigger on pull_request"
        pr = on["pull_request"]
        assert "branches" in pr, "pull_request must specify target branches"
        assert "main" in pr["branches"], "pull_request must target main branch"


class TestCIJob:
    """Validate job configuration."""

    def _get_job(self):
        wf = _load_workflow()
        jobs = wf.get("jobs", {})
        assert len(jobs) > 0, "Workflow must have at least one job"
        # Get the first (and expected only) job
        job_name = list(jobs.keys())[0]
        return jobs[job_name]

    def _get_steps(self):
        job = self._get_job()
        return job.get("steps", [])

    def _find_step_by_uses(self, uses_prefix):
        """Find a step that uses a specific action."""
        for step in self._get_steps():
            uses = step.get("uses", "")
            if uses.startswith(uses_prefix):
                return step
        return None

    def _find_step_by_run(self, run_substring):
        """Find a step whose run command contains the given substring."""
        for step in self._get_steps():
            run = step.get("run", "")
            if run_substring in run:
                return step
        return None

    def test_ci_runs_on_ubuntu(self):
        job = self._get_job()
        runs_on = job.get("runs-on", "")
        assert "ubuntu" in runs_on, "Job must run on ubuntu"

    def test_ci_python_version(self):
        step = self._find_step_by_uses("actions/setup-python")
        assert step is not None, "Must use actions/setup-python"
        python_version = str(step.get("with", {}).get("python-version", ""))
        assert "3.12" in python_version, "Must use Python 3.12"

    def test_ci_pip_cache(self):
        step = self._find_step_by_uses("actions/setup-python")
        assert step is not None, "Must use actions/setup-python"
        cache = step.get("with", {}).get("cache", "")
        assert cache == "pip", "Must enable pip caching"

    def test_ci_install_step(self):
        step = self._find_step_by_run(".[dev]")
        assert step is not None, "Must have a step that installs dev dependencies"

    def test_ci_pytest_step(self):
        step = self._find_step_by_run("pytest")
        assert step is not None, "Must have a step that runs pytest"

    def test_ci_ruff_check_step(self):
        step = self._find_step_by_run("ruff check")
        assert step is not None, "Must have a step that runs ruff check"

    def test_ci_ruff_format_step(self):
        step = self._find_step_by_run("ruff format")
        assert step is not None, "Must have a step that runs ruff format"


class TestCIConcurrency:
    """Validate concurrency configuration."""

    def test_ci_concurrency_group(self):
        wf = _load_workflow()
        assert "concurrency" in wf, "Workflow must have concurrency config"
        conc = wf["concurrency"]
        assert "group" in conc, "Concurrency must define a group"
        assert conc.get("cancel-in-progress") is True, "Must cancel in-progress runs"
