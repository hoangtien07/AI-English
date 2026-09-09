import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.core.config import Settings

BASE_PROD_KWARGS = dict(
    APP_ENV="production",
    DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
    SECRET_KEY="a-real-random-secret-key-value-with-32-chars",
    DEBUG=False,
    ENABLE_APP_CORS=True,
    # Settings.model_config reads a local .env file (pydantic-settings
    # env_file), so any field not pinned here falls back to whatever a
    # developer's machine-local, gitignored .env happens to contain —
    # e.g. a local ALLOWED_ORIGINS with http://localhost:5959 for dev.
    # Pin every field validate_production_security() inspects so this
    # test's outcome never depends on ambient local config.
    ALLOWED_ORIGINS="https://app.example,https://admin.example",
    CONTENT_AGENT_ENABLED=False,
    LEARNER_STATE_ENABLED=False,
    GOOGLE_CLIENT_ID="client-id",
    GOOGLE_ADMIN_CLIENT_ID="admin-client-id",
    FIREBASE_CREDENTIALS_FILE=None,
    SMTP_HOST=None,
    SMTP_USERNAME=None,
    SMTP_PASSWORD=None,
    SMTP_USE_TLS=True,
    SMTP_USE_SSL=False,
    EMAIL_FROM="noreply@example.com",
)


def test_comma_separated_allowed_hosts_is_parsed_from_environment(monkeypatch):
    """A conventional comma-list must not be JSON-decoded before validation."""
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("ALLOWED_HOSTS", "localhost, 127.0.0.1,api.local")

    settings = Settings(_env_file=None)

    assert settings.ALLOWED_HOSTS == ["localhost", "127.0.0.1", "api.local"]


def test_empty_previous_token_expiry_from_environment_is_none(monkeypatch):
    """An empty optional datetime is valid in local env files."""
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("LEARNER_STATE_INTERNAL_TOKEN_PREVIOUS_EXPIRES_AT", "")

    settings = Settings(_env_file=None)

    assert settings.LEARNER_STATE_INTERNAL_TOKEN_PREVIOUS_EXPIRES_AT is None


def test_short_secret_key_is_rejected_in_production():
    with pytest.raises(ValueError, match="at least 32 characters"):
        Settings(
            **{
                **BASE_PROD_KWARGS,
                "SECRET_KEY": "too-short",
                "CORS_ALLOW_ORIGIN_REGEX": _CLEAN_CORS_REGEX,
            }
        )


def test_unbounded_cors_regex_is_rejected_in_production():
    with pytest.raises(ValueError, match="Unbounded CORS regex"):
        Settings(
            **BASE_PROD_KWARGS,
            CORS_ALLOW_ORIGIN_REGEX=r"^https://.*\.example$",
        )


def test_devtunnels_regex_escaped_dot_is_rejected():
    """CORS_ALLOW_ORIGIN_REGEX values are regexes, so a real dev-tunnel
    domain shows up as "devtunnels\\.ms", not the literal "devtunnels.ms" —
    the check must still catch it."""
    with pytest.raises(ValueError, match="development tunnel"):
        Settings(
            **BASE_PROD_KWARGS,
            CORS_ALLOW_ORIGIN_REGEX=r"^https://demo\.devtunnels\.ms$",
        )


def test_github_dev_regex_escaped_dot_is_rejected():
    with pytest.raises(ValueError, match="development tunnel"):
        Settings(
            **BASE_PROD_KWARGS,
            CORS_ALLOW_ORIGIN_REGEX=r"^https://workspace\.github\.dev$",
        )


def test_localhost_regex_is_rejected_in_production():
    with pytest.raises(ValueError, match="Localhost CORS regex"):
        Settings(
            **BASE_PROD_KWARGS,
            CORS_ALLOW_ORIGIN_REGEX=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        )


def test_clean_production_cors_regex_is_accepted():
    settings = Settings(
        **BASE_PROD_KWARGS,
        CORS_ALLOW_ORIGIN_REGEX=r"^https://([a-zA-Z0-9-]+\.)?example$",
    )
    assert settings.is_production


