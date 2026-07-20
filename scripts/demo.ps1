# End-to-end demo: register -> JWT -> scan a food photo -> calorie range.
#
# Point it at a running stack (docker compose up) or your staging URL:
#   $env:BASE_URL="http://localhost:8000"
#   .\scripts\demo.ps1 ml\data\raw\food-101\images\pizza\1005649.jpg
param([Parameter(Mandatory = $true)][string]$Image)

$ErrorActionPreference = "Stop"
$base = if ($env:BASE_URL) { $env:BASE_URL } else { "http://localhost:8000" }
$email = if ($env:DEMO_EMAIL) { $env:DEMO_EMAIL } else { "demo@nutriscan.app" }
$password = if ($env:DEMO_PASSWORD) { $env:DEMO_PASSWORD } else { "sup3rSecret!pw" }

if (-not (Test-Path $Image)) { throw "no such image: $Image" }
$creds = @{ email = $email; password = $password } | ConvertTo-Json

Write-Host "-> register $email (ok if it already exists)"
try { Invoke-RestMethod -Method Post -Uri "$base/api/v1/auth/register/" -ContentType "application/json" -Body $creds | Out-Null } catch {}

Write-Host "-> obtain JWT"
$token = (Invoke-RestMethod -Method Post -Uri "$base/api/v1/auth/token/" -ContentType "application/json" -Body $creds).access

Write-Host "-> scan $Image"
$form = @{ image = Get-Item $Image }
Invoke-RestMethod -Method Post -Uri "$base/api/v1/scan/" -Headers @{ Authorization = "Bearer $token" } -Form $form | ConvertTo-Json -Depth 6
