"""Tests for S13.3 -- Agent Signal Cards.

Structural validation tests that verify the agent card components
exist with correct content, types, and integration.
"""

import os
import subprocess

import pytest

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")


class TestAgentMetadata:
    """FR-1: Agent metadata registry."""

    def test_agents_metadata_file_exists(self):
        filepath = os.path.join(FRONTEND_DIR, "lib", "agents.ts")
        assert os.path.isfile(filepath), "Missing frontend/lib/agents.ts"

    def test_agents_metadata_has_all_agents(self):
        filepath = os.path.join(FRONTEND_DIR, "lib", "agents.ts")
        with open(filepath) as f:
            content = f.read()
        # SignalSynthesizer is not in the frontend agent registry (it's internal).
        # The registry contains the 6 user-facing agents.
        agents = [
            "ValuationScout",
            "MomentumTracker",
            "PulseMonitor",
            "EconomyWatcher",
            "ComplianceChecker",
            "RiskGuardian",
        ]
        for agent in agents:
            assert agent in content, f"Missing agent metadata for {agent}"

    def test_agents_metadata_has_display_name(self):
        filepath = os.path.join(FRONTEND_DIR, "lib", "agents.ts")
        with open(filepath) as f:
            content = f.read()
        assert "displayName" in content, "Missing displayName field in agent metadata"

    def test_agents_metadata_has_role(self):
        filepath = os.path.join(FRONTEND_DIR, "lib", "agents.ts")
        with open(filepath) as f:
            content = f.read()
        assert "role" in content, "Missing role field in agent metadata"

    def test_agents_metadata_has_icon(self):
        filepath = os.path.join(FRONTEND_DIR, "lib", "agents.ts")
        with open(filepath) as f:
            content = f.read()
        assert "icon" in content, "Missing icon field in agent metadata"

    def test_agents_metadata_exports_get_function(self):
        filepath = os.path.join(FRONTEND_DIR, "lib", "agents.ts")
        with open(filepath) as f:
            content = f.read()
        assert "getAgentMeta" in content, "Missing getAgentMeta function"

    def test_agents_metadata_has_fallback(self):
        """Unknown agent names should return fallback metadata."""
        filepath = os.path.join(FRONTEND_DIR, "lib", "agents.ts")
        with open(filepath) as f:
            content = f.read()
        assert "fallback" in content.lower() or "default" in content.lower(), (
            "Missing fallback/default handling for unknown agents"
        )


class TestAgentDetailType:
    """FR-2: AgentDetail type in api.ts."""

    def test_agent_detail_type_exists(self):
        filepath = os.path.join(FRONTEND_DIR, "types", "api.ts")
        with open(filepath) as f:
            content = f.read()
        assert "interface AgentDetail" in content, "Missing AgentDetail interface"

    def test_agent_detail_has_signal(self):
        filepath = os.path.join(FRONTEND_DIR, "types", "api.ts")
        with open(filepath) as f:
            content = f.read()
        assert "signal:" in content.split("AgentDetail")[1].split("}")[0], (
            "AgentDetail missing signal field"
        )

    def test_agent_detail_has_confidence(self):
        filepath = os.path.join(FRONTEND_DIR, "types", "api.ts")
        with open(filepath) as f:
            content = f.read()
        detail_section = content.split("AgentDetail")[1].split("}")[0]
        assert "confidence" in detail_section, "AgentDetail missing confidence field"

    def test_agent_detail_has_reasoning(self):
        filepath = os.path.join(FRONTEND_DIR, "types", "api.ts")
        with open(filepath) as f:
            content = f.read()
        detail_section = content.split("AgentDetail")[1].split("}")[0]
        assert "reasoning" in detail_section, "AgentDetail missing reasoning field"

    def test_agent_detail_has_key_metrics(self):
        filepath = os.path.join(FRONTEND_DIR, "types", "api.ts")
        with open(filepath) as f:
            content = f.read()
        detail_section = content.split("AgentDetail")[1].split("}")[0]
        assert "key_metrics" in detail_section, "AgentDetail missing key_metrics field"

    def test_final_verdict_has_analyst_details(self):
        filepath = os.path.join(FRONTEND_DIR, "types", "api.ts")
        with open(filepath) as f:
            content = f.read()
        verdict_section = content.split("interface FinalVerdict")[1].split("}")[0]
        assert "analyst_details" in verdict_section, "FinalVerdict missing analyst_details field"


