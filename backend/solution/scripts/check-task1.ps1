# Proves Task 1 against the running API and mock CRM.
# Start both servers first, then from backend/solution:
#   powershell -ExecutionPolicy Bypass -File .\scripts\check-task1.ps1

$ErrorActionPreference = "Stop"
$api = "http://127.0.0.1:3000"
$crm = "http://127.0.0.1:4002"
$failures = @()

function Set-CrmMode([string]$mode) {
    $file = Join-Path $env:TEMP "crm-mode.json"
    Set-Content -Path $file -Value "{`"mode`":`"$mode`"}" -Encoding ascii -NoNewline
    $response = (curl.exe -s -X POST "$crm/__control" -H "Content-Type: application/json" --data-binary "@$file") -join "`n"
    $parsed = $response | ConvertFrom-Json
    if ($parsed.mode -ne $mode) {
        throw "Could not set CRM mode to $mode. Response: $response"
    }
}

function Invoke-Api([string]$path) {
    $file = Join-Path $env:TEMP "task1-body.json"
    $meta = curl.exe -s -o $file -w "%{http_code} %{time_total}" "$api$path"
    $parts = $meta.Trim() -split "\s+"
    $body = Get-Content -Path $file -Raw
    $json = $null
    if ($body) {
        $json = $body | ConvertFrom-Json
    }
    [pscustomobject]@{
        Status  = [int]$parts[0]
        Seconds = [double]::Parse($parts[1], [cultureinfo]::InvariantCulture)
        Json    = $json
        Raw     = $body
    }
}

function Add-Check([string]$name, [bool]$passed, [string]$detail) {
    if ($passed) {
        Write-Host "PASS  $name"
    } else {
        Write-Host "FAIL  $name  $detail"
        $script:failures += $name
    }
}

function Assert-Schema($json) {
    $fields = @(
        "portfolioId", "clientId", "label", "currency", "totalMarketValue",
        "dayChangeAmount", "dayChangePercent", "totalReturnSinceInception", "asOf"
    )
    foreach ($field in $fields) {
        if (-not ($json.PSObject.Properties.Name -contains $field)) {
            return $false
        }
    }
    return $true
}

curl.exe -sf "$api/health" | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "The API is not responding on port 3000."
    exit 1
}
curl.exe -sf "$crm/health" | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "The mock CRM is not responding on port 4002."
    exit 1
}

Set-CrmMode "ok"

$p9001 = Invoke-Api "/portfolios/P-9001"
Add-Check "P-9001 maps the CRM account" (
    $p9001.Status -eq 200 -and
    (Assert-Schema $p9001.Json) -and
    $p9001.Json.portfolioId -eq "P-9001" -and
    $p9001.Json.clientId -eq "abc123" -and
    $p9001.Json.label -eq "Taxable Brokerage" -and
    $p9001.Json.currency -eq "CAD" -and
    $p9001.Json.totalMarketValue -eq 48930 -and
    $p9001.Json.dayChangeAmount -eq 30 -and
    $p9001.Json.totalReturnSinceInception -eq 0.187
) $p9001.Raw

$p9002 = Invoke-Api "/portfolios/P-9002"
Add-Check "P-9002 selects its own account, not the first one" (
    $p9002.Status -eq 200 -and
    $p9002.Json.label -eq "Retirement Account" -and
    $p9002.Json.totalMarketValue -eq 500 -and
    $p9002.Json.dayChangePercent -eq 0 -and
    $p9002.Json.totalReturnSinceInception -eq 0.25
) $p9002.Raw

$empty = Invoke-Api "/portfolios/P-EMPTY"
Add-Check "P-EMPTY keeps real zeros" (
    $empty.Status -eq 200 -and
    $empty.Json.totalMarketValue -eq 0 -and
    $empty.Json.dayChangeAmount -eq 0 -and
    $empty.Json.dayChangePercent -eq 0 -and
    $empty.Json.totalReturnSinceInception -eq 0
) $empty.Raw

$single = Invoke-Api "/portfolios/P-SINGLE"
Add-Check "P-SINGLE maps the other client" (
    $single.Status -eq 200 -and
    $single.Json.clientId -eq "single-client" -and
    $single.Json.label -eq "Single Asset Class" -and
    $single.Json.totalMarketValue -eq 2275
) $single.Raw

$missingId = Invoke-Api "/portfolios/NOPE"
Add-Check "unknown id is 404" (
    $missingId.Status -eq 404 -and
    $missingId.Json.error -eq "not_found"
) $missingId.Raw

Set-CrmMode "missing"
$missingFields = Invoke-Api "/portfolios/P-9001"
Add-Check "missing CRM fields stay null" (
    $missingFields.Status -eq 200 -and
    $null -eq $missingFields.Json.label -and
    $null -eq $missingFields.Json.totalMarketValue -and
    $missingFields.Json.currency -eq "CAD" -and
    $missingFields.Json.dayChangeAmount -eq 30
) $missingFields.Raw

Set-CrmMode "nested"
$nested = Invoke-Api "/portfolios/P-9002"
Add-Check "nested account list still maps" (
    $nested.Status -eq 200 -and
    $nested.Json.portfolioId -eq "P-9002" -and
    $nested.Json.label -eq "Retirement Account"
) $nested.Raw

Set-CrmMode "error"
$errorCase = Invoke-Api "/portfolios/P-9001"
Add-Check "CRM 503 becomes 502" (
    $errorCase.Status -eq 502 -and
    $errorCase.Json.error -eq "crm_unavailable"
) $errorCase.Raw

Set-CrmMode "timeout"
$timeoutCase = Invoke-Api "/portfolios/P-9001"
Add-Check "CRM hang becomes 504 before 10 seconds" (
    $timeoutCase.Status -eq 504 -and
    $timeoutCase.Json.error -eq "crm_timeout" -and
    $timeoutCase.Seconds -lt 9
) "$($timeoutCase.Status) in $($timeoutCase.Seconds)s $($timeoutCase.Raw)"

Set-CrmMode "ok"

Write-Host ""
if ($failures.Count -eq 0) {
    Write-Host "Task 1 passed."
    exit 0
}
Write-Host "Task 1 failed: $($failures -join ', ')"
exit 1
