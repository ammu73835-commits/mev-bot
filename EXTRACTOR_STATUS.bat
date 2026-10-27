@echo off
title MEV Extractor Status
cd /d "%~dp0"
:loop
cls
echo ================================================================
echo   MEV EXTRACTOR LIVE STATUS   (refreshes every 10s)
echo ================================================================
if exist logs\status.json (type logs\status.json) else (echo no status yet - bot not started)
if exist logs\FUNDING_DETECTED.txt echo. & echo *** FUNDING WAS DETECTED *** & type logs\FUNDING_DETECTED.txt
if exist logs\profit_ledger.json echo. & echo --- FIRED TRANSACTIONS --- & type logs\profit_ledger.json
timeout /t 10 /nobreak >nul
goto loop
