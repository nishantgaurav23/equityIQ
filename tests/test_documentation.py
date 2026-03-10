"""Tests for S14.5 -- Final Documentation.

Validates that all required documentation files exist and contain
the expected sections and content.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestReadmeExists:
    """README.md exists and has minimum content."""

    def test_readme_exists(self):
        readme = ROOT / "README.md"
        assert readme.exists(), "README.md must exist at project root"
        assert readme.stat().st_size > 500, "README.md should have substantial content"

    def test_readme_has_setup_section(self):
        content = (ROOT / "README.md").read_text()
        # Look for setup/installation section
        assert re.search(
            r"##\s*(Quick Start|Setup|Installation|Getting Started|Local Setup)", content
        ), "README must have a setup section"

    def test_readme_has_testing_section(self):
        content = (ROOT / "README.md").read_text()
        assert re.search(r"##\s*(Test|Running Tests|Development)", content), (
            "README must have a testing section"
        )

    def test_readme_has_architecture_section(self):
        content = (ROOT / "README.md").read_text()
        assert re.search(r"##\s*Architecture", content), (
            "README must have an architecture section or link"
        )

    def test_readme_mentions_env_setup(self):
        content = (ROOT / "README.md").read_text()
        assert ".env" in content, "README must mention .env setup"

    def test_readme_mentions_make_commands(self):
        content = (ROOT / "README.md").read_text()
        assert "make" in content.lower(), "README must mention make commands"


class TestApiReference:
    """docs/api-reference.md exists and covers all endpoints."""

    def test_api_reference_exists(self):
        doc = ROOT / "docs" / "api-reference.md"
        assert doc.exists(), "docs/api-reference.md must exist"

    def test_api_reference_has_analyze_endpoint(self):
        content = (ROOT / "docs" / "api-reference.md").read_text()
        assert "/analyze" in content, "API docs must cover /analyze endpoint"

    def test_api_reference_has_portfolio_endpoint(self):
        content = (ROOT / "docs" / "api-reference.md").read_text()
        assert "/portfolio" in content, "API docs must cover /portfolio endpoint"

    def test_api_reference_has_history_endpoint(self):
        content = (ROOT / "docs" / "api-reference.md").read_text()
        assert "/history" in content, "API docs must cover /history endpoint"

    def test_api_reference_has_search_endpoint(self):
        content = (ROOT / "docs" / "api-reference.md").read_text()
        assert "/search" in content, "API docs must cover /search endpoint"

    def test_api_reference_has_health_endpoint(self):
        content = (ROOT / "docs" / "api-reference.md").read_text()
        assert "/health" in content, "API docs must cover /health endpoint"

    def test_api_reference_has_curl_examples(self):
        content = (ROOT / "docs" / "api-reference.md").read_text()
        assert "curl" in content.lower(), "API docs must include curl examples"

    def test_api_reference_has_response_examples(self):
        content = (ROOT / "docs" / "api-reference.md").read_text()
        # Check for JSON response examples
        assert re.search(r'"(ticker|status|final_signal)"', content), (
            "API docs must include response examples"
        )


class TestArchitectureDoc:
    """docs/architecture.md exists and describes the agent system."""

    def test_architecture_doc_exists(self):
        doc = ROOT / "docs" / "architecture.md"
        assert doc.exists(), "docs/architecture.md must exist"

    def test_architecture_has_agent_table(self):
        content = (ROOT / "docs" / "architecture.md").read_text()
        agents = [
            "ValuationScout",
            "MomentumTracker",
            "PulseMonitor",
            "EconomyWatcher",
            "ComplianceChecker",
            "SignalSynthesizer",
            "RiskGuardian",
        ]
        for agent in agents:
            assert agent in content, f"Architecture doc must mention {agent}"

    def test_architecture_has_data_flow(self):
        content = (ROOT / "docs" / "architecture.md").read_text()
        assert re.search(r"(data flow|signal flow|pipeline|orchestrat)", content, re.IGNORECASE), (
            "Architecture doc must describe the data/signal flow"
        )

    def test_architecture_has_signal_weighting(self):
        content = (ROOT / "docs" / "architecture.md").read_text()
        assert re.search(r"(weight|0\.25|0\.20|0\.15)", content), (
            "Architecture doc must describe signal weighting"
        )

    def test_architecture_has_design_decisions(self):
        content = (ROOT / "docs" / "architecture.md").read_text()
        assert re.search(
            r"(design decision|XGBoost|parallel execution|graceful degradation)",
            content,
            re.IGNORECASE,
        ), "Architecture doc must describe key design decisions"


class TestDeploymentDoc:
    """docs/deployment.md exists and covers Docker + GCP."""

    def test_deployment_doc_exists(self):
        doc = ROOT / "docs" / "deployment.md"
        assert doc.exists(), "docs/deployment.md must exist"

    def test_deployment_has_docker_section(self):
        content = (ROOT / "docs" / "deployment.md").read_text()
        assert re.search(r"(docker|Docker|container)", content), "Deployment doc must cover Docker"

    def test_deployment_has_gcp_section(self):
        content = (ROOT / "docs" / "deployment.md").read_text()
        assert re.search(r"(Cloud Run|GCP|Google Cloud)", content), (
            "Deployment doc must cover GCP Cloud Run"
        )

    def test_deployment_has_env_vars(self):
        content = (ROOT / "docs" / "deployment.md").read_text()
        assert re.search(r"(environment variable|\.env|ENVIRONMENT)", content), (
            "Deployment doc must cover environment variables"
        )

    def test_deployment_has_health_check(self):
        content = (ROOT / "docs" / "deployment.md").read_text()
        assert "/health" in content, "Deployment doc must mention health check endpoint"


class TestEnvVarsDocumented:
    """All environment variables from settings.py are documented somewhere."""

    REQUIRED_VARS = [
        "GOOGLE_API_KEY",
        "POLYGON_API_KEY",
        "FRED_API_KEY",
        "NEWS_API_KEY",
        "ENVIRONMENT",
        "SQLITE_DB_PATH",
        "LOG_LEVEL",
    ]

    def test_env_vars_documented_in_readme_or_docs(self):
        """All critical env vars must appear in README or docs."""
        readme = (ROOT / "README.md").read_text()
        deployment = (ROOT / "docs" / "deployment.md").read_text()
        combined = readme + deployment

        missing = [var for var in self.REQUIRED_VARS if var not in combined]
        assert not missing, f"These env vars are not documented: {missing}"


class TestDocsNoBrokenLinks:
    """Check that internal links between docs are valid."""

    def _get_md_files(self) -> list[Path]:
        docs_dir = ROOT / "docs"
        return list(docs_dir.glob("*.md"))

    def test_docs_no_broken_internal_links(self):
        for md_file in self._get_md_files():
            content = md_file.read_text()
            # Find markdown links like [text](path)
            links = re.findall(r"\[.*?\]\(((?!http)[^)]+)\)", content)
            for link in links:
                # Strip anchor
                path = link.split("#")[0]
                if not path:
                    continue
                target = md_file.parent / path
                assert target.exists(), (
                    f"Broken link in {md_file.name}: {link} -> {target} does not exist"
                )
