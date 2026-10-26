@echo off
echo ========================================
echo   ORACLE CLOUD MONITORING DASHBOARD
echo   Real-time Bot Status Check
echo ========================================
echo.

:MENU
echo.
echo Select Option:
echo   1) Check Bot Status (Real-time)
echo   2) View Live Profit Logs
echo   3) Check Wallet Balances
echo   4) View Profit Summary
echo   5) Restart Bots
echo   6) Exit
echo.
set /p choice="Enter choice (1-6): "

if "%choice%"=="1" goto STATUS
if "%choice%"=="2" goto LOGS
if "%choice%"=="3" goto BALANCE
if "%choice%"=="4" goto SUMMARY
if "%choice%"=="5" goto RESTART
if "%choice%"=="6" goto END

goto MENU

:STATUS
echo.
echo ========================================
echo   BOT STATUS CHECK
echo ========================================
echo.
echo Checking EVM Bot (BSC, Arbitrum, Polygon, Base)...
timeout /t 2 /nobreak >nul
type logs\mev_bot.log | findstr /C:"profit" /C:"Front-run" /C:"Sandwich" | more
echo.
echo Checking Solana Bot...
timeout /t 2 /nobreak >nul
type logs\solana_bot.log | findstr /C:"profit" /C:"Front-run" /C:"Whale" | more
echo.
echo ========================================
goto MENU

:LOGS
echo.
echo ========================================
echo   LIVE PROFIT LOGS (Press Ctrl+C to exit)
echo ========================================
echo.
type logs\launcher.log | findstr /C:"profit" /C:"SUCCESS" /C:"extracted"
goto MENU

:BALANCE
echo.
echo ========================================
echo   WALLET BALANCES
echo ========================================
echo.
echo MetaMask: 0xb28EB4204fbf139EC0af66d81F7B448921238B10
echo   - BSC: Check on bscscan.com
echo   - Arbitrum: Check on arbiscan.io
echo   - Polygon: Check on polygonscan.com
echo   - Base: Check on basescan.org
echo.
echo Phantom: E9kXJR36bcrksE8ig6xnGqR3zM2yuHSiLyDNy5KravHf
echo   - Solana: Check on solscan.io
echo.
echo ========================================
goto MENU

:SUMMARY
echo.
echo ========================================
echo   PROFIT SUMMARY
echo ========================================
echo.
echo Total Profits Today:
type logs\launcher.log | findstr /C:"Total:"
echo.
echo ========================================
goto MENU

:RESTART
echo.
echo ========================================
echo   RESTARTING BOTS...
echo ========================================
echo.
taskkill /F /IM python.exe 2>nul
timeout /t 3 /nobreak >nul
start AUTOMATED_LAUNCHER.py
echo Bots restarted!
echo.
goto MENU

:END
exit
