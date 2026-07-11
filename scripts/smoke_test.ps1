$ErrorActionPreference = "Stop"

$ApiUrl = if ($env:AUTOSNAB_API_URL) { $env:AUTOSNAB_API_URL } else { "http://localhost:8000" }
$CadastralNumber = "66:41:0101001:123"

Write-Host "1/3 GET /ping"
$ping = Invoke-RestMethod -Method Get -Uri "$ApiUrl/ping"
if ($ping.status -ne "ok") { throw "Ping failed" }

Write-Host "2/3 POST /query (external emulator may wait up to 60 seconds)"
$body = @{
    cadastral_number = $CadastralNumber
    latitude = 56.8389
    longitude = 60.6057
} | ConvertTo-Json

$query = Invoke-RestMethod `
    -Method Post `
    -Uri "$ApiUrl/query" `
    -ContentType "application/json" `
    -Body $body `
    -TimeoutSec 75

if ($query.status -ne "completed") { throw "Query did not complete" }
Write-Host "request_id=$($query.id), result=$($query.result), duration_ms=$($query.duration_ms)"

Write-Host "3/3 GET /history"
$encodedNumber = [System.Uri]::EscapeDataString($CadastralNumber)
$history = Invoke-RestMethod -Method Get -Uri "$ApiUrl/history?cadastral_number=$encodedNumber&limit=10&offset=0"
if ($history.total -lt 1) { throw "History is empty" }

Write-Host "+ Smoke test passed"
