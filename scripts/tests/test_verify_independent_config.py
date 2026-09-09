import importlib.util
import tempfile
from pathlib import Path


SPEC = importlib.util.spec_from_file_location(
    "verify_independent_config",
    Path(__file__).parent.parent / "security" / "verify_independent_config.py",
)
sentinel = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sentinel)


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
    test_allows_environment_interpolation_for_provider_credentials()
    test_allows_nested_yaml_environment_interpolation_for_provider_credentials()
    test_detects_nested_yaml_provider_credential_literal()
    test_ignores_non_credential_provider_settings()
    test_excludes_non_executable_reference_files()
    print("verify_independent_config tests passed.")
