"""Exact-route CORS preflight regressions for local authentication."""

from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.testclient import TestClient

from app.core.config import Settings, settings
from app.main import app


def test_register_preflight_allows_configured_origin_on_real_application():
    """The application stack, not a stand-alone middleware, permits registration."""
    origin = settings.cors_origins[0]

    response = TestClient(app).options(
        "/api/v1/auth/register",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "POST" in response.headers["access-control-allow-methods"]


def test_register_preflight_denies_unconfigured_origin_on_real_application():
    """The exact registration endpoint must not become a cross-origin signup API."""
    response = TestClient(app).options(
        "/api/v1/auth/register",
        headers={
            "Origin": "https://untrusted.invalid",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_comma_separated_allowed_hosts_are_enforced():
    """The same comma-list accepted by settings is honored by host middleware."""
    local_settings = Settings(
        _env_file=None,
        APP_ENV="testing",
        DATABASE_URL="sqlite+aiosqlite:///./host-policy-test.sqlite3",
        SECRET_KEY="test-secret-key",
        ALLOWED_HOSTS="localhost,127.0.0.1",
    )
    policy_app = FastAPI()
    policy_app.add_middleware(TrustedHostMiddleware, allowed_hosts=local_settings.ALLOWED_HOSTS)
    client = TestClient(policy_app)

    assert client.get("/", headers={"Host": "localhost"}).status_code == 404
    assert client.get("/", headers={"Host": "127.0.0.1:8000"}).status_code == 404
    assert client.get("/", headers={"Host": "untrusted.invalid"}).status_code == 400
