@echo off
title MONEY EXTRACTOR 24/7 - profit-locked MEV supervisor
cd /d "%~dp0"
echo ================================================================
echo   MONEY EXTRACTOR 24/7 - starting...
echo   - Fires ONLY when profit gate + on-chain simulation BOTH pass
echo   - Zero gas while wallets are unfunded (auto-detects funding)
echo   - Status: logs\status.json   Fired txs: logs\profit_ledger.json
echo   - Stop: close this window (or Ctrl+C)
echo ================================================================
python MONEY_EXTRACTOR_247.py
pause
