param(
    [string]$ProjectPath
)

$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param(
        [string]$Command,
        [string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $Command $($Arguments -join ' ')"
    }
}

if ([string]::IsNullOrWhiteSpace($ProjectPath)) {
    $ProjectPath = Resolve-Path (Join-Path $PSScriptRoot "..")
}

Push-Location $ProjectPath
try {
    Invoke-Checked docker @("compose", "ps")

    $runningServices = docker compose ps --services --status running
    if ($LASTEXITCODE -ne 0) {
        throw "Could not read running docker compose services"
    }

    foreach ($service in @("bot", "db", "redis")) {
        if ($runningServices -notcontains $service) {
            throw "Service is not running: $service"
        }
    }

    Invoke-Checked docker @(
        "compose",
        "exec",
        "-T",
        "db",
        "pg_isready",
        "-h",
        "127.0.0.1"
    )

    $redisPing = docker compose exec -T redis redis-cli ping
    if ($LASTEXITCODE -ne 0) {
        throw "Redis ping command failed"
    }
    if (($redisPing | Select-Object -First 1).Trim() -ne "PONG") {
        throw "Redis ping did not return PONG"
    }

    Invoke-Checked docker @(
        "compose",
        "exec",
        "-T",
        "bot",
        "python",
        "scripts/runtime_smoke.py"
    )
}
finally {
    Pop-Location
}
