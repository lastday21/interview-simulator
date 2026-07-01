param(
    [string]$ProjectPath,
    [switch]$SkipSmoke
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

function Wait-DockerReady {
    param(
        [int]$TimeoutSeconds = 180
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        docker info *> $null
        if ($LASTEXITCODE -eq 0) {
            return
        }
        Start-Sleep -Seconds 3
    }

    throw "Docker daemon did not become ready within $TimeoutSeconds seconds"
}

function Start-DockerDesktop {
    docker info *> $null
    if ($LASTEXITCODE -eq 0) {
        return
    }

    $dockerDesktopPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dockerDesktopPath) {
        Start-Process -FilePath $dockerDesktopPath -WindowStyle Hidden
    }

    Wait-DockerReady
}

if ([string]::IsNullOrWhiteSpace($ProjectPath)) {
    $ProjectPath = Resolve-Path (Join-Path $PSScriptRoot "..")
}

Push-Location $ProjectPath
try {
    if (-not (Test-Path ".env")) {
        throw "Missing .env in $ProjectPath"
    }

    Start-DockerDesktop
    Invoke-Checked docker @("compose", "up", "-d", "--build")
    Invoke-Checked docker @("compose", "ps")

    if (-not $SkipSmoke) {
        & (Join-Path $PSScriptRoot "smoke.ps1") -ProjectPath $ProjectPath
    }
}
finally {
    Pop-Location
}
