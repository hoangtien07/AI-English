[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$Command,

    [string]$ConfirmResetData
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectName = "lexilingo"
$ResetConfirmation = "DELETE-LOCAL-DATA"
$RepositoryRoot = Split-Path -Parent $PSScriptRoot
$ComposeFile = Join-Path $RepositoryRoot "docker-compose.dev.yml"
$RootEnvironmentFile = Join-Path $RepositoryRoot ".env"
$BackendEnvironmentFile = Join-Path $RepositoryRoot "backend-service/.env"
$CoreServices = @("postgres", "redis", "backend-service")
$FullServices = @("postgres", "redis", "backend-service", "mongodb", "redis-ai", "ai-service")
$SupportedCommands = @("up-core", "up-full", "status", "test", "stop", "reset-data")

function Stop-WithError([string]$Message) {
    Write-Error $Message
    exit 1
}

function Write-Info([string]$Message) {
    Write-Host "[dev-local] $Message"
}

function Assert-CommandAvailable([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found on PATH."
    }
}

function Test-IgnoredFile([string]$Path) {
    & git check-ignore --quiet -- $Path
    return $LASTEXITCODE -eq 0
}

function Get-EnvironmentValues([string]$Path) {
    $values = @{}
    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if ($trimmed.Length -eq 0 -or $trimmed.StartsWith("#")) { continue }
        if ($trimmed -match "^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$") {
            $values[$matches[1]] = $matches[2].Trim()
        }
    }
    return $values
}

function Assert-EnvironmentFiles {
    foreach ($path in @($RootEnvironmentFile, $BackendEnvironmentFile)) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Required ignored local environment file is missing: $path. Copy its .env.example and provide owned local values."
        }
        if (-not (Test-IgnoredFile $path)) {
            throw "Refusing to use '$path' because it is not ignored by Git. Local secrets must remain ignored."
        }
    }
}

function Assert-RequiredEnvironmentValues([hashtable]$Values, [string]$FileLabel, [string[]]$RequiredNames) {
    $missing = @()
    foreach ($name in $RequiredNames) {
        if (-not $Values.ContainsKey($name) -or [string]::IsNullOrWhiteSpace($Values[$name])) { $missing += "${FileLabel}:$name" }
    }
    if ($missing.Count -gt 0) {
        throw "Required local environment values are missing or empty: $($missing -join ', '). Values were not displayed."
    }
}

function Assert-CoreEnvironment {
    Assert-EnvironmentFiles
    Assert-RequiredEnvironmentValues (Get-EnvironmentValues $RootEnvironmentFile) ".env" @("POSTGRES_PASSWORD", "SECRET_KEY", "ALLOWED_ORIGINS", "FIREBASE_PROJECT_ID")
    Assert-RequiredEnvironmentValues (Get-EnvironmentValues $BackendEnvironmentFile) "backend-service/.env" @("APP_ENV", "DATABASE_URL", "SECRET_KEY", "ALLOWED_ORIGINS", "ALLOWED_HOSTS", "REDIS_URL", "AI_SERVICE_URL")
}

function Assert-FullEnvironment {
    Assert-CoreEnvironment
    $rootValues = Get-EnvironmentValues $RootEnvironmentFile
    Assert-RequiredEnvironmentValues $rootValues ".env" @("AI_ADMIN_API_KEY", "GEMINI_API_KEY")
}

function Invoke-Compose([string[]]$Arguments) {
    Assert-CommandAvailable "docker"
    $composeArguments = @("compose", "--project-name", $ProjectName, "--file", $ComposeFile, "--env-file", $RootEnvironmentFile) + $Arguments
    & docker @composeArguments
    if ($LASTEXITCODE -ne 0) { throw "Docker Compose command failed (exit code $LASTEXITCODE)." }
}

function Get-ServiceHealth([string]$Service) {
    $containerOutput = @(& docker compose --project-name $ProjectName --file $ComposeFile --env-file $RootEnvironmentFile ps -q $Service)
    $containerId = ($containerOutput -join "").Trim()
    if ([string]::IsNullOrWhiteSpace($containerId)) { return "missing" }
    $stateOutput = @(& docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' $containerId)
    $state = ($stateOutput -join "").Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($state)) { return "unknown" }
    return $state
}

