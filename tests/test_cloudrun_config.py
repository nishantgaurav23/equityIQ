"""Tests for S12.3 -- Cloud Run service configuration."""

import pathlib

import yaml

CLOUDRUN_PATH = pathlib.Path(__file__).resolve().parent.parent / "deploy" / "cloudrun.yaml"


def _load_config():
    """Load and parse the Cloud Run YAML config."""
    assert CLOUDRUN_PATH.exists(), f"deploy/cloudrun.yaml not found at {CLOUDRUN_PATH}"
    with open(CLOUDRUN_PATH) as f:
        return yaml.safe_load(f)


class TestCloudRunYamlExists:
    def test_cloudrun_yaml_exists(self):
        assert CLOUDRUN_PATH.exists()

    def test_cloudrun_yaml_not_empty(self):
        assert CLOUDRUN_PATH.stat().st_size > 0


class TestCloudRunYamlValid:
    def test_api_version(self):
        config = _load_config()
        assert config["apiVersion"] == "serving.knative.dev/v1"

    def test_kind_is_service(self):
        config = _load_config()
        assert config["kind"] == "Service"

    def test_has_metadata(self):
        config = _load_config()
        assert "metadata" in config
        assert "name" in config["metadata"]

    def test_service_name(self):
        config = _load_config()
        assert config["metadata"]["name"] == "equityiq"


class TestResourceLimits:
    def test_memory_limit(self):
        config = _load_config()
        container = config["spec"]["template"]["spec"]["containers"][0]
        assert container["resources"]["limits"]["memory"] == "1Gi"

    def test_cpu_limit(self):
        config = _load_config()
        container = config["spec"]["template"]["spec"]["containers"][0]
        assert container["resources"]["limits"]["cpu"] == "1"


class TestAutoScaling:
    def _get_template_annotations(self):
        config = _load_config()
        return config["spec"]["template"]["metadata"]["annotations"]

    def test_min_scale(self):
        annotations = self._get_template_annotations()
        assert annotations["autoscaling.knative.dev/minScale"] == "0"

    def test_max_scale(self):
        annotations = self._get_template_annotations()
        assert annotations["autoscaling.knative.dev/maxScale"] == "4"


class TestNetworking:
    def test_container_port(self):
        config = _load_config()
        container = config["spec"]["template"]["spec"]["containers"][0]
        ports = container["ports"]
        assert any(p["containerPort"] == 8080 for p in ports)

    def test_concurrency(self):
        config = _load_config()
        assert config["spec"]["template"]["spec"]["containerConcurrency"] == 80


class TestTimeout:
    def test_request_timeout(self):
        config = _load_config()
        annotations = config["spec"]["template"]["metadata"]["annotations"]
        assert annotations["run.googleapis.com/request-timeout"] == "300"


class TestSecretReferences:
    REQUIRED_SECRETS = [
        "GOOGLE_API_KEY",
        "POLYGON_API_KEY",
        "FRED_API_KEY",
        "NEWS_API_KEY",
        "SERPER_API_KEY",
        "TAVILY_API_KEY",
    ]

    def _get_env_vars(self):
        config = _load_config()
        container = config["spec"]["template"]["spec"]["containers"][0]
        return container.get("env", [])

    def test_all_secrets_referenced(self):
        env_vars = self._get_env_vars()
        env_names = [e["name"] for e in env_vars]
        for secret in self.REQUIRED_SECRETS:
            assert secret in env_names, f"Missing secret reference: {secret}"

    def test_secrets_use_secret_key_ref(self):
        env_vars = self._get_env_vars()
        secret_envs = [e for e in env_vars if e["name"] in self.REQUIRED_SECRETS]
        for env in secret_envs:
            assert "valueFrom" in env, f"{env['name']} missing valueFrom"
            assert "secretKeyRef" in env["valueFrom"], f"{env['name']} missing secretKeyRef"


class TestStartupProbe:
    def test_startup_probe_exists(self):
        config = _load_config()
        container = config["spec"]["template"]["spec"]["containers"][0]
        assert "startupProbe" in container

    def test_startup_probe_path(self):
        config = _load_config()
        container = config["spec"]["template"]["spec"]["containers"][0]
        probe = container["startupProbe"]
        assert probe["httpGet"]["path"] == "/health"

    def test_startup_probe_port(self):
        config = _load_config()
        container = config["spec"]["template"]["spec"]["containers"][0]
        probe = container["startupProbe"]
        assert probe["httpGet"]["port"] == 8080


class TestImageReference:
    def test_image_uses_artifact_registry(self):
        config = _load_config()
        container = config["spec"]["template"]["spec"]["containers"][0]
        image = container["image"]
        assert "docker.pkg.dev" in image

    def test_image_contains_equityiq(self):
        config = _load_config()
        container = config["spec"]["template"]["spec"]["containers"][0]
        image = container["image"]
        assert "equityiq" in image
