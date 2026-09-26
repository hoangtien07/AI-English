#!/usr/bin/env bash
# Render kong.hybrid.yml from kong.hybrid.yml.template.
#
# Kong's declarative loader does not expand environment variables, so every
# ${VAR} placeholder in the template is substituted here with envsubst and the
# result is written to kong.hybrid.yml -- the file docker-compose.kong.hybrid.yml
# mounts read-only into the Kong container.
#
# Usage:
#   ./render-hybrid.sh [path/to/env-file]
# Variables are taken from the environment, optionally preceded by sourcing the
# env file given as $1 (default: ./kong-hybrid.env next to this script).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE="$SCRIPT_DIR/kong.hybrid.yml.template"
OUTPUT="$SCRIPT_DIR/kong.hybrid.yml"
ENV_FILE="${1:-$SCRIPT_DIR/kong-hybrid.env}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

required=(
  PUBLIC_WEB_ORIGIN
  ADMIN_WEB_ORIGIN
  BACKEND_UPSTREAM_URL
  AI_UPSTREAM_URL
  KONG_MOBILE_API_KEY
  KONG_ADMIN_API_KEY
  KONG_INTERNAL_API_KEY
)
missing=()
for var in "${required[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    missing+=("$var")
  fi
done
if (( ${#missing[@]} > 0 )); then
  printf 'Missing required environment variables: %s\n' "${missing[*]}" >&2
  printf 'Export them or list them in %s (see kong-hybrid.env.example).\n' "$ENV_FILE" >&2
  exit 1
fi

if ! command -v envsubst >/dev/null 2>&1; then
  echo 'envsubst not found; install gettext (e.g. apt-get install gettext-base).' >&2
  exit 1
fi

# Substitute only the declared inputs — bare envsubst would also blank out
# Kong/Nginx runtime variables ($host, $request_uri, ...) inside the template.
subst_vars="$(printf '${%s} ' "${required[@]}")"
envsubst "$subst_vars" < "$TEMPLATE" > "$OUTPUT"
printf 'Rendered %s\n' "$OUTPUT"
