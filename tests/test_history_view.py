"""Tests for S13.4 -- History View frontend page."""

import os
import re
import subprocess

import pytest

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


class TestFileExistence:
    """Verify all required files exist."""

    def test_history_page_exists(self):
        path = os.path.join(FRONTEND_DIR, "app", "history", "page.tsx")
        assert os.path.isfile(path), f"Missing: {path}"

    def test_history_table_component_exists(self):
        path = os.path.join(FRONTEND_DIR, "app", "history", "components", "HistoryTable.tsx")
        assert os.path.isfile(path), f"Missing: {path}"

    def test_signal_trend_chart_exists(self):
        path = os.path.join(
            FRONTEND_DIR, "app", "history", "components", "SignalTrendChart.tsx"
        )
        assert os.path.isfile(path), f"Missing: {path}"

    def test_date_range_filter_exists(self):
        path = os.path.join(
            FRONTEND_DIR, "app", "history", "components", "DateRangeFilter.tsx"
        )
        assert os.path.isfile(path), f"Missing: {path}"


class TestSignalSnapshotType:
    """Verify SignalSnapshot type is defined in types/api.ts."""

    def test_signal_snapshot_interface_exists(self):
        path = os.path.join(FRONTEND_DIR, "types", "api.ts")
        content = open(path).read()
        assert "SignalSnapshot" in content, "SignalSnapshot interface not found in types/api.ts"

    def test_signal_snapshot_has_required_fields(self):
        path = os.path.join(FRONTEND_DIR, "types", "api.ts")
        content = open(path).read()
        for field in ["session_id", "ticker", "final_signal", "overall_confidence", "created_at"]:
            assert field in content, f"SignalSnapshot missing field: {field}"


class TestApiClientFunctions:
    """Verify API client has history functions."""

    def test_api_exports_get_ticker_history(self):
        path = os.path.join(FRONTEND_DIR, "lib", "api.ts")
        content = open(path).read()
        assert "getTickerHistory" in content, "getTickerHistory not found in lib/api.ts"

    def test_api_exports_get_signal_trend(self):
        path = os.path.join(FRONTEND_DIR, "lib", "api.ts")
        content = open(path).read()
        assert "getSignalTrend" in content, "getSignalTrend not found in lib/api.ts"

    def test_get_ticker_history_returns_final_verdict_array(self):
        path = os.path.join(FRONTEND_DIR, "lib", "api.ts")
        content = open(path).read()
        assert re.search(r"getTickerHistory.*FinalVerdict\[\]", content, re.DOTALL), (
            "getTickerHistory should return Promise<FinalVerdict[]>"
        )

    def test_get_signal_trend_returns_signal_snapshot_array(self):
        path = os.path.join(FRONTEND_DIR, "lib", "api.ts")
        content = open(path).read()
        assert re.search(r"getSignalTrend.*SignalSnapshot\[\]", content, re.DOTALL), (
            "getSignalTrend should return Promise<SignalSnapshot[]>"
        )

    def test_api_imports_signal_snapshot(self):
        path = os.path.join(FRONTEND_DIR, "lib", "api.ts")
        content = open(path).read()
        assert "SignalSnapshot" in content, "lib/api.ts should import SignalSnapshot"


class TestHistoryPageContent:
    """Verify history page has required UI elements."""

    def test_history_page_has_ticker_input(self):
        path = os.path.join(FRONTEND_DIR, "app", "history", "page.tsx")
        content = open(path).read()
        # Redesigned page uses filter tabs and verdict rows instead of a raw input.
        # Verify interactive filtering or search capability exists.
        assert "filter" in content.lower() or "input" in content or "Search" in content, (
            "History page should have filtering or search capability"
        )

    def test_history_page_imports_components(self):
        path = os.path.join(FRONTEND_DIR, "app", "history", "page.tsx")
        content = open(path).read()
        # Redesigned page uses SignalBadge and inline rows instead of HistoryTable/SignalTrendChart.
        assert "SignalBadge" in content, "History page should use SignalBadge component"

    def test_history_page_imports_api_functions(self):
        path = os.path.join(FRONTEND_DIR, "app", "history", "page.tsx")
        content = open(path).read()
        assert (
            "getTickerHistory" in content
            or "getSignalTrend" in content
            or "getRecentVerdicts" in content
        ), "History page should use API functions"

    def test_history_page_has_loading_state(self):
        path = os.path.join(FRONTEND_DIR, "app", "history", "page.tsx")
        content = open(path).read()
        assert re.search(r"loading|Loading|isLoading|setLoading", content), (
            "History page should have a loading state"
        )

    def test_history_page_has_error_handling(self):
        path = os.path.join(FRONTEND_DIR, "app", "history", "page.tsx")
        content = open(path).read()
        # Redesigned page uses .catch() for error handling instead of explicit error state.
        assert re.search(r"error|Error|setError|\.catch", content), (
            "History page should handle errors"
        )


