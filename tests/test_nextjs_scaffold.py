"""Tests for S13.1 -- Next.js Scaffold.

Structural validation tests that verify the frontend project
is properly set up with all required files and configurations.
"""

import json
import os
import subprocess

import pytest

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")


class TestProjectStructure:
    """FR-1: Verify all required project files exist."""

    @pytest.mark.parametrize(
        "filename",
        [
            "package.json",
            "tsconfig.json",
            "next.config.ts",
            "app/layout.tsx",
            "app/page.tsx",
            "app/globals.css",
        ],
    )
    def test_required_files_exist(self, filename):
        filepath = os.path.join(FRONTEND_DIR, filename)
        assert os.path.isfile(filepath), f"Missing required file: {filename}"

    def test_public_directory_exists(self):
        assert os.path.isdir(os.path.join(FRONTEND_DIR, "public"))

    def test_lib_directory_exists(self):
        assert os.path.isdir(os.path.join(FRONTEND_DIR, "lib"))

    def test_types_directory_exists(self):
        assert os.path.isdir(os.path.join(FRONTEND_DIR, "types"))


class TestPackageJson:
    """FR-1: Verify package.json has correct dependencies."""

    @pytest.fixture
    def pkg(self):
        with open(os.path.join(FRONTEND_DIR, "package.json")) as f:
            return json.load(f)

    @pytest.mark.parametrize(
        "dep",
        ["next", "react", "react-dom"],
    )
    def test_has_runtime_dependency(self, pkg, dep):
        assert dep in pkg.get("dependencies", {}), f"Missing dependency: {dep}"

    @pytest.mark.parametrize(
        "dep",
        ["typescript", "@types/node", "@types/react", "@types/react-dom", "tailwindcss"],
    )
    def test_has_dev_dependency(self, pkg, dep):
        deps = pkg.get("devDependencies", {})
        all_deps = {**pkg.get("dependencies", {}), **deps}
        assert dep in all_deps, f"Missing dev dependency: {dep}"

    def test_has_build_script(self, pkg):
        assert "build" in pkg.get("scripts", {}), "Missing 'build' script"

    def test_has_dev_script(self, pkg):
        assert "dev" in pkg.get("scripts", {}), "Missing 'dev' script"

    def test_has_lint_script(self, pkg):
        assert "lint" in pkg.get("scripts", {}), "Missing 'lint' script"


class TestEnvironmentConfig:
    """FR-2: Verify environment configuration."""

    def test_env_example_exists(self):
        filepath = os.path.join(FRONTEND_DIR, ".env.local.example")
        assert os.path.isfile(filepath), "Missing .env.local.example"

    def test_env_example_has_api_url(self):
        filepath = os.path.join(FRONTEND_DIR, ".env.local.example")
        with open(filepath) as f:
            content = f.read()
        assert "NEXT_PUBLIC_API_URL" in content, "Missing NEXT_PUBLIC_API_URL in .env.local.example"

    def test_env_example_has_app_name(self):
        filepath = os.path.join(FRONTEND_DIR, ".env.local.example")
        with open(filepath) as f:
            content = f.read()
        assert "NEXT_PUBLIC_APP_NAME" in content, (
            "Missing NEXT_PUBLIC_APP_NAME in .env.local.example"
        )

    def test_config_module_exists(self):
        filepath = os.path.join(FRONTEND_DIR, "lib", "config.ts")
        assert os.path.isfile(filepath), "Missing lib/config.ts"

    def test_config_has_defaults(self):
        filepath = os.path.join(FRONTEND_DIR, "lib", "config.ts")
        with open(filepath) as f:
            content = f.read()
        assert "localhost:8000" in content, "Missing default API URL in config.ts"
        assert "EquityIQ" in content, "Missing default app name in config.ts"


class TestApiClient:
    """FR-3: Verify API client setup."""

    def test_api_client_exists(self):
        filepath = os.path.join(FRONTEND_DIR, "lib", "api.ts")
        assert os.path.isfile(filepath), "Missing lib/api.ts"

    def test_api_client_has_analyze_function(self):
        filepath = os.path.join(FRONTEND_DIR, "lib", "api.ts")
        with open(filepath) as f:
            content = f.read()
        assert "analyzeStock" in content, "Missing analyzeStock function in api.ts"

    def test_api_client_has_error_handling(self):
        filepath = os.path.join(FRONTEND_DIR, "lib", "api.ts")
        with open(filepath) as f:
            content = f.read()
        assert "ApiError" in content, "Missing ApiError class in api.ts"

    def test_api_client_has_health_check(self):
        filepath = os.path.join(FRONTEND_DIR, "lib", "api.ts")
        with open(filepath) as f:
            content = f.read()
        assert "checkHealth" in content, "Missing checkHealth function in api.ts"


