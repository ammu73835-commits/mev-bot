@echo off
chcp 65001 >nul
title SIMPLE ORACLE DEPLOYMENT
cls
echo ========================================
echo   SIMPLE ORACLE DEPLOYMENT
echo   Follow the guide - 10 minutes total
echo ========================================
echo.
echo STEP 1: Opening Oracle Cloud...
start https://cloud.oracle.com
echo.
echo ========================================
echo   IN THE BROWSER - DO THIS:
echo ========================================
echo.
echo 1. LOGIN with your Gmail
echo.
echo 2. CREATE VM:
echo    - Menu (top-left) | Compute | Instances | Create
echo    - Name: mev-bot
echo    - Image: Ubuntu 22.04
echo    - Shape: VM.Standard.A1.Flex
echo    - OCPUs: 2, Memory: 24 GB
echo    - Generate SSH key pair
echo    - Download .pem to: C:\Users\romen\Downloads\oracle_key.pem
echo    - Click Create
echo.
echo 3. WAIT 2-3 minutes for "Running" status
echo.
echo 4. COPY the Public IPv4 address
echo.
echo ========================================
pause
echo.
echo ========================================
echo   ENTER VM IP ADDRESS
echo ========================================
set /p VM_IP="VM Public IPv4 (e.g., 129.146.123.45): "
echo.
echo ========================================
echo   UPLOADING FILES...
echo ========================================
cd /d "%~dp0"
powershell -Command "scp -i 'C:\Users\romen\Downloads\oracle_key.pem' -o StrictHostKeyChecking=no mev-bot-deploy.zip ubuntu@%VM_IP%:/tmp/"
echo.
echo ========================================
echo   DEPLOYING BOTS...
echo ========================================
echo This takes 3-5 minutes...
powershell -Command "ssh -i 'C:\Users\romen\Downloads\oracle_key.pem' -o StrictHostKeyChecking=no ubuntu@%VM_IP% 'cd /tmp ^&^& unzip -o mev-bot-deploy.zip ^&^& cd deployment ^&^& chmod +x complete_deploy_script.sh ^&^& ./complete_deploy_script.sh'"
echo.
echo ========================================
echo   DEPLOYMENT COMPLETE!
echo ========================================
echo.
echo Bots running 24/7 on Oracle Cloud!
echo VM IP: %VM_IP%
echo.
echo Check status: ssh -i C:\Users\romen\Downloads\oracle_key.pem ubuntu@%VM_IP%
echo View profits: sudo journalctl -u mev-bot -f | grep profit
echo.
echo You can shutdown PC and take rest!
echo ========================================
pause
