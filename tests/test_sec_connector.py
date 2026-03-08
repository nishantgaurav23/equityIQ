"""Tests for SEC Edgar connector -- tools/sec_connector.py."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from config.settings import Settings


@pytest.fixture
def settings():
    """Settings with test defaults."""
    return Settings(ENVIRONMENT="test")


@pytest.fixture
def connector(settings):
    """Fresh SecConnector instance with test settings."""
    from tools.sec_connector import SecConnector

    return SecConnector(settings=settings)


# --- Sample SEC API Responses ---

SAMPLE_COMPANY_TICKERS = {
    "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corporation"},
}

SAMPLE_SUBMISSIONS = {
    "cik": "320193",
    "entityType": "operating",
    "name": "Apple Inc.",
    "tickers": ["AAPL"],
    "filings": {
        "recent": {
            "accessionNumber": [
                "0000320193-23-000106",
                "0000320193-23-000077",
                "0000320193-23-000064",
            ],
            "filingDate": [
                "2023-11-03",
                "2023-08-04",
                "2023-05-05",
            ],
            "form": ["10-K", "10-Q", "10-Q"],
            "primaryDocument": [
                "aapl-20230930.htm",
                "aapl-20230701.htm",
                "aapl-20230401.htm",
            ],
            "primaryDocDescription": [
                "10-K Annual Report",
                "10-Q Quarterly Report",
                "10-Q Quarterly Report",
            ],
        }
    },
}

SAMPLE_SUBMISSIONS_GOING_CONCERN = {
    "cik": "999999",
    "entityType": "operating",
    "name": "Risky Corp",
    "tickers": ["RISK"],
    "filings": {
        "recent": {
            "accessionNumber": ["0000999999-23-000001", "0000999999-23-000002"],
            "filingDate": ["2023-11-01", "2023-08-01"],
            "form": ["10-K", "8-K"],
            "primaryDocument": ["risk-10k.htm", "risk-8k.htm"],
            "primaryDocDescription": [
                "10-K Annual Report - Going Concern Doubt",
                "8-K Current Report - Restatement of Financial Statements",
            ],
        }
    },
}


def _make_response(data, status_code=200):
    """Create a mock httpx.Response."""
    return httpx.Response(
        status_code=status_code,
        json=data,
        request=httpx.Request("GET", "https://example.com"),
    )


def _make_text_response(text, status_code=200):
    """Create a mock httpx.Response with text content."""
    return httpx.Response(
        status_code=status_code,
        text=text,
        request=httpx.Request("GET", "https://example.com"),
    )


# --- Test SecConnector class existence and init ---


class TestSecConnectorInit:
    def test_class_exists(self):
        from tools.sec_connector import SecConnector

        assert SecConnector is not None

    def test_init_default_settings(self, connector):
        assert connector.client is not None
        assert connector.cache is not None

    def test_init_has_user_agent(self, connector):
        assert "User-Agent" in connector.client.headers or hasattr(connector, "user_agent")

    def test_init_ttl_cache_5min(self, connector):
        assert connector.cache.ttl == 300

    def test_module_singleton(self):
        from tools.sec_connector import sec

        assert sec is not None


# --- Test get_company_cik ---


class TestGetCompanyCik:
    @pytest.mark.asyncio
    async def test_cik_success(self, connector):
        mock_response = _make_response(SAMPLE_COMPANY_TICKERS)
        mock_get = AsyncMock(return_value=mock_response)
        with patch.object(connector.client, "get", mock_get):
            cik = await connector.get_company_cik("AAPL")
            assert cik == "320193"

    @pytest.mark.asyncio
    async def test_cik_not_found(self, connector):
        mock_response = _make_response(SAMPLE_COMPANY_TICKERS)
        mock_get = AsyncMock(return_value=mock_response)
        with patch.object(connector.client, "get", mock_get):
            cik = await connector.get_company_cik("ZZZZZZ")
            assert cik is None

    @pytest.mark.asyncio
    async def test_cik_network_error(self, connector):
        with patch.object(
            connector.client, "get", new_callable=AsyncMock, side_effect=httpx.ConnectError("fail")
        ):
            cik = await connector.get_company_cik("AAPL")
            assert cik is None

    @pytest.mark.asyncio
    async def test_cik_bad_status(self, connector):
        mock_response = _make_response({}, status_code=500)
        mock_get = AsyncMock(return_value=mock_response)
        with patch.object(connector.client, "get", mock_get):
            cik = await connector.get_company_cik("AAPL")
            assert cik is None

    @pytest.mark.asyncio
    async def test_cik_cached(self, connector):
        mock_response = _make_response(SAMPLE_COMPANY_TICKERS)
        mock_get = AsyncMock(return_value=mock_response)
        with patch.object(connector.client, "get", mock_get):
            cik1 = await connector.get_company_cik("AAPL")
            cik2 = await connector.get_company_cik("AAPL")
            assert cik1 == cik2 == "320193"
            assert mock_get.call_count == 1  # cached on second call


# --- Test get_sec_filings ---


class TestGetSecFilings:
    @pytest.mark.asyncio
    async def test_filings_success(self, connector):
        cik_response = _make_response(SAMPLE_COMPANY_TICKERS)
        filings_response = _make_response(SAMPLE_SUBMISSIONS)

        mock_get = AsyncMock(side_effect=[cik_response, filings_response])
        with patch.object(connector.client, "get", mock_get):
            filings = await connector.get_sec_filings("AAPL")
            assert isinstance(filings, list)
            assert len(filings) > 0
            # Check filing dict structure
            filing = filings[0]
            assert "filing_type" in filing
            assert "filed_date" in filing
            assert "description" in filing

    @pytest.mark.asyncio
    async def test_filings_cik_not_found(self, connector):
        cik_response = _make_response(SAMPLE_COMPANY_TICKERS)
        mock_get = AsyncMock(return_value=cik_response)
        with patch.object(connector.client, "get", mock_get):
            filings = await connector.get_sec_filings("ZZZZZZ")
            assert filings == []

    @pytest.mark.asyncio
    async def test_filings_network_error(self, connector):
        with patch.object(
            connector.client, "get", new_callable=AsyncMock, side_effect=httpx.ConnectError("fail")
        ):
            filings = await connector.get_sec_filings("AAPL")
            assert filings == []

    @pytest.mark.asyncio
    async def test_filings_bad_response(self, connector):
        cik_response = _make_response(SAMPLE_COMPANY_TICKERS)
        bad_response = _make_response({}, status_code=500)

        mock_get = AsyncMock(side_effect=[cik_response, bad_response])
        with patch.object(connector.client, "get", mock_get):
            filings = await connector.get_sec_filings("AAPL")
            assert filings == []

    @pytest.mark.asyncio
    async def test_filings_cached(self, connector):
        cik_response = _make_response(SAMPLE_COMPANY_TICKERS)
        filings_response = _make_response(SAMPLE_SUBMISSIONS)

        mock_get = AsyncMock(side_effect=[cik_response, filings_response])
        with patch.object(connector.client, "get", mock_get):
            filings1 = await connector.get_sec_filings("AAPL")

        # Second call should hit cache
        mock_get2 = AsyncMock()
        with patch.object(connector.client, "get", mock_get2):
            filings2 = await connector.get_sec_filings("AAPL")
            assert filings1 == filings2
            mock_get2.assert_not_called()


# --- Test score_risk ---


class TestScoreRisk:
    @pytest.mark.asyncio
    async def test_score_risk_clean(self, connector):
        """Clean filings should have low risk score."""
        cik_response = _make_response(SAMPLE_COMPANY_TICKERS)
        filings_response = _make_response(SAMPLE_SUBMISSIONS)

        mock_get = AsyncMock(side_effect=[cik_response, filings_response])
        with patch.object(connector.client, "get", mock_get):
            result = await connector.score_risk("AAPL")
            assert isinstance(result, dict)
            assert "risk_score" in result
            assert "risk_flags" in result
            assert "latest_filing_type" in result
            assert "days_since_filing" in result
            assert result["risk_score"] >= 0.0
            assert result["risk_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_score_risk_going_concern(self, connector):
        """Going concern flag should produce high risk score."""
        cik_response = _make_response(
            {"0": {"cik_str": 999999, "ticker": "RISK", "title": "Risky Corp"}}
        )
        filings_response = _make_response(SAMPLE_SUBMISSIONS_GOING_CONCERN)

        mock_get = AsyncMock(side_effect=[cik_response, filings_response])
        with patch.object(connector.client, "get", mock_get):
            result = await connector.score_risk("RISK")
            assert "going_concern" in result["risk_flags"]
            assert result["risk_score"] >= 0.5

    @pytest.mark.asyncio
    async def test_score_risk_restatement(self, connector):
        """Restatement flag should produce high risk score."""
        cik_response = _make_response(
            {"0": {"cik_str": 999999, "ticker": "RISK", "title": "Risky Corp"}}
        )
        filings_response = _make_response(SAMPLE_SUBMISSIONS_GOING_CONCERN)

        mock_get = AsyncMock(side_effect=[cik_response, filings_response])
        with patch.object(connector.client, "get", mock_get):
            result = await connector.score_risk("RISK")
            assert "restatement" in result["risk_flags"]
            assert result["risk_score"] >= 0.5

    @pytest.mark.asyncio
    async def test_score_risk_late_filing(self, connector):
        """Very old filings should trigger late_filing flag."""
        old_date = (datetime.now(timezone.utc) - timedelta(days=400)).strftime("%Y-%m-%d")
        old_submissions = {
            "cik": "320193",
            "entityType": "operating",
            "name": "Apple Inc.",
            "tickers": ["AAPL"],
            "filings": {
                "recent": {
                    "accessionNumber": ["0000320193-23-000106"],
                    "filingDate": [old_date],
                    "form": ["10-K"],
                    "primaryDocument": ["old.htm"],
                    "primaryDocDescription": ["10-K Annual Report"],
                }
            },
        }
        cik_response = _make_response(SAMPLE_COMPANY_TICKERS)
        filings_response = _make_response(old_submissions)

        mock_get = AsyncMock(side_effect=[cik_response, filings_response])
        with patch.object(connector.client, "get", mock_get):
            result = await connector.score_risk("AAPL")
            assert "late_filing" in result["risk_flags"]

    @pytest.mark.asyncio
    async def test_score_risk_network_error(self, connector):
        """Network error should return empty dict."""
        with patch.object(
            connector.client, "get", new_callable=AsyncMock, side_effect=httpx.ConnectError("fail")
        ):
            result = await connector.score_risk("AAPL")
            assert result == {}

    @pytest.mark.asyncio
    async def test_score_risk_no_filings(self, connector):
        """No filings found should return empty dict."""
        cik_response = _make_response(SAMPLE_COMPANY_TICKERS)
        empty_submissions = {
            "cik": "320193",
            "filings": {
                "recent": {
                    "accessionNumber": [],
                    "filingDate": [],
                    "form": [],
                    "primaryDocument": [],
                    "primaryDocDescription": [],
                }
            },
        }
        filings_response = _make_response(empty_submissions)

        mock_get = AsyncMock(side_effect=[cik_response, filings_response])
        with patch.object(connector.client, "get", mock_get):
            result = await connector.score_risk("AAPL")
            assert result == {}

    @pytest.mark.asyncio
    async def test_score_risk_clamped(self, connector):
        """Risk score should always be between 0.0 and 1.0."""
        # Create filings with many risk flags to try to exceed 1.0
        risky_submissions = {
            "cik": "999999",
            "filings": {
                "recent": {
                    "accessionNumber": ["0001", "0002", "0003"],
                    "filingDate": [
                        (datetime.now(timezone.utc) - timedelta(days=500)).strftime("%Y-%m-%d"),
                        (datetime.now(timezone.utc) - timedelta(days=600)).strftime("%Y-%m-%d"),
                        (datetime.now(timezone.utc) - timedelta(days=700)).strftime("%Y-%m-%d"),
                    ],
                    "form": ["10-K", "8-K", "8-K"],
                    "primaryDocument": ["a.htm", "b.htm", "c.htm"],
                    "primaryDocDescription": [
                        "Going Concern - Material Weakness - Restatement",
                        "SEC Investigation Report",
                        "Delisting Risk Notice",
                    ],
                }
            },
        }
        cik_response = _make_response(
            {"0": {"cik_str": 999999, "ticker": "BAD", "title": "Bad Corp"}}
        )
        filings_response = _make_response(risky_submissions)

        mock_get = AsyncMock(side_effect=[cik_response, filings_response])
        with patch.object(connector.client, "get", mock_get):
            result = await connector.score_risk("BAD")
            assert result["risk_score"] <= 1.0
            assert result["risk_score"] >= 0.0

    @pytest.mark.asyncio
    async def test_score_risk_cached(self, connector):
        """Second call should use cache."""
        cik_response = _make_response(SAMPLE_COMPANY_TICKERS)
        filings_response = _make_response(SAMPLE_SUBMISSIONS)

        mock_get = AsyncMock(side_effect=[cik_response, filings_response])
        with patch.object(connector.client, "get", mock_get):
            result1 = await connector.score_risk("AAPL")

        mock_get2 = AsyncMock()
        with patch.object(connector.client, "get", mock_get2):
            result2 = await connector.score_risk("AAPL")
            assert result1 == result2
            mock_get2.assert_not_called()


# --- Test close ---


class TestClose:
    @pytest.mark.asyncio
    async def test_close(self, connector):
        with patch.object(connector.client, "aclose", new_callable=AsyncMock) as mock_close:
            await connector.close()
            mock_close.assert_called_once()


# --- Test days_since_filing calculation ---


class TestDaysSinceFiling:
    @pytest.mark.asyncio
    async def test_days_since_filing_recent(self, connector):
        """Recent filing should have small days_since_filing."""
        recent_date = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")
        submissions = {
            "cik": "320193",
            "filings": {
                "recent": {
                    "accessionNumber": ["0001"],
                    "filingDate": [recent_date],
                    "form": ["10-K"],
                    "primaryDocument": ["a.htm"],
                    "primaryDocDescription": ["10-K Annual Report"],
                }
            },
        }
        cik_response = _make_response(SAMPLE_COMPANY_TICKERS)
        filings_response = _make_response(submissions)

        mock_get = AsyncMock(side_effect=[cik_response, filings_response])
        with patch.object(connector.client, "get", mock_get):
            result = await connector.score_risk("AAPL")
            assert result["days_since_filing"] >= 4
            assert result["days_since_filing"] <= 6