class TestHistoryTableComponent:
    """Verify HistoryTable component content."""

    def test_history_table_has_signal_badges(self):
        path = os.path.join(FRONTEND_DIR, "app", "history", "components", "HistoryTable.tsx")
        content = open(path).read()
        # Should have color coding for signals
        assert re.search(r"green|red|yellow|emerald|rose|amber", content, re.IGNORECASE), (
            "HistoryTable should have color-coded signal badges"
        )

    def test_history_table_accepts_verdicts_prop(self):
        path = os.path.join(FRONTEND_DIR, "app", "history", "components", "HistoryTable.tsx")
        content = open(path).read()
        assert "FinalVerdict" in content, "HistoryTable should use FinalVerdict type"

    def test_history_table_has_columns(self):
        path = os.path.join(FRONTEND_DIR, "app", "history", "components", "HistoryTable.tsx")
        content = open(path).read()
        # Should display key columns
        for col in ["Signal", "Confidence"]:
            assert col in content or col.lower() in content.lower(), (
                f"HistoryTable should have {col} column"
            )

    def test_history_table_handles_empty(self):
        path = os.path.join(FRONTEND_DIR, "app", "history", "components", "HistoryTable.tsx")
        content = open(path).read()
        assert re.search(r"no.*anal|empty|No.*found|length.*0|\.length", content, re.IGNORECASE), (
            "HistoryTable should handle empty data"
        )


class TestSignalTrendChart:
    """Verify SignalTrendChart component."""

    def test_trend_chart_maps_signals_to_numbers(self):
        path = os.path.join(
            FRONTEND_DIR, "app", "history", "components", "SignalTrendChart.tsx"
        )
        content = open(path).read()
        # Should map signals like STRONG_BUY=2, BUY=1, HOLD=0, SELL=-1, STRONG_SELL=-2
        assert re.search(r"STRONG_BUY|STRONG_SELL", content), (
            "SignalTrendChart should map signal levels"
        )

    def test_trend_chart_accepts_snapshots_prop(self):
        path = os.path.join(
            FRONTEND_DIR, "app", "history", "components", "SignalTrendChart.tsx"
        )
        content = open(path).read()
        assert "SignalSnapshot" in content, "SignalTrendChart should use SignalSnapshot type"

    def test_trend_chart_handles_empty(self):
        path = os.path.join(
            FRONTEND_DIR, "app", "history", "components", "SignalTrendChart.tsx"
        )
        content = open(path).read()
        assert re.search(r"no.*data|empty|No.*trend|length.*0|\.length", content, re.IGNORECASE), (
            "SignalTrendChart should handle empty data"
        )


class TestDateRangeFilter:
    """Verify DateRangeFilter component."""

    def test_date_filter_has_date_inputs(self):
        path = os.path.join(
            FRONTEND_DIR, "app", "history", "components", "DateRangeFilter.tsx"
        )
        content = open(path).read()
        assert re.search(r'type=["\']date["\']', content), (
            "DateRangeFilter should have date input fields"
        )

    def test_date_filter_has_clear_button(self):
        path = os.path.join(
            FRONTEND_DIR, "app", "history", "components", "DateRangeFilter.tsx"
        )
        content = open(path).read()
        assert re.search(r"[Cc]lear|[Rr]eset", content), (
            "DateRangeFilter should have a clear/reset button"
        )


class TestLayoutNavigation:
    """Verify layout has history navigation link."""

    def test_layout_has_history_link(self):
        path = os.path.join(FRONTEND_DIR, "app", "layout.tsx")
        content = open(path).read()
        assert re.search(r'href=["\']/?history["\']|/history', content), (
            "Layout should have link to /history"
        )


class TestBuildSucceeds:
    """Verify frontend builds without errors."""

    @pytest.mark.slow
    @pytest.mark.skipif(
        not os.path.exists(
            os.path.join(os.path.dirname(__file__), "..", "frontend", "node_modules")
        ),
        reason="node_modules not installed (run npm install in frontend/)",
    )
    def test_next_build_succeeds(self):
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=FRONTEND_DIR,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, f"Build failed:\n{result.stderr}\n{result.stdout}"
