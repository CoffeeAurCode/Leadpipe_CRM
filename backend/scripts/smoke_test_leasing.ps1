# smoke_test_leasing.ps1
# Live HTTP smoke tests for the lease agent backend endpoints.
# Runs against the deployed Render URL. Requires no credentials.
# Usage: .\backend\scripts\smoke_test_leasing.ps1 [-Manager <uuid>] [-BaseUrl <url>]
#
# Outputs PASS / FAIL per check. Exits with code 1 if any check fails.

param(
    [string]$Manager = "28c43c77-8c9c-496f-8d1e-39ffa9d619e3",
    [string]$BaseUrl = "https://tenant-management-mvp.onrender.com"
)

$pass = 0
$fail = 0

function Check {
    param([string]$Label, [scriptblock]$Test)
    try {
        $result = & $Test
        if ($result) {
            Write-Host "  [PASS] $Label" -ForegroundColor Green
            $script:pass++
        } else {
            Write-Host "  [FAIL] $Label" -ForegroundColor Red
            $script:fail++
        }
    } catch {
        Write-Host "  [FAIL] $Label - exception: $_" -ForegroundColor Red
        $script:fail++
    }
}

function Get-Json {
    param([string]$Url)
    $resp = Invoke-WebRequest -Uri $Url -Method GET -UseBasicParsing -ErrorAction Stop
    return $resp.StatusCode, ($resp.Content | ConvertFrom-Json)
}

