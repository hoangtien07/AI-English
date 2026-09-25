#!/usr/bin/env bash
# Bash port of dev-local.ps1 for macOS/Linux developers.
# Same commands and safety contract:
#   ./scripts/dev-local.sh <up-core|up-full|status|test|stop|reset-data> [DELETE-LOCAL-DATA]
set -euo pipefail

ProjectName="lexilingo"
ResetConfirmation="DELETE-LOCAL-DATA"
RepositoryRoot="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ComposeFile="$RepositoryRoot/docker-compose.dev.yml"
RootEnvironmentFile="$RepositoryRoot/.env"
BackendEnvironmentFile="$RepositoryRoot/backend-service/.env"
CoreServices=(postgres redis backend-service)
FullServices=(postgres redis backend-service mongodb redis-ai ai-service)

die() {
    echo "[dev-local] ERROR: $*" >&2
    exit 1
}

info() {
    echo "[dev-local] $*"
}

assert_command_available() {
    command -v "$1" >/dev/null 2>&1 || die "Required command '$1' was not found on PATH."
}

is_ignored_file() {
    git -C "$RepositoryRoot" check-ignore --quiet -- "$1"
}

# Reads KEY=VALUE lines (matching dev-local.ps1's parser) into the named
# associative array. Values are returned trimmed; no values are printed.
read_environment_values() {
    local path="$1" out_var="$2"
    local line trimmed key value
    declare -n values="$out_var"
    values=()
    while IFS= read -r line || [[ -n "$line" ]]; do
        trimmed="${line#"${line%%[![:space:]]*}"}"
        trimmed="${trimmed%"${trimmed##*[![:space:]]}"}"
        [[ -z "$trimmed" || "$trimmed" == \#* ]] && continue
        if [[ "$trimmed" =~ ^(export[[:space:]]+)?([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*=[[:space:]]*(.*)$ ]]; then
            key="${BASH_REMATCH[2]}"
            value="${BASH_REMATCH[3]}"
            value="${value%"${value##*[![:space:]]}"}"
            values["$key"]="$value"
        fi
    done < "$path"
}

assert_environment_files() {
    local path
    for path in "$RootEnvironmentFile" "$BackendEnvironmentFile"; do
        [[ -f "$path" ]] || die "Required ignored local environment file is missing: $path. Copy its .env.example and provide owned local values."
        is_ignored_file "$path" || die "Refusing to use '$path' because it is not ignored by Git. Local secrets must remain ignored."
    done
}

assert_required_environment_values() {
    local file_label="$1" values_var="$2"
    shift 2
    local required_names=("$@")
    local missing=() name
    declare -n values="$values_var"
    for name in "${required_names[@]}"; do
        [[ -n "${values[$name]:-}" ]] || missing+=("${file_label}:${name}")
    done
    ((${#missing[@]} == 0)) || die "Required local environment values are missing or empty: ${missing[*]}. Values were not displayed."
}

assert_core_environment() {
    assert_environment_files
    local root_values backend_values
    read_environment_values "$RootEnvironmentFile" root_values
    assert_required_environment_values ".env" root_values POSTGRES_PASSWORD SECRET_KEY ALLOWED_ORIGINS
    read_environment_values "$BackendEnvironmentFile" backend_values
    assert_required_environment_values "backend-service/.env" backend_values APP_ENV DATABASE_URL SECRET_KEY ALLOWED_ORIGINS ALLOWED_HOSTS REDIS_URL AI_SERVICE_URL
}

assert_full_environment() {
    assert_core_environment
    local root_values
    read_environment_values "$RootEnvironmentFile" root_values
    assert_required_environment_values ".env" root_values AI_ADMIN_API_KEY GEMINI_API_KEY
}

compose() {
    assert_command_available docker
    docker compose --project-name "$ProjectName" --file "$ComposeFile" --env-file "$RootEnvironmentFile" "$@"
}

service_health() {
    local service="$1" container_id state
    container_id="$(compose ps -q "$service" 2>/dev/null | tr -d '[:space:]')" || true
    [[ -n "$container_id" ]] || { echo "missing"; return; }
    state="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container_id" 2>/dev/null | tr -d '[:space:]')" || true
    [[ -n "$state" ]] || { echo "unknown"; return; }
    echo "$state"
}

wait_for_service_health() {
    local timeout_seconds="$1"
    shift
    local services=("$@")
    local deadline=$((SECONDS + timeout_seconds)) pending service state
    while true; do
        pending=()
        for service in "${services[@]}"; do
            state="$(service_health "$service")"
            [[ "$state" == "healthy" ]] || pending+=("$service ($state)")
        done
        ((${#pending[@]} == 0)) && return 0
        ((SECONDS < deadline)) || die "Timed out waiting for healthy services: ${pending[*]}. Run './scripts/dev-local.sh status' and 'docker compose --project-name $ProjectName --file docker-compose.dev.yml logs --tail 100 <service>' for a targeted diagnosis."
        sleep 2
    done
}

wait_for_http_health() {
    local name="$1" uri="$2" timeout_seconds="$3"
    local deadline=$((SECONDS + timeout_seconds)) last_failure="no response" code
    assert_command_available curl
    while true; do
        code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 5 "$uri" 2>/dev/null)" || code=""
        if [[ "$code" =~ ^[0-9]+$ ]] && ((code >= 200 && code < 300)); then
            return 0
        fi
        last_failure="${code:+HTTP $code}"
        last_failure="${last_failure:-curl failed}"
        ((SECONDS < deadline)) || die "$name did not become ready at $uri within $timeout_seconds seconds ($last_failure). Run './scripts/dev-local.sh status' and inspect only that service's Compose logs."
        sleep 2
    done
}

start_local_stack() {
    local include_ai="$1"
    if [[ "$include_ai" == "true" ]]; then
        assert_full_environment
        compose --profile full up --detach
        wait_for_service_health 240 "${FullServices[@]}"
        wait_for_http_health "Backend" "http://127.0.0.1:8000/health" 30
        wait_for_http_health "AI service" "http://127.0.0.1:8001/health" 30
        info "Full local stack is healthy (backend: http://127.0.0.1:8000, AI: http://127.0.0.1:8001)."
    else
        assert_core_environment
        compose up --detach "${CoreServices[@]}"
        wait_for_service_health 150 "${CoreServices[@]}"
        wait_for_http_health "Backend" "http://127.0.0.1:8000/health" 30
        info "Core local stack is healthy (backend: http://127.0.0.1:8000)."
    fi
}

show_status() {
    [[ -f "$RootEnvironmentFile" ]] || die "Cannot inspect this Compose project because .env is missing. No values were read."
    compose ps
    local service
    for service in "${FullServices[@]}"; do
        info "$service: $(service_health "$service")"
    done
}

assert_not_running_tests() {
    local name
    for name in PYTEST_CURRENT_TEST PESTER_VERSION DEV_LOCAL_TEST_MODE CI; do
        [[ -z "${!name:-}" ]] || die "Refusing reset-data while a test context is active ($name)."
    done
}

declared_compose_volumes() {
    assert_command_available python3
    compose config --format json | python3 -c 'import json,sys; print("\n".join(sorted((json.load(sys.stdin).get("volumes") or {}).keys())))'
}

reset_data_volumes() {
    local declared targets=() volume logical_name
    mapfile -t declared < <(declared_compose_volumes)
    while IFS= read -r volume; do
        [[ -n "$volume" ]] || continue
        logical_name="$(docker volume inspect --format '{{ index .Labels "com.docker.compose.volume" }}' "$volume" 2>/dev/null | tr -d '[:space:]')" \
            || die "Refusing reset-data because Compose volume '$volume' has an ambiguous label."
        [[ -n "$logical_name" ]] || die "Refusing reset-data because Compose volume '$volume' has an ambiguous label."
        local found=""
        if ((${#declared[@]} > 0)); then
            local d
            for d in "${declared[@]}"; do [[ "$d" == "$logical_name" ]] && found=1; done
        fi
        [[ -n "$found" ]] || die "Refusing reset-data because Compose volume '$volume' is outside this file's declared local data contract."
        targets+=("$volume")
    done < <(docker volume ls --quiet --filter "label=com.docker.compose.project=$ProjectName")
    printf '%s\n' "${targets[@]:-}" | awk 'NF' | sort -u
}

reset_local_data() {
    local confirm="$1"
    assert_not_running_tests
    [[ "$confirm" == "$ResetConfirmation" ]] || die "reset-data is destructive and requires the '$ResetConfirmation' confirmation argument. No containers or volumes were changed."
    assert_core_environment
    local volumes=()
    mapfile -t volumes < <(reset_data_volumes)
    ((${#volumes[@]} > 0)) || { info "No existing local Compose data volumes were found for project '$ProjectName'; nothing was reset."; return; }
    info "The following exact local Compose volumes will be removed: ${volumes[*]}"
    compose stop
    docker volume rm -- "${volumes[@]}" || die "One or more exact local Compose volumes could not be removed. No broader cleanup was attempted."
    info "Local Compose data was reset. Run './scripts/dev-local.sh up-core' or './scripts/dev-local.sh up-full' to create fresh local data."
}

invoke_local_checks() {
    assert_core_environment
    info "Starting only PostgreSQL and Redis for the isolated backend test runner."
    compose up --detach postgres redis
    wait_for_service_health 90 postgres redis
    (cd "$RepositoryRoot/backend-service" && python -m scripts.run_isolated_tests) \
        || die "Isolated backend pytest failed."
    local ai_pytest_base_temp="$RepositoryRoot/ai-service/.pytest-tmp"
    mkdir -p "$ai_pytest_base_temp"
    compose --profile full run --rm --no-deps --volume "$ai_pytest_base_temp:/tmp/pytest" \
        ai-service python -m pytest tests/test_config_security.py tests/stt/test_config.py -q --basetemp=/tmp/pytest
    npm --prefix "$RepositoryRoot/admin-service" run test \
        || die "Admin tests failed."
    npm --prefix "$RepositoryRoot/admin-service" run build:check \
        || die "Admin build check failed."
    (cd "$RepositoryRoot/flutter-app" && flutter test) \
        || die "Flutter tests failed."
    (cd "$RepositoryRoot/flutter-app" && flutter analyze --no-fatal-warnings --no-fatal-infos) \
        || die "Flutter analysis found one or more errors. Warnings and infos were reported but are non-fatal."
    info "Local checks completed without resetting Compose data."
}

Command="${1:-}"
ConfirmArg="${2:-}"

case "$Command" in
    up-core)   start_local_stack false ;;
    up-full)   start_local_stack true ;;
    status)    show_status ;;
    test)      invoke_local_checks ;;
    stop)      assert_environment_files; compose stop; info "Local Compose services stopped; data volumes were preserved." ;;
    reset-data) reset_local_data "$ConfirmArg" ;;
    *) die "Usage: ./scripts/dev-local.sh <up-core|up-full|status|test|stop|reset-data> [$ResetConfirmation]" ;;
esac