class TestTypeDefinitions:
    """FR-4: Verify TypeScript type definitions."""

    def test_types_file_exists(self):
        filepath = os.path.join(FRONTEND_DIR, "types", "api.ts")
        assert os.path.isfile(filepath), "Missing types/api.ts"

    def test_types_has_final_verdict(self):
        filepath = os.path.join(FRONTEND_DIR, "types", "api.ts")
        with open(filepath) as f:
            content = f.read()
        assert "FinalVerdict" in content, "Missing FinalVerdict interface"

    def test_types_has_analyst_report(self):
        filepath = os.path.join(FRONTEND_DIR, "types", "api.ts")
        with open(filepath) as f:
            content = f.read()
        assert "AnalystReport" in content, "Missing AnalystReport interface"

    def test_types_has_signal_enum(self):
        filepath = os.path.join(FRONTEND_DIR, "types", "api.ts")
        with open(filepath) as f:
            content = f.read()
        assert "STRONG_BUY" in content, "Missing signal type definitions"
        assert "STRONG_SELL" in content, "Missing signal type definitions"

    def test_types_has_portfolio_insight(self):
        filepath = os.path.join(FRONTEND_DIR, "types", "api.ts")
        with open(filepath) as f:
            content = f.read()
        assert "PortfolioInsight" in content, "Missing PortfolioInsight interface"


class TestLayoutStructure:
    """FR-5: Verify layout and base styling."""

    def test_layout_has_html_structure(self):
        filepath = os.path.join(FRONTEND_DIR, "app", "layout.tsx")
        with open(filepath) as f:
            content = f.read()
        assert "<html" in content, "Missing <html> element in layout"
        assert "<body" in content, "Missing <body> element in layout"

    def test_layout_has_header(self):
        filepath = os.path.join(FRONTEND_DIR, "app", "layout.tsx")
        with open(filepath) as f:
            content = f.read()
        assert "<header" in content, "Missing <header> element in layout"

    def test_layout_has_main(self):
        filepath = os.path.join(FRONTEND_DIR, "app", "layout.tsx")
        with open(filepath) as f:
            content = f.read()
        assert "<main" in content, "Missing <main> element in layout"

    def test_layout_has_footer(self):
        filepath = os.path.join(FRONTEND_DIR, "app", "layout.tsx")
        with open(filepath) as f:
            content = f.read()
        assert "<footer" in content, "Missing <footer> element in layout"

    def test_layout_has_metadata(self):
        filepath = os.path.join(FRONTEND_DIR, "app", "layout.tsx")
        with open(filepath) as f:
            content = f.read()
        assert "metadata" in content, "Missing metadata export in layout"

    def test_globals_css_has_tailwind(self):
        filepath = os.path.join(FRONTEND_DIR, "app", "globals.css")
        with open(filepath) as f:
            content = f.read()
        assert "@tailwind" in content or "@import" in content, (
            "Missing Tailwind directives in globals.css"
        )


class TestHomePage:
    """FR-6: Verify home page content."""

    def test_homepage_has_app_name(self):
        filepath = os.path.join(FRONTEND_DIR, "app", "page.tsx")
        with open(filepath) as f:
            content = f.read()
        # Redesigned page uses "AI Stock Predictor" as the hero heading.
        assert "EquityIQ" in content or "AI Stock Predictor" in content, (
            "Missing app branding on homepage"
        )

    def test_homepage_has_health_check(self):
        filepath = os.path.join(FRONTEND_DIR, "app", "page.tsx")
        with open(filepath) as f:
            content = f.read()
        assert "health" in content.lower() or "status" in content.lower(), (
            "Missing health/status indicator on homepage"
        )


class TestTailwindConfig:
    """FR-1: Verify Tailwind CSS is configured via globals.css (Tailwind v4)."""

    def test_globals_css_imports_tailwind(self):
        filepath = os.path.join(FRONTEND_DIR, "app", "globals.css")
        with open(filepath) as f:
            content = f.read()
        assert '@import "tailwindcss"' in content, "Missing Tailwind v4 import in globals.css"


class TestNextConfig:
    """FR-3: Verify Next.js configuration."""

    def test_next_config_exists(self):
        filepath = os.path.join(FRONTEND_DIR, "next.config.ts")
        assert os.path.isfile(filepath), "Missing next.config.ts"

    def test_next_config_has_rewrites(self):
        filepath = os.path.join(FRONTEND_DIR, "next.config.ts")
        with open(filepath) as f:
            content = f.read()
        assert "rewrites" in content or "proxy" in content.lower(), (
            "Missing API rewrites/proxy in next.config.ts"
        )


class TestTypescriptCompilation:
    """Verify TypeScript compiles without errors."""

    def test_typescript_compiles(self):
        result = subprocess.run(
            ["npx", "tsc", "--noEmit"],
            cwd=FRONTEND_DIR,
            capture_output=True,
            text=True,
            timeout=120,
        )
        msg = f"TypeScript compilation failed:\n{result.stdout}\n{result.stderr}"
        assert result.returncode == 0, msg


# ── S13.2: Stock Analysis Page Tests ─────────────────────────────────────────


