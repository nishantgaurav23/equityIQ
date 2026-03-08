"""Tests for agents/a2a_server.py -- A2A protocol server factory."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from config.data_contracts import AnalystReport

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_mock_agent(
    name: str = "valuation_scout",
    report: AnalystReport | None = None,
) -> MagicMock:
    """Create a mock BaseAnalystAgent."""
    agent = MagicMock()
    agent.name = name
    agent.get_agent_card.return_value = {
        "name": name,
        "description": "Mock agent for testing.",
        "url": "http://localhost:8001",
        "capabilities": ["get_fundamentals"],
        "output_schema": "ValuationReport",
    }
    if report is None:
        report = AnalystReport(
            ticker="AAPL",
            agent_name=name,
            signal="BUY",
            confidence=0.85,
            reasoning="Strong fundamentals.",
        )
    agent.analyze = AsyncMock(return_value=report)
    return agent


def _make_jsonrpc_request(
    method: str = "tasks/send",
    task_id: str = "task-456",
    ticker: str = "AAPL",
    req_id: str | int = "req-123",
) -> dict:
    """Build a valid JSONRPC request dict."""
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
        "params": {
            "id": task_id,
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": ticker}],
            },
        },
    }


@pytest.fixture
def mock_agent():
    return _make_mock_agent()


@pytest.fixture
def app(mock_agent):
    from agents.a2a_server import create_agent_server

    return create_agent_server(mock_agent)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Agent Card Endpoint
# ---------------------------------------------------------------------------


class TestAgentCard:
    async def test_agent_card_endpoint(self, client: AsyncClient):
        resp = await client.get("/.well-known/agent-card.json")
        assert resp.status_code == 200

    async def test_agent_card_has_required_fields(self, client: AsyncClient):
        resp = await client.get("/.well-known/agent-card.json")
        data = resp.json()
        for field in ("name", "description", "url", "capabilities", "output_schema"):
            assert field in data, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# Health Endpoint
# ---------------------------------------------------------------------------


class TestHealth:
    async def test_health_endpoint(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200

    async def test_health_response(self, client: AsyncClient):
        resp = await client.get("/health")
        data = resp.json()
        assert data["status"] == "ok"
        assert data["agent"] == "valuation_scout"


# ---------------------------------------------------------------------------
# A2A JSONRPC -- tasks/send success
# ---------------------------------------------------------------------------


class TestA2ATasksSend:
    async def test_a2a_tasks_send_success(self, client: AsyncClient, mock_agent):
        body = _make_jsonrpc_request()
        resp = await client.post("/a2a", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert "result" in data
        mock_agent.analyze.assert_awaited_once_with("AAPL")

    async def test_a2a_tasks_send_result_structure(self, client: AsyncClient):
        body = _make_jsonrpc_request()
        resp = await client.post("/a2a", json=body)
        result = resp.json()["result"]
        assert result["id"] == "task-456"
        assert result["status"]["state"] == "completed"
        assert "artifacts" in result
        assert len(result["artifacts"]) > 0
        assert "parts" in result["artifacts"][0]

    async def test_a2a_tasks_send_artifact_contains_report(self, client: AsyncClient):
        body = _make_jsonrpc_request()
        resp = await client.post("/a2a", json=body)
        artifact = resp.json()["result"]["artifacts"][0]
        text_part = artifact["parts"][0]["text"]
        report_data = json.loads(text_part)
        assert report_data["ticker"] == "AAPL"
        assert report_data["signal"] == "BUY"

    async def test_a2a_tasks_send_preserves_task_id(self, client: AsyncClient):
        body = _make_jsonrpc_request(task_id="my-custom-id")
        resp = await client.post("/a2a", json=body)
        assert resp.json()["result"]["id"] == "my-custom-id"

    async def test_a2a_tasks_send_preserves_request_id(self, client: AsyncClient):
        body = _make_jsonrpc_request(req_id=42)
        resp = await client.post("/a2a", json=body)
        assert resp.json()["id"] == 42


# ---------------------------------------------------------------------------
# A2A JSONRPC -- error cases
# ---------------------------------------------------------------------------


class TestA2AErrors:
    async def test_a2a_unknown_method(self, client: AsyncClient):
        body = _make_jsonrpc_request(method="unknown/foo")
        resp = await client.post("/a2a", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == -32601

    async def test_a2a_invalid_request_body(self, client: AsyncClient):
        resp = await client.post("/a2a", json={"bad": "data"})
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == -32600

    async def test_a2a_missing_params(self, client: AsyncClient):
        body = {"jsonrpc": "2.0", "id": "req-1", "method": "tasks/send"}
        resp = await client.post("/a2a", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == -32600

    async def test_a2a_missing_text_in_parts(self, client: AsyncClient):
        body = {
            "jsonrpc": "2.0",
            "id": "req-1",
            "method": "tasks/send",
            "params": {
                "id": "task-1",
                "message": {"role": "user", "parts": []},
            },
        }
        resp = await client.post("/a2a", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == -32602


# ---------------------------------------------------------------------------
# A2A -- agent fallback
# ---------------------------------------------------------------------------


class TestA2AFallback:
    async def test_a2a_agent_fallback_still_completes(self, client: AsyncClient, mock_agent):
        fallback = AnalystReport(
            ticker="AAPL",
            agent_name="valuation_scout",
            signal="HOLD",
            confidence=0.0,
            reasoning="Analysis failed: timeout",
        )
        mock_agent.analyze = AsyncMock(return_value=fallback)
        body = _make_jsonrpc_request()
        resp = await client.post("/a2a", json=body)
        result = resp.json()["result"]
        assert result["status"]["state"] == "completed"
        text = result["artifacts"][0]["parts"][0]["text"]
        report = json.loads(text)
        assert report["signal"] == "HOLD"
        assert report["confidence"] == 0.0


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class TestFactory:
    def test_create_agent_server_returns_fastapi(self):
        from agents.a2a_server import create_agent_server

        mock = _make_mock_agent()
        server = create_agent_server(mock)
        assert isinstance(server, FastAPI)

    def test_server_reusable_with_different_agents(self):
        from agents.a2a_server import create_agent_server

        agent1 = _make_mock_agent(name="valuation_scout")
        agent2 = _make_mock_agent(name="momentum_tracker")
        server1 = create_agent_server(agent1)
        server2 = create_agent_server(agent2)
        assert isinstance(server1, FastAPI)
        assert isinstance(server2, FastAPI)
        assert server1 is not server2
