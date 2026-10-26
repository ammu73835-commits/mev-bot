@echo off
echo ========================================
echo   MEV BOT AUTO-START
echo   Extracting Guaranteed Money 24/7
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)

echo.
echo [2/3] Checking configuration...
if not exist "config\bot_config.json" (
    echo Configuration not found!
    echo Running configurator...
    python CONFIGURE_BOTS.py
)

echo.
echo [3/3] Starting MEV Bots...
echo.
echo ========================================
echo   🤖 BOTS ARE NOW RUNNING!
echo   💰 Extracting money from:
echo      - Arbitrum
echo      - Polygon  
echo      - Base
echo      - Solana
echo ========================================
echo.
echo Press Ctrl+C to stop bots
echo.

python AUTOMATED_LAUNCHER.py

pause
