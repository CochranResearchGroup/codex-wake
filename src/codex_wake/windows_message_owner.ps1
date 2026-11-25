# Foreground runner for a preconfigured normal Windows account and native database.
# Configure the service/task outside this script under the owning account.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Python,
    [Parameter(Mandatory=$true)][string]$OwnerConfig,
    [ValidatePattern('^[A-Za-z0-9_.-]{1,128}$')][string]$PostgresService,
    [int]$ReadinessSeconds=30,
    [switch]$Once
)

$ErrorActionPreference = 'Stop'
if ($ReadinessSeconds -lt 1 -or $ReadinessSeconds -gt 300 -or
    -not [System.IO.Path]::IsPathRooted($Python) -or
    -not [System.IO.Path]::IsPathRooted($OwnerConfig)) { exit 2 }

if ($PostgresService) {
    $wait = [System.Diagnostics.Stopwatch]::StartNew()
    do {
        $database = Get-Service -Name $PostgresService -ErrorAction SilentlyContinue
        if ($database -and $database.Status -eq 'Running') { break }
        if ($Once) { break }
        Start-Sleep -Milliseconds 500
    } while ($wait.Elapsed.TotalSeconds -lt $ReadinessSeconds)
    if (-not $database -or $database.Status -ne 'Running') {
        '{"shared_ingress":false,"status":"waiting_for_native_database_service"}'
        exit 3
    }
}

# SQL readiness is required even when an isolated foreground database has no
# registered Windows service.
if ($Once) {
    $result = & $Python -m codex_wake.message_owner --config $OwnerConfig tick
    $code = $LASTEXITCODE
    $result
    if ($code -eq 0 -and ($result | ConvertFrom-Json).shared_ingress -ne $true) { exit 3 }
    exit $code
}
& $Python -m codex_wake.message_owner --config $OwnerConfig run
exit $LASTEXITCODE
