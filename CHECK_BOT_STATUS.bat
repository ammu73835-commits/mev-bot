@echo off
chcp 65001 >nul
title MEV Bot Status Monitor
cls

:MAIN_LOOP
cls
echo ========================================
echo   MEV BOT STATUS MONITOR
echo   Real-time Status & Profits
echo ========================================
echo.
echo [STATUS CHECK - %date% %time%]
echo.

REM Check if launcher is running
tasklist | findstr /i "python" >nul
if %errorlevel% equ 0 (
    echo [OK] Python bots are RUNNING
) else (
    echo [!] Python not running - Start with AUTOMATED_LAUNCHER.py
)

echo.
echo --- BOT LOGS (Last 20 lines) ---
echo.

REM Show last 20 lines of log
if exist logs\launcher.log (
    powershell -Command "Get-Content 'logs\launcher.log' -Tail 20"
) else (
    echo [!] No logs yet - Bots starting...
)

echo.
echo ========================================
echo [F] View profits only
echo [R] Refresh status
echo [Q] Quit
echo ========================================
choice /C FRQ /N /M "Select option"
if errorlevel 3 goto END
if errorlevel 2 goto MAIN_LOOP
if errorlevel 1 goto PROFITS

:PROFITS
cls
echo ========================================
echo   PROFIT LOGS
echo ========================================
echo.
powershell -Command "Get-Content 'logs\launcher.log' | Select-String 'profit|Profit|PROFIT|extracted|Extracted|EXTRACTED|success|Success|SUCCESS'"
echo.
choice /C BK /N /M "[B]ack or [K]eep viewing"
if errorlevel 2 goto PROFITS
goto MAIN_LOOP

:END
exit