#!/usr/bin/env bash
# Render the edge nginx configs from nginx/templates/*.template into
# nginx/conf.d/*.conf, which docker-compose.gateway.yml mounts read-only.
# nginx does not expand ${VAR} placeholders itself, so substitution happens
# here via envsubst.
#
# Usage:
#   ./render-nginx.sh [path/to/env-file]
# Variables are taken from the environment, optionally preceded by sourcing the
# env file given as $1 (default: ./gateway.env next to this script).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="$SCRIPT_DIR/nginx/templates"
OUTPUT_DIR="$SCRIPT_DIR/nginx/conf.d"
ENV_FILE="${1:-$SCRIPT_DIR/gateway.env}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

required=(
  API_SERVER_NAME
  AI_SERVER_NAME
  API_SSL_CERT_PATH
  API_SSL_KEY_PATH
  AI_SSL_CERT_PATH
  AI_SSL_KEY_PATH
  BACKEND_UPSTREAM_ADDR
  AI_UPSTREAM_ADDR
)
missing=()
for var in "${required[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    missing+=("$var")
  fi
done
if (( ${#missing[@]} > 0 )); then
  printf 'Missing required environment variables: %s\n' "${missing[*]}" >&2
  printf 'Export them or list them in %s (see gateway.env.example).\n' "$ENV_FILE" >&2
  exit 1
fi

if ! command -v envsubst >/dev/null 2>&1; then
  echo 'envsubst not found; install gettext (e.g. apt-get install gettext-base).' >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"
shopt -s nullglob
for template in "$TEMPLATE_DIR"/*.template; do
  output="$OUTPUT_DIR/$(basename "${template%.template}")"
  envsubst < "$template" > "$output"
  printf 'Rendered %s\n' "$output"
done
