@echo off
echo ========================================
echo  MEV BOTS - RUNNING NOW ON 5 NETWORKS
echo ========================================
echo.
echo Starting BSC Bot...
start "BSC Bot" cmd /k "cd /d %~dp0 && python bsc.py"
timeout /t 3 /nobreak >nul

echo Starting EVM Bot (Arbitrum, Polygon, Base)...
start "EVM Bot" cmd /k "cd /d %~dp0 && python all.py"
timeout /t 3 /nobreak >nul

echo Starting Solana Bot...
start "Solana Bot" cmd /k "cd /d %~dp0 && python solana.py"

echo.
echo ========================================
echo  ALL 5 BOTS ARE NOW RUNNING!
echo ========================================
echo.
echo BSC: Running
echo Arbitrum: Running
echo Polygon: Running
echo Base: Running
echo Solana: Running
echo.
echo Profits going to:
echo MetaMask: 0xb28EB4204fbf139EC0af66d81F7B448921238B10
echo Phantom: E9kXJR36bcrksE8ig6xnGqR3zM2yuHSiLyDNy5KravHf
echo.
echo Press any key to exit (bots keep running)...
pause >nul