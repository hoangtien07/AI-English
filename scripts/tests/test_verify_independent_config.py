import importlib.util
import tempfile
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "verify_independent_config",
    Path(__file__).parent.parent / "security" / "verify_independent_config.py",
)
sentinel = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sentinel)

_FIREBASE_WEB_API_KEY = "AIza" + "A" * 20


def _violations_in_temporary_repo(relative: str, content: str) -> list[str]:
    """Exercise path-sensitive sentinel behavior without changing the real tree."""
    with tempfile.TemporaryDirectory() as temporary:
        original_root = sentinel.ROOT
        sentinel.ROOT = Path(temporary)
        try:
            candidate = sentinel.ROOT / relative
            candidate.parent.mkdir(parents=True)
            candidate.write_text(content)
            return sentinel.violations_for(candidate)
        finally:
            sentinel.ROOT = original_root


def test_detects_legacy_runtime_marker_without_exposing_content():
    with tempfile.TemporaryDirectory() as temporary:
        candidate = Path(temporary) / "runtime.env"
        candidate.write_text("API_BASE_URL=https://api." + "lexilingo.me/api/v1\n")
        assert "legacy runtime marker" in sentinel.violations_for(candidate)


def test_detects_obvious_provider_credential_literal():
    with tempfile.TemporaryDirectory() as temporary:
        candidate = Path(temporary) / "runtime.env"
        candidate.write_text("GEMINI_API_KEY=not-a-placeholder-value\n")
        assert "provider credential assignment" in sentinel.violations_for(candidate)


def test_allows_firebase_web_api_key_only_in_owned_flutter_options_field():
    violations = _violations_in_temporary_repo(
        "flutter-app/lib/firebase_options.dart",
        "static const FirebaseOptions web = FirebaseOptions(\n"
        f"  apiKey: '{_FIREBASE_WEB_API_KEY}',\n"
        ");\n",
    )
    assert violations == []


def test_allows_firebase_web_api_key_only_in_owned_service_worker_field():
    violations = _violations_in_temporary_repo(
        "flutter-app/web/firebase-messaging-sw.js",
        "const firebaseConfig = {\n"
        f'  apiKey: "{_FIREBASE_WEB_API_KEY}",\n'
        "};\n",
    )
    assert violations == []


def test_rejects_firebase_web_api_key_outside_owned_config_locations():
    violations = _violations_in_temporary_repo(
        "flutter-app/lib/unrelated.dart",
        f"const apiKey = '{_FIREBASE_WEB_API_KEY}';\n",
    )
    assert "credential literal" in violations


def test_rejects_firebase_web_api_key_in_an_unapproved_config_field():
    violations = _violations_in_temporary_repo(
        "flutter-app/lib/firebase_options.dart",
        "static const FirebaseOptions web = FirebaseOptions(\n"
        f"  clientSecret: '{_FIREBASE_WEB_API_KEY}',\n"
        ");\n",
    )
    assert "credential literal" in violations


def test_detects_private_oauth_client_secret_assignment():
    with tempfile.TemporaryDirectory() as temporary:
        candidate = Path(temporary) / "runtime.env"
        candidate.write_text("GOOGLE_CLIENT_SECRET=private-oauth-secret\n")
        assert "provider credential assignment" in sentinel.violations_for(candidate)


def test_detects_service_account_private_key_assignment():
    with tempfile.TemporaryDirectory() as temporary:
        candidate = Path(temporary) / "service-account.yaml"
        candidate.write_text('private_key: "service-account-private-value"\n')
        assert "provider credential assignment" in sentinel.violations_for(candidate)


def test_detects_smtp_credential_assignment():
    with tempfile.TemporaryDirectory() as temporary:
        candidate = Path(temporary) / "runtime.env"
        candidate.write_text("SMTP_PASSWORD=private-smtp-password\n")
        assert "provider credential assignment" in sentinel.violations_for(candidate)


def test_detects_gemini_api_key_outside_firebase_web_config():
    with tempfile.TemporaryDirectory() as temporary:
        candidate = Path(temporary) / "runtime.env"
        candidate.write_text(f"GEMINI_API_KEY={_FIREBASE_WEB_API_KEY}\n")
        assert "credential literal" in sentinel.violations_for(candidate)


def test_allows_environment_interpolation_for_provider_credentials():
    with tempfile.TemporaryDirectory() as temporary:
        candidate = Path(temporary) / "runtime.env"
        candidate.write_text("GEMINI_API_KEY=${GEMINI_API_KEY}\n")
        assert sentinel.violations_for(candidate) == []


def test_allows_nested_yaml_environment_interpolation_for_provider_credentials():
    with tempfile.TemporaryDirectory() as temporary:
        candidate = Path(temporary) / "runtime.yaml"
        candidate.write_text("gemini:\n  api_key: ${GEMINI_API_KEY}\n")
        assert sentinel.violations_for(candidate) == []


def test_detects_nested_yaml_provider_credential_literal():
    with tempfile.TemporaryDirectory() as temporary:
        candidate = Path(temporary) / "runtime.yaml"
        candidate.write_text("gemini:\n  api_key: not-a-placeholder-value\n")
        assert "provider credential assignment" in sentinel.violations_for(candidate)


def test_ignores_non_credential_provider_settings():
    with tempfile.TemporaryDirectory() as temporary:
        candidate = Path(temporary) / "runtime.yaml"
        candidate.write_text("GROQ_REQUIRE_SEVEN_KEYS: true\nGROQ_MODEL: model-name\n")
        assert sentinel.violations_for(candidate) == []


def test_excludes_non_executable_reference_files():
    for relative in (
        "admin-service/QUICKSTART.md",
        "admin-service/.gitignore",
        "admin-service/public/.well-known/security.txt",
        "flutter-app/web/.well-known/security.txt",
    ):
        assert not sentinel.should_scan(sentinel.ROOT / relative)


if __name__ == "__main__":
    test_detects_legacy_runtime_marker_without_exposing_content()
    test_detects_obvious_provider_credential_literal()
    test_allows_firebase_web_api_key_only_in_owned_flutter_options_field()
    test_allows_firebase_web_api_key_only_in_owned_service_worker_field()
    test_rejects_firebase_web_api_key_outside_owned_config_locations()
    test_rejects_firebase_web_api_key_in_an_unapproved_config_field()
    test_detects_private_oauth_client_secret_assignment()
    test_detects_service_account_private_key_assignment()
    test_detects_smtp_credential_assignment()
    test_detects_gemini_api_key_outside_firebase_web_config()
    test_allows_environment_interpolation_for_provider_credentials()
    test_allows_nested_yaml_environment_interpolation_for_provider_credentials()
    test_detects_nested_yaml_provider_credential_literal()
    test_ignores_non_credential_provider_settings()
    test_excludes_non_executable_reference_files()
    print("verify_independent_config tests passed.")