function Wait-ForServiceHealth([string[]]$Services, [int]$TimeoutSeconds) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        $pending = @()
        foreach ($service in $Services) {
            $state = Get-ServiceHealth $service
            if ($state -ne "healthy") { $pending += "$service ($state)" }
        }
        if ($pending.Count -eq 0) { return }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    throw "Timed out waiting for healthy services: $($pending -join ', '). Run '.\\scripts\\dev-local.ps1 status' and 'docker compose --project-name $ProjectName --file docker-compose.dev.yml logs --tail 100 <service>' for a targeted diagnosis."
}

function Wait-ForHttpHealth([string]$Name, [string]$Uri, [int]$TimeoutSeconds) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $lastFailure = "no response"
    do {
        try {
            $response = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) { return }
            $lastFailure = "HTTP $($response.StatusCode)"
        } catch { $lastFailure = $_.Exception.Message }
        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)
    throw "$Name did not become ready at $Uri within $TimeoutSeconds seconds ($lastFailure). Run '.\\scripts\\dev-local.ps1 status' and inspect only that service's Compose logs."
}

function Start-LocalStack([bool]$IncludeAi) {
    if ($IncludeAi) {
        Assert-FullEnvironment
        Invoke-Compose @("--profile", "full", "up", "--detach")
        Wait-ForServiceHealth $FullServices 240
        Wait-ForHttpHealth "Backend" "http://127.0.0.1:8000/health" 30
        Wait-ForHttpHealth "AI service" "http://127.0.0.1:8001/health" 30
        Write-Info "Full local stack is healthy (backend: http://127.0.0.1:8000, AI: http://127.0.0.1:8001)."
    } else {
        Assert-CoreEnvironment
        Invoke-Compose (@("up", "--detach") + $CoreServices)
        Wait-ForServiceHealth $CoreServices 150
        Wait-ForHttpHealth "Backend" "http://127.0.0.1:8000/health" 30
        Write-Info "Core local stack is healthy (backend: http://127.0.0.1:8000)."
    }
}

function Show-Status {
    if (-not (Test-Path -LiteralPath $RootEnvironmentFile -PathType Leaf)) { throw "Cannot inspect this Compose project because .env is missing. No values were read." }
    Invoke-Compose @("ps")
    foreach ($service in $FullServices) { Write-Info "${service}: $(Get-ServiceHealth $service)" }
}

function Assert-NotRunningTests {
    foreach ($name in @("PYTEST_CURRENT_TEST", "PESTER_VERSION", "DEV_LOCAL_TEST_MODE", "CI")) {
        if (-not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($name))) { throw "Refusing reset-data while a test context is active ($name)." }
    }
    if (@(Get-PSCallStack | Where-Object { $_.Command -match "Pester|Invoke-Pester|\bIt\b" }).Count -gt 0) { throw "Refusing reset-data while invoked from a PowerShell test context." }
}

function Get-DeclaredComposeVolumes {
    $configText = & docker compose --project-name $ProjectName --file $ComposeFile --env-file $RootEnvironmentFile config --format json
    if ($LASTEXITCODE -ne 0) { throw "Unable to resolve the local Compose volume contract." }
    return @(($configText | ConvertFrom-Json).volumes.PSObject.Properties.Name)
}

function Get-ResetDataVolumes {
    $declared = Get-DeclaredComposeVolumes
    $targets = @()
    foreach ($volume in @(& docker volume ls --quiet --filter "label=com.docker.compose.project=$ProjectName")) {
        if ([string]::IsNullOrWhiteSpace($volume)) { continue }
        $logicalName = (& docker volume inspect --format '{{ index .Labels "com.docker.compose.volume" }}' $volume).Trim()
        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($logicalName)) { throw "Refusing reset-data because Compose volume '$volume' has an ambiguous label." }
        if ($logicalName -notin $declared) { throw "Refusing reset-data because Compose volume '$volume' is outside this file's declared local data contract." }
        $targets += $volume
    }
    return @($targets | Sort-Object -Unique)
}

