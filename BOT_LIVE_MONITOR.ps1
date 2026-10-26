# ============================================================
#  BOT LIVE MONITOR - checks the cloud engine EVERY SECOND
#  Shows: engine run status, wallet balances, next run timing
#  (The bot runs on GitHub's free cloud 24/7 - no Oracle signup
#   needed; this monitor is your "oracle" on the desktop.)
# ============================================================
$repo  = "ammu73835-commits/mev-bot"
$mm    = "0xb28EB4204fbf139EC0af66d81F7B448921238B10"
$ph    = "E9kXJR36bcrksE8ig6xnGqR3zM2yuHSiLyDNy5KravHf"
$root  = "c:\Users\romen\OneDrive\Desktop\all in one bot"
$script:bsc = "?"; $script:sol = "?"; $lastBalFetch = [datetime]::MinValue

function Fetch-Balances {
    try {
        $body = @{jsonrpc="2.0"; id=1; method="eth_getBalance"; params=@($mm,"latest")} | ConvertTo-Json
        $r = Invoke-RestMethod -Uri "https://bsc-dataseed.binance.org/" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 8
        $hex = [string]$r.result
        $digits = $hex.TrimStart('0','x')
        if (-not $digits) { $script:bsc = 0.0 } else { $script:bsc = [math]::Round([Convert]::ToUInt64($digits, 16) / 1e18, 8) }
    } catch { $script:bsc = "rpc err" }
    try {
        $body = @{jsonrpc="2.0"; id=1; method="getBalance"; params=@($ph)} | ConvertTo-Json
        $r = Invoke-RestMethod -Uri "https://api.mainnet-beta.solana.com" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 8
        $script:sol = [math]::Round([double]$r.result.value / 1e9, 9)
    } catch { $script:sol = "rpc err" }
}

Write-Host "Starting monitor..." -ForegroundColor Cyan
Fetch-Balances
$lastBalFetch = Get-Date

while ($true) {
    Clear-Host
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "   MEV BOT - LIVE CLOUD MONITOR (refresh: every 1 second)" -ForegroundColor Cyan
    Write-Host "   Repo: github.com/$repo" -ForegroundColor DarkCyan
    Write-Host "============================================================" -ForegroundColor Cyan

    # ---- cloud engine status
    try {
        $runs = (gh api "repos/$repo/actions/runs?per_page=15" 2>$null | ConvertFrom-Json)
        $mine = $runs.workflow_runs | Where-Object { $_.name -like "MEV Engine Cloud*" } | Select-Object -First 3
        if (-not $mine) {
            Write-Host " [..] querying cloud runs..." -ForegroundColor Yellow
        }
        foreach ($r in $mine) {
            $age = [int]((Get-Date) - [datetime]$r.created_at).TotalMinutes
            switch ($r.status) {
                "in_progress" {
                    Write-Host (" [RUNNING] run #{0}  (alive {1} min)  profit-gate ACTIVE" -f $r.run_number, $age) -ForegroundColor Green
                }
                "queued" {
                    Write-Host (" [QUEUED ] run #{0}  (starts when current finishes)" -f $r.run_number) -ForegroundColor Yellow
                }
                default {
                    $col = @{ "success" = "DarkGreen"; "failure" = "Red" }[$r.conclusion]; if (-not $col) { $col = "Gray" }
                    Write-Host (" [DONE {0}] run #{1}  ({2} min ago)" -f $r.conclusion, $r.run_number, $age) -ForegroundColor $col
                }
            }
        }
        $active = $mine | Where-Object { $_.status -eq "in_progress" }
        if ($active) {
            Write-Host " >>> CLOUD ENGINE IS LIVE AND SCANNING 5 NETWORKS 24/7 <<<" -ForegroundColor Green
        } else {
            $next = $mine | Where-Object { $_.status -eq "queued" }
            if (-not $next) { Write-Host " >>> waiting for next scheduled run (every 4h cron) <<<" -ForegroundColor Yellow }
        }
    } catch {
        Write-Host " [!] gh api unreachable: $($_.Exception.Message)" -ForegroundColor Red
    }

    # ---- wallets
    Write-Host "------------------------------------------------------------" -ForegroundColor Cyan
    if (((Get-Date) - $lastBalFetch).TotalSeconds -gt 30) { Fetch-Balances; $lastBalFetch = Get-Date }
    if ($script:bsc -is [double] -and $script:bsc -gt 0) {
        Write-Host (" MetaMask BSC : {0} BNB   (live-fire gas available)" -f $script:bsc) -ForegroundColor Green
    } else {
        Write-Host " MetaMask BSC : $script:bsc BNB   (WALLET EMPTY - fund to fire live)" -ForegroundColor Yellow
    }
    if ($script:sol -is [double] -and $script:sol -gt 0) {
        Write-Host (" Phantom SOL  : {0} SOL" -f $script:sol) -ForegroundColor Green
    } else {
        Write-Host " Phantom SOL  : $script:sol SOL  (WALLET EMPTY)" -ForegroundColor Yellow
    }
    Write-Host "------------------------------------------------------------" -ForegroundColor Cyan
    Write-Host " Live logs : https://github.com/$repo/actions" -ForegroundColor DarkCyan
    Write-Host " (Ctrl+C to close)  checked at $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor DarkGray
    Start-Sleep -Seconds 1
}