@pytest.mark.parametrize(
    "origin",
    ["http://localhost:57393", "http://127.0.0.1:42117"],
)
def test_local_cors_regex_allows_ephemeral_ports(origin):
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["POST"],
        allow_headers=["Content-Type"],
    )

    response = TestClient(app).options(
        "/register",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_local_cors_regex_denies_external_origin():
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["POST"],
        allow_headers=["Content-Type"],
    )

    response = TestClient(app).options(
        "/register",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


_CLEAN_CORS_REGEX = r"^https://([a-zA-Z0-9-]+\.)?example$"


def test_firebase_credentials_file_inside_repo_is_rejected():
    kwargs = {
        **BASE_PROD_KWARGS,
        "CORS_ALLOW_ORIGIN_REGEX": _CLEAN_CORS_REGEX,
        "FIREBASE_CREDENTIALS_FILE": "./firebase-service-account.json",
    }
    with pytest.raises(ValueError, match="FIREBASE_CREDENTIALS_FILE"):
        Settings(**kwargs)


def test_firebase_credentials_file_outside_repo_is_accepted():
    kwargs = {
        **BASE_PROD_KWARGS,
        "CORS_ALLOW_ORIGIN_REGEX": _CLEAN_CORS_REGEX,
        "FIREBASE_CREDENTIALS_FILE": "/run/secrets/firebase.json",
    }
    settings = Settings(**kwargs)
    assert settings.is_production


def test_admin_allowlists_normalize_case_and_require_exact_addresses():
    settings = Settings(
        _env_file=None,
        APP_ENV="testing",
        DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
        SECRET_KEY="test-secret-key",
        SMTP_HOST="SMTP.GMAIL.COM",
        SMTP_USERNAME=" Sender@Example.com ",
        EMAIL_FROM=" SENDER@example.com ",
        ADMIN_EMAIL_WHITELIST="  Admin@Example.com,ADMIN@example.com ",
        SUPER_ADMIN_EMAIL_WHITELIST=" Owner@Example.com ",
    )

    assert settings.SMTP_HOST == "smtp.gmail.com"
    assert settings.SMTP_USERNAME == "sender@example.com"
    assert settings.EMAIL_FROM == "sender@example.com"
    assert settings.admin_email_whitelist == ["admin@example.com"]
    assert settings.super_admin_email_whitelist == ["owner@example.com"]
    assert settings.get_admin_role_for_email("OWNER@EXAMPLE.COM") == "super_admin"
    assert settings.get_admin_role_for_email("admin@example.com") == "admin"
    assert settings.get_admin_role_for_email("person@example.com") is None


@pytest.mark.parametrize("allowlist", ["*@example.com", "@example.com", "not-an-email"])
def test_admin_allowlists_reject_domain_wide_or_invalid_entries(allowlist):
    with pytest.raises(ValueError, match="allowlists"):
        Settings(
            _env_file=None,
            APP_ENV="testing",
            DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
            SECRET_KEY="test-secret-key",
            SUPER_ADMIN_EMAIL_WHITELIST=allowlist,
        )


def test_gmail_requires_starttls_on_port_587_in_production():
    with pytest.raises(ValueError, match="Gmail SMTP requires STARTTLS"):
        Settings(
            **{
                **BASE_PROD_KWARGS,
                "CORS_ALLOW_ORIGIN_REGEX": _CLEAN_CORS_REGEX,
                "SMTP_HOST": "smtp.gmail.com",
                "SMTP_PORT": 465,
                "SMTP_USERNAME": "sender@example.com",
                "SMTP_PASSWORD": "app-password",
                "SMTP_USE_TLS": False,
                "SMTP_USE_SSL": True,
                "EMAIL_FROM": "sender@example.com",
            },
        )


def test_smtp_timeout_is_bounded():
    with pytest.raises(ValueError, match="less than or equal to 30"):
        Settings(
            _env_file=None,
            APP_ENV="testing",
            DATABASE_URL="postgresql+asyncpg://u:p@localhost/db",
            SECRET_KEY="test-secret-key",
            SMTP_TIMEOUT=31,
        )
