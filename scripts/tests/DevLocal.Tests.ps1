$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$scriptPath = Join-Path $repoRoot 'scripts/dev-local.ps1'

function Invoke-DevLocal {
    param([string[]] $Arguments)

    $previousPath = $env:Path
    $previousErrorActionPreference = $ErrorActionPreference
    try {
        # Tests that exercise refusal paths must never resolve the host Docker CLI.
        $env:Path = "$TestDrive$([IO.Path]::PathSeparator)$previousPath"
        $global:LASTEXITCODE = 0
        $ErrorActionPreference = 'Continue'
        $output = & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $scriptPath @Arguments 2>&1 | Out-String
        [pscustomobject]@{
            ExitCode = $global:LASTEXITCODE
            Output   = $output
        }
    }
    finally {
        $env:Path = $previousPath
        $ErrorActionPreference = $previousErrorActionPreference
    }
}

Describe 'scripts/dev-local.ps1 command safety' {
    BeforeAll {
        (Test-Path -LiteralPath $scriptPath) | Should Be $true
    }

    It 'rejects a missing command and prints the supported command names' {
        $result = Invoke-DevLocal @()

        $result.ExitCode | Should Not Be 0
        foreach ($command in 'up-core', 'up-full', 'status', 'test', 'stop', 'reset-data') {
            $result.Output | Should Match ([regex]::Escape($command))
        }
    }

    It 'rejects an unknown command without invoking Docker' {
        $dockerLog = Join-Path $TestDrive 'docker-called.txt'
        Set-Content -LiteralPath (Join-Path $TestDrive 'docker.cmd') -Value "@echo off`r`necho %* > `"$dockerLog`"`r`nexit /b 0"

        $result = Invoke-DevLocal @('not-a-command')

        $result.ExitCode | Should Not Be 0
        $result.Output | Should Match 'unknown|unsupported|usage'
        (Test-Path -LiteralPath $dockerLog) | Should Be $false
    }

    It 'refuses reset-data without the exact destructive confirmation before invoking Docker' {
        $dockerLog = Join-Path $TestDrive 'docker-called.txt'
        Set-Content -LiteralPath (Join-Path $TestDrive 'docker.cmd') -Value "@echo off`r`necho %* > `"$dockerLog`"`r`nexit /b 0"

        foreach ($arguments in @(
            @('reset-data'),
            @('reset-data', '-ConfirmResetData', 'not-the-confirmation')
        )) {
            $result = Invoke-DevLocal $arguments
            $result.ExitCode | Should Not Be 0
            $result.Output | Should Match 'confirm|DELETE-LOCAL-DATA'
        }

        (Test-Path -LiteralPath $dockerLog) | Should Be $false
    }

    It 'uses a named strong confirmation contract and does not use broad Compose volume deletion' {
        $source = Get-Content -Raw -LiteralPath $scriptPath

        $source | Should Match 'ConfirmResetData'
        $source | Should Match 'DELETE-LOCAL-DATA'
        $source | Should Not Match '(?i)compose\s+down\s+.*(?:--volumes|-v)'
    }

    It 'uses the deterministic lexilingo Compose project identity for every managed command' {
        $source = Get-Content -Raw -LiteralPath $scriptPath

        $source | Should Match '\$ProjectName\s*=\s*"lexilingo"'
        $source | Should Match 'compose\s+--project-name\s+\$ProjectName'
        $source | Should Match 'label=com\.docker\.compose\.project=\$ProjectName'
    }

    It 'keeps management-tool credentials out of core and full environment requirements' {
        $source = Get-Content -Raw -LiteralPath $scriptPath

        $source | Should Match 'function Assert-CoreEnvironment'
        $source | Should Match 'function Assert-FullEnvironment'
        $source | Should Match 'Assert-CoreEnvironment\s*\r?\n\s*\$rootValues'
        $source | Should Match '"AI_ADMIN_API_KEY", "GEMINI_API_KEY"'
        $source | Should Not Match 'Assert-RequiredEnvironmentValues .*PGADMIN_DEFAULT_PASSWORD'
        $source | Should Not Match 'Assert-RequiredEnvironmentValues .*MONGO_EXPRESS_PASSWORD'
        $source | Should Match '"up-core" \{ Start-LocalStack \$false \}'
        $source | Should Match '"up-full" \{ Start-LocalStack \$true \}'
        $source | Should Match 'function Invoke-LocalChecks \{\s*Assert-CoreEnvironment'
        $source | Should Match 'Invoke-Compose \(@\("up", "--detach"\) \+ \$CoreServices\)'
        $source | Should Match 'Invoke-Compose @\("--profile", "full", "up", "--detach"\)'
        $source | Should Match 'Values were not displayed'
    }

    It 'runs focused AI tests in the profiled Compose container with read-only tests and an explicit repo-local basetemp' {
        $source = Get-Content -Raw -LiteralPath $scriptPath
        $compose = Get-Content -Raw -LiteralPath (Join-Path $repoRoot 'docker-compose.dev.yml')

        $source | Should Match 'ai-service/\.pytest-tmp'
        $source | Should Match 'New-Item -ItemType Directory -Path \$aiPytestBaseTemp -Force'
        $source | Should Match '"--profile", "full", "run", "--rm", "--no-deps"'
        $source | Should Match '"--basetemp=/tmp/pytest"'
        $source | Should Not Match 'python -m pytest tests/test_config_security\.py tests/stt/test_config\.py -q'
        $compose | Should Match '\./ai-service/tests:/app/tests:ro'
    }

    It 'keeps Flutter analysis visible while making only errors fatal' {
        $source = Get-Content -Raw -LiteralPath $scriptPath

        $source | Should Match 'flutter analyze --no-fatal-warnings --no-fatal-infos'
        $source | Should Match 'Flutter analysis found one or more errors'
    }

    It 'keeps reset constrained to exact labelled volumes declared by this Compose file' {
        $source = Get-Content -Raw -LiteralPath $scriptPath

        $source | Should Match 'function Get-DeclaredComposeVolumes'
        $source | Should Match 'function Get-ResetDataVolumes'
        $source | Should Match 'com\.docker\.compose\.volume'
        $source | Should Match 'docker volume rm -- \$volumes'
        $source | Should Not Match '(?i)docker\s+volume\s+prune'
    }
}
