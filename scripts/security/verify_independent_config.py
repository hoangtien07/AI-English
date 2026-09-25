#!/usr/bin/env python3
"""Reject legacy runtime coupling and obvious private credentials in deployable sources.

This is a current-tree guard, not a history rewrite tool. Documentation, licenses,
and test/reference fixtures are deliberately excluded because they may describe
legacy systems without being executable deployment input.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TARGETS = (
    ".github",
    "admin-service",
    "ai-service",
    "backend-service",
    "contracts",
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
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"\b(?:sk|gsk)_[0-9A-Za-z_-]{16,}"),
    re.compile(r"\b(?:ghp|github_pat)_[0-9A-Za-z_-]{16,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
PROVIDER_ASSIGNMENT = re.compile(
    r"(?im)^[ \t]*(?:GEMINI|GROQ|OPENAI|HUGGINGFACE|SENTRY|REVENUECAT|KONG)"
    r"[A-Z0-9_]*(?:API_KEYS?|KEY|TOKEN|SECRET|PASSWORD|DSN)"
    r"[ \t]*[:=][ \t]*['\"]?([^\s'\"#]+)"
)
NESTED_PROVIDER_ASSIGNMENT = re.compile(
    r"(?im)^[ \t]*api_key[ \t]*:[ \t]*['\"]?([^\s'\"#]+)"
)
SAFE_ASSIGNMENT_PREFIXES = ("${", "${{", "replace", "your", "changeme")


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
    violations.extend("credential literal" for pattern in SECRET_PATTERNS if pattern.search(text))
    environment_like = path.suffix in {".env", ".yaml", ".yml", ".sh", ".bash"} or path.name.startswith(".env")
    if environment_like:
        for value in (*PROVIDER_ASSIGNMENT.findall(text), *NESTED_PROVIDER_ASSIGNMENT.findall(text)):
            normalized = value.lower()
            if normalized and not normalized.startswith(SAFE_ASSIGNMENT_PREFIXES):
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