function Reset-LocalData {
    Assert-NotRunningTests
    if ($ConfirmResetData -cne $ResetConfirmation) { throw "reset-data is destructive and requires -ConfirmResetData '$ResetConfirmation'. No containers or volumes were changed." }
    Assert-CoreEnvironment
    $volumes = Get-ResetDataVolumes
    if ($volumes.Count -eq 0) { Write-Info "No existing local Compose data volumes were found for project '$ProjectName'; nothing was reset."; return }
    Write-Info "The following exact local Compose volumes will be removed: $($volumes -join ', ')"
    Invoke-Compose @("stop")
    & docker volume rm -- $volumes
    if ($LASTEXITCODE -ne 0) { throw "One or more exact local Compose volumes could not be removed. No broader cleanup was attempted." }
    Write-Info "Local Compose data was reset. Run '.\\scripts\\dev-local.ps1 up-core' or '.\\scripts\\dev-local.ps1 up-full' to create fresh local data."
}

function Invoke-LocalChecks {
    Assert-CoreEnvironment
    Write-Info "Starting only PostgreSQL and Redis for the isolated backend test runner."
    Invoke-Compose @("up", "--detach", "postgres", "redis")
    Wait-ForServiceHealth @("postgres", "redis") 90
    Push-Location (Join-Path $RepositoryRoot "backend-service")
    try { & python -m scripts.run_isolated_tests; if ($LASTEXITCODE -ne 0) { throw "Isolated backend pytest failed (exit code $LASTEXITCODE)." } } finally { Pop-Location }
    $aiPytestBaseTemp = Join-Path $RepositoryRoot "ai-service/.pytest-tmp"
    New-Item -ItemType Directory -Path $aiPytestBaseTemp -Force | Out-Null
    Invoke-Compose @("--profile", "full", "run", "--rm", "--no-deps", "--volume", "${aiPytestBaseTemp}:/tmp/pytest", "ai-service", "python", "-m", "pytest", "tests/test_config_security.py", "tests/stt/test_config.py", "-q", "--basetemp=/tmp/pytest")
    & npm --prefix (Join-Path $RepositoryRoot "admin-service") run test
    if ($LASTEXITCODE -ne 0) { throw "Admin tests failed (exit code $LASTEXITCODE)." }
    & npm --prefix (Join-Path $RepositoryRoot "admin-service") run build:check
    if ($LASTEXITCODE -ne 0) { throw "Admin build check failed (exit code $LASTEXITCODE)." }
    Push-Location (Join-Path $RepositoryRoot "flutter-app")
    try { & flutter test; if ($LASTEXITCODE -ne 0) { throw "Flutter tests failed (exit code $LASTEXITCODE)." }; & flutter analyze --no-fatal-warnings --no-fatal-infos; if ($LASTEXITCODE -ne 0) { throw "Flutter analysis found one or more errors (exit code $LASTEXITCODE). Warnings and infos were reported but are non-fatal." } } finally { Pop-Location }
    Write-Info "Local checks completed without resetting Compose data."
}

if ([string]::IsNullOrWhiteSpace($Command) -or $Command -notin $SupportedCommands) {
    Stop-WithError "Usage: .\\scripts\\dev-local.ps1 <up-core|up-full|status|test|stop|reset-data> [-ConfirmResetData '$ResetConfirmation']"
}

try {
    switch ($Command) {
        "up-core" { Start-LocalStack $false }
        "up-full" { Start-LocalStack $true }
        "status" { Show-Status }
        "test" { Invoke-LocalChecks }
        "stop" { Assert-EnvironmentFiles; Invoke-Compose @("stop"); Write-Info "Local Compose services stopped; data volumes were preserved." }
        "reset-data" { Reset-LocalData }
    }
} catch {
    Stop-WithError $_.Exception.Message
}
