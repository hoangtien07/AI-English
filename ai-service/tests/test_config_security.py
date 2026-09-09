import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from api.core.config import Settings


LOCAL_CORS_REGEX = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"


def test_localhost_regex_is_rejected_in_production():
    with pytest.raises(ValueError, match="Localhost CORS regex"):
        Settings(
            _env_file=None,
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="x" * 32,
            ALLOWED_ORIGINS=["https://app.example"],
            CORS_ALLOW_ORIGIN_REGEX=LOCAL_CORS_REGEX,
        )


def test_unbounded_cors_regex_is_rejected_in_production():
    with pytest.raises(ValueError, match="Unbounded CORS regex"):
        Settings(
            _env_file=None,
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="x" * 32,
            ALLOWED_ORIGINS=["https://app.example"],
            CORS_ALLOW_ORIGIN_REGEX=r"^https://.*\.example$",
        )


@pytest.mark.parametrize(
    "origin",
    ["http://localhost:57393", "http://127.0.0.1:42117"],
)
def test_local_cors_regex_allows_ephemeral_ports(origin):
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[],
        allow_origin_regex=LOCAL_CORS_REGEX,
        allow_credentials=True,
        allow_methods=["POST"],
        allow_headers=["Content-Type"],
    )

    response = TestClient(app).options(
        "/embed",
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
        allow_origin_regex=LOCAL_CORS_REGEX,
        allow_credentials=True,
        allow_methods=["POST"],
        allow_headers=["Content-Type"],
    )

    response = TestClient(app).options(
        "/embed",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
