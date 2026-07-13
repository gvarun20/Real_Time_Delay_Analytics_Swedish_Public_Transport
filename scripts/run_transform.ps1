# Run PySpark transform for a service date
# Usage: .\scripts\run_transform.ps1 -ServiceDate 2026-07-12

param(
    [string]$ServiceDate = (Get-Date -Format "yyyy-MM-dd"),
    [double]$SampleFraction = 0
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host "Running transform for $ServiceDate ..."
$args = @(
    "compose", "exec", "airflow-scheduler",
    "python", "/opt/airflow/project/jobs/transform_gtfs.py",
    "--service-date", $ServiceDate
)
if ($SampleFraction -gt 0) {
    $args += @("--sample-fraction", $SampleFraction)
}

docker @args

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Check Postgres fact count:" -ForegroundColor Green
    Write-Host "  docker compose exec postgres-analytics psql -U transit -d transit_dw -c `"SELECT COUNT(*) FROM fact_trip_delay;`""
}
