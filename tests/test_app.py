"""Tests for app.py -- S1.4 FastAPI App Skeleton."""

from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestCreateApp:
    """Test the create_app() factory function."""

    def test_create_app_returns_fastapi(self):
        from app import create_app

        app = create_app()
        assert isinstance(app, FastAPI)

    def test_app_title_and_version(self):
        from app import create_app

        app = create_app()
        assert app.title == "EquityIQ"
        assert app.version == "0.1.0"

    def test_app_has_lifespan(self):
        from app import create_app

        app = create_app()
        assert app.router.lifespan_context is not None


class TestHealthEndpoint:
    """Test GET /health endpoint."""

    def test_health_returns_200(self):
        from app import create_app

        app = create_app()
        with TestClient(app) as client:
            resp = client.get("/health")
            assert resp.status_code == 200

    def test_health_returns_status_ok(self):
        from app import create_app

        app = create_app()
        with TestClient(app) as client:
            data = client.get("/health").json()
            assert data["status"] == "ok"

    def test_health_has_environment(self):
        from app import create_app

        app = create_app()
        with TestClient(app) as client:
            data = client.get("/health").json()
            assert "environment" in data

    def test_health_has_version(self):
        from app import create_app

        app = create_app()
        with TestClient(app) as client:
            data = client.get("/health").json()
            assert data["version"] == "0.1.0"


class TestModuleLevelApp:
    """Test module-level app instance."""

    def test_module_level_app_exists(self):
        from app import app

        assert isinstance(app, FastAPI)