class TestAgentCardComponent:
    """FR-3: AgentCard component."""

    def test_agent_card_component_exists(self):
        filepath = os.path.join(FRONTEND_DIR, "app", "components", "AgentCard.tsx")
        assert os.path.isfile(filepath), "Missing AgentCard.tsx"

    def test_agent_card_has_signal_coloring(self):
        filepath = os.path.join(FRONTEND_DIR, "app", "components", "AgentCard.tsx")
        with open(filepath) as f:
            content = f.read()
        assert "green" in content, "AgentCard missing green color for BUY signal"
        assert "red" in content, "AgentCard missing red color for SELL signal"
        assert "yellow" in content or "amber" in content, (
            "AgentCard missing yellow/amber color for HOLD signal"
        )

    def test_agent_card_has_confidence_display(self):
        filepath = os.path.join(FRONTEND_DIR, "app", "components", "AgentCard.tsx")
        with open(filepath) as f:
            content = f.read()
        assert "confidence" in content.lower(), "AgentCard missing confidence display"

    def test_agent_card_imports_agent_meta(self):
        filepath = os.path.join(FRONTEND_DIR, "app", "components", "AgentCard.tsx")
        with open(filepath) as f:
            content = f.read()
        assert "getAgentMeta" in content, "AgentCard should import getAgentMeta"

    def test_agent_card_has_reasoning_toggle(self):
        filepath = os.path.join(FRONTEND_DIR, "app", "components", "AgentCard.tsx")
        with open(filepath) as f:
            content = f.read()
        assert "Show more" in content or "expanded" in content.lower(), (
            "AgentCard missing reasoning expand/collapse"
        )

    def test_agent_card_has_agent_detail_prop(self):
        filepath = os.path.join(FRONTEND_DIR, "app", "components", "AgentCard.tsx")
        with open(filepath) as f:
            content = f.read()
        assert "AgentDetail" in content, "AgentCard should use AgentDetail type"


class TestAgentCardGridComponent:
    """FR-4: AgentCardGrid component."""

    def test_agent_card_grid_component_exists(self):
        filepath = os.path.join(FRONTEND_DIR, "app", "components", "AgentCardGrid.tsx")
        assert os.path.isfile(filepath), "Missing AgentCardGrid.tsx"

    def test_agent_card_grid_responsive(self):
        filepath = os.path.join(FRONTEND_DIR, "app", "components", "AgentCardGrid.tsx")
        with open(filepath) as f:
            content = f.read()
        assert "grid" in content, "AgentCardGrid missing grid layout"
        assert "md:" in content or "lg:" in content, "AgentCardGrid missing responsive breakpoints"

    def test_agent_card_grid_empty_state(self):
        filepath = os.path.join(FRONTEND_DIR, "app", "components", "AgentCardGrid.tsx")
        with open(filepath) as f:
            content = f.read()
        # Empty state returns null (no entries) -- this is a valid empty-state approach.
        assert "null" in content or "No agent signals" in content or "length === 0" in content, (
            "AgentCardGrid missing empty state handling"
        )

    def test_agent_card_grid_imports_agent_card(self):
        filepath = os.path.join(FRONTEND_DIR, "app", "components", "AgentCardGrid.tsx")
        with open(filepath) as f:
            content = f.read()
        assert "AgentCard" in content, "AgentCardGrid should import AgentCard"

    def test_agent_card_grid_accepts_details_prop(self):
        filepath = os.path.join(FRONTEND_DIR, "app", "components", "AgentCardGrid.tsx")
        with open(filepath) as f:
            content = f.read()
        assert "details" in content, "AgentCardGrid should accept details prop"


class TestPageIntegration:
    """FR-6: Integration with analysis page."""

    def test_page_uses_agent_card_grid(self):
        filepath = os.path.join(FRONTEND_DIR, "app", "page.tsx")
        with open(filepath) as f:
            content = f.read()
        assert "AgentCardGrid" in content, "page.tsx should use AgentCardGrid"

    def test_page_imports_agent_card_grid(self):
        filepath = os.path.join(FRONTEND_DIR, "app", "page.tsx")
        with open(filepath) as f:
            content = f.read()
        assert "import" in content and "AgentCardGrid" in content, (
            "page.tsx should import AgentCardGrid"
        )

    def test_page_passes_analyst_signals(self):
        filepath = os.path.join(FRONTEND_DIR, "app", "page.tsx")
        with open(filepath) as f:
            content = f.read()
        assert "analyst_signals" in content, "page.tsx should pass analyst_signals to AgentCardGrid"


class TestTypeScriptCompilation:
    """Verify TypeScript compiles without errors."""

    @pytest.mark.skipif(
        not os.path.exists(os.path.join(FRONTEND_DIR, "node_modules")),
        reason="node_modules not installed (run npm install in frontend/)",
    )
    def test_typescript_compiles(self):
        result = subprocess.run(
            ["npx", "tsc", "--noEmit"],
            cwd=FRONTEND_DIR,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, (
            f"TypeScript compilation failed:\n{result.stdout}\n{result.stderr}"
        )