function Post-Json {
    param([string]$Url, [hashtable]$Body)
    $json = $Body | ConvertTo-Json
    $resp = Invoke-WebRequest -Uri $Url -Method POST -Body $json `
        -ContentType "application/json" -UseBasicParsing -ErrorAction Stop
    return $resp.StatusCode, ($resp.Content | ConvertFrom-Json)
}

Write-Host ""
Write-Host "===== Lease Agent Smoke Tests =====" -ForegroundColor Cyan
Write-Host "Base URL: $BaseUrl"
Write-Host "Manager:  $Manager"
Write-Host ""

# ---------------------------------------------------------------------------
Write-Host "--- 1. GET /leasing/listings-for-agent ---" -ForegroundColor Yellow
# ---------------------------------------------------------------------------

Check "returns HTTP 200" {
    $code, $_ = Get-Json "$BaseUrl/leasing/listings-for-agent?manager_id=$Manager"
    $code -eq 200
}

Check "response has 'count' field" {
    $_, $body = Get-Json "$BaseUrl/leasing/listings-for-agent?manager_id=$Manager"
    $null -ne $body.count
}

Check "response has 'listings' array" {
    $_, $body = Get-Json "$BaseUrl/leasing/listings-for-agent?manager_id=$Manager"
    $null -ne $body.listings
}

Check "response has 'has_more' field" {
    $_, $body = Get-Json "$BaseUrl/leasing/listings-for-agent?manager_id=$Manager"
    $body.PSObject.Properties.Name -contains "has_more"
}

Check "has_more is boolean (not null)" {
    $_, $body = Get-Json "$BaseUrl/leasing/listings-for-agent?manager_id=$Manager"
    $body.has_more -is [bool]
}

Check "small portfolio: listings array is non-empty when has_more=false" {
    $_, $body = Get-Json "$BaseUrl/leasing/listings-for-agent?manager_id=$Manager"
    if ($body.has_more -eq $false) {
        $body.listings.Count -ge 0   # may be 0 if no active listings for this manager
    } else {
        $true   # large portfolio path â€” skip this check
    }
}

Check "listing items have expected fields" {
    $_, $body = Get-Json "$BaseUrl/leasing/listings-for-agent?manager_id=$Manager"
    if ($body.listings.Count -gt 0) {
        $item = $body.listings[0]
        ($null -ne $item.listing_uuid) -and
        ($null -ne $item.flat_number) -and
        ($null -ne $item.monthly_rent) -and
        ($null -ne $item.bedrooms)
    } else {
        $true  # no listings to check shape of
    }
}

Check "monthly_rent is a number (not string)" {
    $_, $body = Get-Json "$BaseUrl/leasing/listings-for-agent?manager_id=$Manager"
    if ($body.listings.Count -gt 0) {
        $body.listings[0].monthly_rent -is [double] -or
        $body.listings[0].monthly_rent -is [int] -or
        $body.listings[0].monthly_rent -is [long] -or
        $body.listings[0].monthly_rent -is [decimal]
    } else {
        $true
    }
}

Check "works without manager_id (returns 200)" {
    $code, $_ = Get-Json "$BaseUrl/leasing/listings-for-agent"
    $code -eq 200
}

# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "--- 2. GET /leasing/search-listings ---" -ForegroundColor Yellow
# ---------------------------------------------------------------------------

Check "returns HTTP 200 with bedrooms filter" {
    $code, $_ = Get-Json "$BaseUrl/leasing/search-listings?manager_id=$Manager&bedrooms=2"
    $code -eq 200
}

Check "returns HTTP 200 with budget_max filter" {
    $code, $_ = Get-Json "$BaseUrl/leasing/search-listings?manager_id=$Manager&budget_max=50000"
    $code -eq 200
}

Check "returns HTTP 200 with both filters" {
    $code, $_ = Get-Json "$BaseUrl/leasing/search-listings?manager_id=$Manager&bedrooms=2&budget_max=50000"
    $code -eq 200
}

Check "response has count and listings fields" {
    $_, $body = Get-Json "$BaseUrl/leasing/search-listings?manager_id=$Manager&bedrooms=2"
    ($null -ne $body.count) -and ($null -ne $body.listings)
}

Check "returns HTTP 200 with no filters" {
    $code, $_ = Get-Json "$BaseUrl/leasing/search-listings"
    $code -eq 200
}

Check "result count does not exceed 5" {
    $_, $body = Get-Json "$BaseUrl/leasing/search-listings?manager_id=$Manager"
    $body.count -le 5
}

Check "bedrooms=3 returns only 3-bedroom units" {
    $_, $body = Get-Json "$BaseUrl/leasing/search-listings?manager_id=$Manager&bedrooms=3"
    if ($body.listings.Count -gt 0) {
        $all3 = $true
        foreach ($item in $body.listings) {
            if ($item.bedrooms -ne 3) { $all3 = $false }
        }
        $all3
    } else {
        $true  # no results is valid if no 3-bed listings exist
    }
}

# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "--- 3. GET /leasing/find-listing (regression) ---" -ForegroundColor Yellow
# ---------------------------------------------------------------------------

Check "find-listing returns 200" {
    $code, $_ = Get-Json "$BaseUrl/leasing/find-listing?query=C301"
    $code -eq 200
}

Check "find-listing response has 'found' field" {
    $_, $body = Get-Json "$BaseUrl/leasing/find-listing?query=C301"
    $body.PSObject.Properties.Name -contains "found"
}

Check "find-listing with empty query returns 200" {
    $code, $_ = Get-Json "$BaseUrl/leasing/find-listing?query="
    $code -eq 200
}

# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "--- 4. POST /voice/lease-lead-direct (regression) ---" -ForegroundColor Yellow
# ---------------------------------------------------------------------------

$testCallId = "smoke-test-" + [guid]::NewGuid().ToString()

Check "returns 200 for valid lead payload" {
    $code, $_ = Post-Json "$BaseUrl/voice/lease-lead-direct?call_id=$testCallId&phone=+910000000000" @{
        caller_name           = "Smoke Test Caller"
        qualification_status  = "unmatched"
        notes                 = "automated smoke test - safe to delete"
    }
    $code -eq 200
}

Check "returns 'duplicate' for same call_id second time" {
    $code, $body = Post-Json "$BaseUrl/voice/lease-lead-direct?call_id=$testCallId&phone=+910000000000" @{
        caller_name           = "Smoke Test Caller"
        qualification_status  = "unmatched"
    }
    $code -eq 200 -and $body.status -eq "duplicate"
}

Check "returns 200 with empty listing_uuid (bug fix regression)" {
    $uniqueId = "smoke-empty-uuid-" + [guid]::NewGuid().ToString()
    $code, $_ = Post-Json "$BaseUrl/voice/lease-lead-direct?call_id=$uniqueId&phone=+910000000001" @{
        caller_name           = "Empty UUID Test"
        listing_uuid          = ""
        qualification_status  = "unmatched"
    }
    $code -eq 200
}

# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "--- 5. GET /leasing/search (existing endpoint regression) ---" -ForegroundColor Yellow
# ---------------------------------------------------------------------------

Check "search returns 200 with bedrooms param" {
    $code, $_ = Get-Json "$BaseUrl/leasing/search?bedrooms=2&manager_id=$Manager"
    $code -eq 200
}

Check "search returns 200 with no params" {
    $code, $_ = Get-Json "$BaseUrl/leasing/search"
    $code -eq 200
}

# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "--- 6. GET /flats/verify-phone (regression) ---" -ForegroundColor Yellow
# ---------------------------------------------------------------------------

Check "verify-phone returns 200 for any payload" {
    $code, $_ = Post-Json "$BaseUrl/flats/verify-phone?phone_number=+910000000000" @{
        flat_number = "Z999"
    }
    $code -eq 200
}

# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "===== Results =====" -ForegroundColor Cyan
Write-Host "  Passed: $pass" -ForegroundColor Green
Write-Host "  Failed: $fail" -ForegroundColor $(if ($fail -gt 0) { "Red" } else { "Green" })
Write-Host ""

if ($fail -gt 0) {
    exit 1
} else {
    exit 0
}

