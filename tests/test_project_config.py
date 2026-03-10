"""Tests for S1.1 -- Dependency Declaration (pyproject.toml + .env.example)."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# ── FR-1: pyproject.toml existence and validity ─────────────────────────────


def test_pyproject_exists():
    assert (ROOT / "pyproject.toml").exists(), "pyproject.toml must exist at project root"


def test_pyproject_valid_toml():
    with open(ROOT / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    assert "project" in data, "pyproject.toml must have a [project] section"


def test_pyproject_project_metadata():
    with open(ROOT / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    proj = data["project"]
    assert proj["name"] == "equityiq"
    assert "version" in proj


def test_pyproject_python_version():
    with open(ROOT / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    requires = data["project"]["requires-python"]
    assert "3.12" in requires, "requires-python must reference 3.12"


EXPECTED_RUNTIME_DEPS = [
    "google-adk",
    "google-generativeai",
    "fastapi",
    "uvicorn",
    "pydantic",
    "pydantic-settings",
    "httpx",
    "aiohttp",
    "cachetools",
    "aiosqlite",
    "xgboost",
    "scikit-learn",
    "pandas",
    "numpy",
    "python-dotenv",
    "beautifulsoup4",
    "lxml",
    "colorlog",
]


def test_pyproject_has_runtime_deps():
    with open(ROOT / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    deps = [
        d.split(">=")[0].split("~=")[0].split("<")[0].strip().lower()
        for d in data["project"]["dependencies"]
    ]
    for pkg in EXPECTED_RUNTIME_DEPS:
        assert pkg.lower() in deps, f"Missing runtime dependency: {pkg}"


EXPECTED_DEV_DEPS = ["pytest", "pytest-asyncio", "ruff", "pytest-mock"]


def test_pyproject_has_dev_deps():
    with open(ROOT / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    opt = data["project"]["optional-dependencies"]
    assert "dev" in opt, "Must have [project.optional-dependencies] dev group"
    dev_deps = [d.split(">=")[0].split("~=")[0].split("<")[0].strip().lower() for d in opt["dev"]]
    for pkg in EXPECTED_DEV_DEPS:
        assert pkg.lower() in dev_deps, f"Missing dev dependency: {pkg}"


# ── FR-2: Ruff configuration ────────────────────────────────────────────────


def test_ruff_config():
    with open(ROOT / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    ruff = data["tool"]["ruff"]
    assert ruff["line-length"] == 100
    assert ruff["target-version"] == "py312"


# ── FR-3: Pytest configuration ──────────────────────────────────────────────


def test_pytest_config():
    with open(ROOT / "pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    pytest_opts = data["tool"]["pytest"]["ini_options"]
    assert pytest_opts["asyncio_mode"] == "auto"
    assert "tests" in pytest_opts["testpaths"]


# ── FR-4: .env.example ──────────────────────────────────────────────────────


def test_env_example_exists():
    assert (ROOT / ".env.example").exists(), ".env.example must exist"


EXPECTED_ENV_VARS = [
    "GOOGLE_API_KEY",
    "POLYGON_API_KEY",
    "FRED_API_KEY",
    "NEWS_API_KEY",
    "ENVIRONMENT",
    "SQLITE_DB_PATH",
    "GCP_PROJECT_ID",
    "GCP_REGION",
    "LOG_LEVEL",
]


def test_env_example_has_all_vars():
    content = (ROOT / ".env.example").read_text()
    for var in EXPECTED_ENV_VARS:
        assert var in content, f".env.example missing variable: {var}"


# ── FR-5: .gitignore ────────────────────────────────────────────────────────


def test_gitignore_excludes_env():
    content = (ROOT / ".gitignore").read_text()
    lines = [line.strip() for line in content.splitlines()]
    assert ".env" in lines or "*.env" in lines, ".env must be in .gitignore"
