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

if ([string]::IsNullOrWhiteSpace($ProjectPath)) {
    $ProjectPath = Resolve-Path (Join-Path $PSScriptRoot "..")
}

Push-Location $ProjectPath
try {
    if (-not (Test-Path ".env")) {
        throw "Missing .env in $ProjectPath"
    }

    Invoke-Checked docker @("compose", "up", "-d", "--build")
    Invoke-Checked docker @("compose", "ps")

    if (-not $SkipSmoke) {
        & (Join-Path $PSScriptRoot "smoke.ps1") -ProjectPath $ProjectPath
    }
}
finally {
    Pop-Location
}