class TestAnalysisPage:
    """S13.2: Verify analysis page structure and functionality."""

    @pytest.fixture
    def page_content(self):
        filepath = os.path.join(FRONTEND_DIR, "app", "page.tsx")
        with open(filepath) as f:
            return f.read()

    def test_page_has_ticker_input(self, page_content):
        # Redesigned page uses TickerSearch component instead of a raw <input>.
        assert "<input" in page_content or "TickerSearch" in page_content, (
            "Missing ticker input or TickerSearch component in page.tsx"
        )

    def test_page_has_submit_button(self, page_content):
        assert "<button" in page_content, "Missing <button> element in page.tsx"
        assert "Analyz" in page_content, "Missing analyze button text in page.tsx"

    def test_page_imports_analyze_stock(self, page_content):
        assert "analyzeStock" in page_content, "page.tsx must import analyzeStock from api client"

    def test_page_has_error_handling(self, page_content):
        assert "error" in page_content.lower(), "page.tsx must handle error state"
        assert "setError" in page_content or "Error" in page_content, (
            "page.tsx must have error state management"
        )

    def test_page_has_loading_state(self, page_content):
        assert "loading" in page_content.lower() or "isLoading" in page_content, (
            "page.tsx must have loading state"
        )
        # Disabled state is now in the TickerSearch component, not in page.tsx directly.
        # Verify page passes isLoading to TickerSearch.
        assert "isLoading" in page_content, (
            "page.tsx must pass loading state (isLoading) to TickerSearch"
        )


class TestSignalBadge:
    """S13.2: Verify SignalBadge component."""

    def test_signal_badge_component_exists(self):
        filepath = os.path.join(FRONTEND_DIR, "components", "SignalBadge.tsx")
        assert os.path.isfile(filepath), "Missing components/SignalBadge.tsx"

    def test_signal_badge_has_signal_prop(self):
        filepath = os.path.join(FRONTEND_DIR, "components", "SignalBadge.tsx")
        with open(filepath) as f:
            content = f.read()
        assert "FinalSignal" in content, "SignalBadge must use FinalSignal type"

    def test_signal_badge_colors(self):
        """SignalBadge maps all 5 signals to appropriate color classes."""
        filepath = os.path.join(FRONTEND_DIR, "components", "SignalBadge.tsx")
        with open(filepath) as f:
            content = f.read()
        for signal in ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]:
            assert signal in content, f"SignalBadge missing mapping for {signal}"
        assert "green" in content, "SignalBadge must use green for BUY signals"
        assert "red" in content, "SignalBadge must use red for SELL signals"
        assert "yellow" in content, "SignalBadge must use yellow for HOLD signal"


class TestConfidenceMeter:
    """S13.2: Verify ConfidenceMeter component."""

    def test_confidence_meter_component_exists(self):
        filepath = os.path.join(FRONTEND_DIR, "components", "ConfidenceMeter.tsx")
        assert os.path.isfile(filepath), "Missing components/ConfidenceMeter.tsx"

    def test_confidence_meter_has_confidence_prop(self):
        filepath = os.path.join(FRONTEND_DIR, "components", "ConfidenceMeter.tsx")
        with open(filepath) as f:
            content = f.read()
        assert "confidence" in content, "ConfidenceMeter must accept confidence prop"


class TestKeyDrivers:
    """S13.2: Verify KeyDrivers component."""

    def test_key_drivers_component_exists(self):
        filepath = os.path.join(FRONTEND_DIR, "components", "KeyDrivers.tsx")
        assert os.path.isfile(filepath), "Missing components/KeyDrivers.tsx"

    def test_key_drivers_has_drivers_prop(self):
        filepath = os.path.join(FRONTEND_DIR, "components", "KeyDrivers.tsx")
        with open(filepath) as f:
            content = f.read()
        assert "drivers" in content, "KeyDrivers must accept drivers prop"
        assert "No key drivers" in content, "KeyDrivers must handle empty array"


class TestAnalystSignals:
    """S13.2: Verify AnalystSignals component."""

    def test_analyst_signals_component_exists(self):
        filepath = os.path.join(FRONTEND_DIR, "components", "AnalystSignals.tsx")
        assert os.path.isfile(filepath), "Missing components/AnalystSignals.tsx"

    def test_analyst_signals_has_signals_prop(self):
        filepath = os.path.join(FRONTEND_DIR, "components", "AnalystSignals.tsx")
        with open(filepath) as f:
            content = f.read()
        assert "signals" in content, "AnalystSignals must accept signals prop"


class TestAnalysisPageComponents:
    """S13.2: Verify components use TypeScript properly."""

    @pytest.mark.parametrize(
        "component",
        ["SignalBadge.tsx", "ConfidenceMeter.tsx", "KeyDrivers.tsx", "AnalystSignals.tsx"],
    )
    def test_components_use_typescript(self, component):
        filepath = os.path.join(FRONTEND_DIR, "components", component)
        with open(filepath) as f:
            content = f.read()
        assert "interface" in content or "type" in content or "Props" in content, (
            f"{component} must use TypeScript typing"
        )
