"""Tests for config/settings.py -- S1.3 Pydantic Settings Configuration."""

from pydantic_settings import BaseSettings


class TestSettingsClass:
    """Test that Settings class exists and has correct structure."""

    def test_settings_class_exists(self):
        from config.settings import Settings

        assert Settings is not None

    def test_settings_is_base_settings(self):
        from config.settings import Settings

        assert issubclass(Settings, BaseSettings)

    def test_settings_has_api_key_fields(self):
        from config.settings import Settings

        fields = Settings.model_fields
        for key in ["GOOGLE_API_KEY", "POLYGON_API_KEY", "FRED_API_KEY", "NEWS_API_KEY"]:
            assert key in fields, f"Missing field: {key}"

    def test_settings_has_infra_fields(self):
        from config.settings import Settings

        fields = Settings.model_fields
        for key in [
            "ENVIRONMENT",
            "SQLITE_DB_PATH",
            "GCP_PROJECT_ID",
            "GCP_REGION",
            "LOG_LEVEL",
        ]:
            assert key in fields, f"Missing field: {key}"

    def test_settings_has_agent_url_fields(self):
        from config.settings import Settings

        fields = Settings.model_fields
        expected = {
            "VALUATION_AGENT_URL": "http://localhost:8001",
            "MOMENTUM_AGENT_URL": "http://localhost:8002",
            "PULSE_AGENT_URL": "http://localhost:8003",
            "ECONOMY_AGENT_URL": "http://localhost:8004",
            "COMPLIANCE_AGENT_URL": "http://localhost:8005",
            "SYNTHESIZER_AGENT_URL": "http://localhost:8006",
            "RISK_AGENT_URL": "http://localhost:8007",
        }
        for key in expected:
            assert key in fields, f"Missing field: {key}"


class TestSettingsDefaults:
    """Test default values when no env vars are set."""

    def test_settings_default_values(self, monkeypatch):
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        monkeypatch.delenv("SQLITE_DB_PATH", raising=False)
        monkeypatch.delenv("GCP_REGION", raising=False)
        s = self._make_settings(monkeypatch)
        assert s.ENVIRONMENT == "local"
        assert s.LOG_LEVEL == "INFO"
        assert s.SQLITE_DB_PATH == "data/equityiq.db"
        assert s.GCP_REGION == "us-central1"

    def test_settings_api_keys_default_empty(self, monkeypatch):
        s = self._make_settings(monkeypatch)
        assert s.GOOGLE_API_KEY == ""
        assert s.POLYGON_API_KEY == ""
        assert s.FRED_API_KEY == ""
        assert s.NEWS_API_KEY == ""

    def test_agent_url_defaults(self, monkeypatch):
        s = self._make_settings(monkeypatch)
        assert s.VALUATION_AGENT_URL == "http://localhost:8001"
        assert s.MOMENTUM_AGENT_URL == "http://localhost:8002"
        assert s.PULSE_AGENT_URL == "http://localhost:8003"
        assert s.ECONOMY_AGENT_URL == "http://localhost:8004"
        assert s.COMPLIANCE_AGENT_URL == "http://localhost:8005"
        assert s.SYNTHESIZER_AGENT_URL == "http://localhost:8006"
        assert s.RISK_AGENT_URL == "http://localhost:8007"

    @staticmethod
    def _make_settings(monkeypatch):
        """Create Settings without reading .env file."""
        from config.settings import Settings

        # Clear all API keys that might be in .env
        for key in [
            "GOOGLE_API_KEY", "POLYGON_API_KEY", "FRED_API_KEY", "NEWS_API_KEY",
            "GCP_PROJECT_ID",
        ]:
            monkeypatch.delenv(key, raising=False)
        return Settings(_env_file=None)


class TestIsProductionProperty:
    """Test the is_production computed property."""

    def test_is_production_local(self):
        from config.settings import Settings

        s = Settings(ENVIRONMENT="local", _env_file=None)
        assert s.is_production is False

    def test_is_production_production(self):
        from config.settings import Settings

        s = Settings(ENVIRONMENT="production", _env_file=None)
        assert s.is_production is True


class TestGetSettings:
    """Test the get_settings() singleton accessor."""

    def test_get_settings_returns_settings(self):
        from config.settings import Settings, get_settings

        get_settings.cache_clear()
        result = get_settings()
        assert isinstance(result, Settings)

    def test_get_settings_is_cached(self):
        from config.settings import get_settings

        get_settings.cache_clear()
        a = get_settings()
        b = get_settings()
        assert a is b

    def test_settings_from_env_vars(self, monkeypatch):
        from config.settings import Settings

        monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        s = Settings(_env_file=None)
        assert s.GOOGLE_API_KEY == "test-google-key"
        assert s.ENVIRONMENT == "production"
        assert s.LOG_LEVEL == "DEBUG"


class TestConfigInit:
    """Test that config/__init__.py re-exports correctly."""

    def test_config_init_exports(self):
        from config import Settings, get_settings

        assert Settings is not None
        assert callable(get_settings)
