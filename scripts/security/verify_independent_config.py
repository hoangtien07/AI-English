#!/usr/bin/env python3
"""Reject legacy runtime coupling and obvious private credentials in deployable sources.

This is a current-tree guard, not a history rewrite tool. Documentation, licenses,
and test/reference fixtures are deliberately excluded because they may describe
legacy systems without being executable deployment input.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGETS = (
    ".github",
    "admin-service",
    "deploy",
    "docker-compose.yml",
    "flutter-app",
    "gateway",
    "infra",
    "mcp-server",
    "scripts",
    ".env.production.example",
)
EXCLUDED_PARTS = {
    ".git",
    ".dart_tool",
    ".pytest_cache",
    ".pytest-tmp",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "docs",
    "node_modules",
    "test",
    "tests",
    "venv",
}
REFERENCE_FILES = {
    Path("scripts/security/verify_independent_config.py"),
    Path("scripts/tests/test_verify_independent_config.py"),
}
LEGACY_RUNTIME_MARKERS = (
    "api.lexilingo.me",
    "ai.lexilingo.me",
    "admin.lexilingo.me",
    "www.lexilingo.me",
    "https://lexilingo.me",
    "lexilingo-88492",
    "lexilingo-backend.onrender.com",
)
SECRET_PATTERNS = (
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"(?:sk|gsk)_[0-9A-Za-z_-]{16,}"),
    re.compile(r"(?:ghp|github_pat)_[0-9A-Za-z_-]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
FIREBASE_WEB_CONFIGS = {
    Path("flutter-app/lib/firebase_options.dart"): re.compile(
        r"static const FirebaseOptions web = FirebaseOptions\((?P<body>.*?)\n\s*\);",
        re.DOTALL,
    ),
    Path("flutter-app/web/firebase-messaging-sw.js"): re.compile(
        r"const firebaseConfig = \{(?P<body>.*?)\n\};",
        re.DOTALL,
    ),
}
CREDENTIAL_ASSIGNMENT = re.compile(
    r"(?im)^[ \t]*(?:export[ \t]+)?['\"]?(?P<key>[A-Za-z_][A-Za-z0-9_.-]*)['\"]?"
    r"[ \t]*[:=][ \t]*(?:['\"])?(?P<value>[^\s'\"#,}]+)"
)
SAFE_ASSIGNMENT_PREFIXES = ("${", "${{", "replace", "your", "changeme")
SAFE_REFERENCE_PREFIXES = ("$", "os.environ", "os.getenv", "getenv", "process.env")


def _relative_path(path: Path) -> Path | None:
    """Return a repository-relative path, or None for external test fixtures."""
    try:
        return path.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return None


def _is_allowed_firebase_web_api_key(path: Path, text: str, match: re.Match[str]) -> bool:
    """Allow an AIza key only as the apiKey field of an owned Web config object."""
    config_pattern = FIREBASE_WEB_CONFIGS.get(_relative_path(path))
    if not config_pattern:
        return False

    for config_match in config_pattern.finditer(text):
        body_start, body_end = config_match.span("body")
        if not body_start <= match.start() < body_end:
            continue
        line_start = text.rfind("\n", body_start, match.start()) + 1
        line_end = text.find("\n", match.end())
        line_end = len(text) if line_end == -1 else line_end
        line = text[line_start:line_end]
        return bool(
            re.fullmatch(
                r"\s*apiKey\s*:\s*['\"]AIza[0-9A-Za-z_-]{20,}['\"]\s*,?\s*(?://.*)?",
                line,
            )
        )
    return False


def _is_credential_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_").replace(".", "_")
    return (
        normalized
        in {
            "client_secret",
            "clientsecret",
            "private_key",
            "privatekey",
        }
        or normalized.endswith(("_client_secret", "_private_key"))
        or normalized in {"smtp_user", "smtp_username", "smtp_password", "smtp_pass"}
    )


def _is_provider_credential_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_").replace(".", "_")
    provider_prefixes = (
        "gemini_",
        "groq_",
        "openai_",
        "huggingface_",
        "sentry_",
        "revenuecat_",
        "kong_",
    )
    return normalized == "api_key" or (
        normalized.startswith(provider_prefixes)
        and normalized.endswith(("api_key", "api_keys", "key", "token", "secret", "password", "dsn"))
    )


def _is_safe_credential_value(value: str) -> bool:
    normalized = value.lower()
    return normalized.startswith(SAFE_ASSIGNMENT_PREFIXES + SAFE_REFERENCE_PREFIXES)


def should_scan(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if relative in REFERENCE_FILES:
        return False
    if relative.name.lower().startswith("readme") or relative.suffix.lower() == ".md":
        return False
    if relative.name == ".gitignore":
        return False
    if (
        relative.name == "security.txt"
        and ".well-known" in relative.parts
        and ({"admin-service", "flutter-app"} & set(relative.parts))
    ):
        return False
    return not any(part in EXCLUDED_PARTS for part in relative.parts)


def violations_for(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []

    violations = ["legacy runtime marker" for marker in LEGACY_RUNTIME_MARKERS if marker in text]
    for pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            if pattern.pattern.startswith("AIza") and _is_allowed_firebase_web_api_key(path, text, match):
                continue
            violations.append("credential literal")

    environment_like = (
        path.suffix in {".env", ".yaml", ".yml", ".sh", ".bash"}
        or path.name.startswith(".env")
    )
    for match in CREDENTIAL_ASSIGNMENT.finditer(text):
        key = match.group("key")
        value = match.group("value")
        if (
            not (_is_credential_key(key) or environment_like and _is_provider_credential_key(key))
            or _is_safe_credential_value(value)
        ):
            continue
        violations.append("provider credential assignment")
    return violations


def paths_for(target: Path):
    """Yield files without traversing generated or dependency directories."""
    if target.is_file():
        yield target
        return

    for directory, subdirectories, filenames in os.walk(target):
        subdirectories[:] = [
            name for name in subdirectories if name not in EXCLUDED_PARTS
        ]
        parent = Path(directory)
        yield from (parent / name for name in filenames)


def main() -> int:
    violations: list[str] = []
    for target in TARGETS:
        candidate = ROOT / target
        for path in paths_for(candidate):
            if path.is_file() and should_scan(path):
                for reason in violations_for(path):
                    violations.append(f"{path.relative_to(ROOT)}: {reason}")

    if violations:
        print("Independence/secret sentinel failed:")
        print("\n".join(sorted(set(violations))))
        return 1
    print("Independence/secret sentinel passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
