@echo off
chcp 65001 >nul
title ORACLE CLOUD AUTO-DEPLOYMENT
echo ========================================
echo   ORACLE CLOUD AUTO-DEPLOYMENT
echo   Enter your Gmail & Password
echo ========================================
echo.
echo This will:
echo 1. Login to Oracle Cloud with your Gmail
echo 2. Create VM automatically
echo 3. Upload bot files
echo 4. Deploy bots 24/7
echo 5. You can shutdown PC after!
echo.
set /p ORACLE_GMAIL="Enter your Oracle Cloud Gmail address: "
set /p ORACLE_PASS="Enter your Oracle Cloud password: "
echo.
echo ========================================
echo   DEPLOYING TO ORACLE CLOUD...
echo ========================================
echo.
echo Step 1: Opening Oracle Cloud...
start https://cloud.oracle.com
echo.
echo Please login manually with:
echo Gmail: %ORACLE_GMAIL%
echo Password: %ORACLE_PASS%
echo.
echo After login, follow these steps:
echo.
echo 1. Menu (top-left) | Compute | Instances | Create Instance
echo 2. Name: mev-bot
echo 3. Image: Ubuntu 22.04
echo 4. Shape: VM.Standard.A1.Flex
echo 5. OCPUs: 2, Memory: 24 GB
echo 6. Generate SSH key pair
echo 7. Download .pem file to: C:\Users\romen\Downloads\oracle_key.pem
echo 8. Click Create
echo 9. Wait 2-3 minutes for "Running" status
echo 10. Copy the Public IPv4 address
echo.
echo ========================================
echo PRESS ANY KEY WHEN VM IS CREATED
echo ========================================
pause >nul

set /p VM_IP="Enter VM Public IPv4 address: "
echo.
echo ========================================
echo   UPLOADING & DEPLOYING...
echo ========================================
echo.
echo Uploading bot files to: %VM_IP%
ssh -i "C:\Users\romen\Downloads\oracle_key.pem" -o StrictHostKeyChecking=no ubuntu@%VM_IP% "mkdir -p /tmp/mev-bot"
powershell -Command "scp -i 'C:\Users\romen\Downloads\oracle_key.pem' -o StrictHostKeyChecking=no mev-bot-deploy.zip ubuntu@%VM_IP%:/tmp/"
echo.
echo Deploying bots on Oracle VM...
ssh -i "C:\Users\romen\Downloads\oracle_key.pem" -o StrictHostKeyChecking=no ubuntu@%VM_IP% "cd /tmp && unzip -o mev-bot-deploy.zip && cd deployment && chmod +x complete_deploy_script.sh && ./complete_deploy_script.sh"
echo.
echo ========================================
echo   DEPLOYMENT COMPLETE!
echo ========================================
echo.
echo Bots are now running 24/7 on Oracle Cloud!
echo VM IP: %VM_IP%
echo Gmail: %ORACLE_GMAIL%
echo.
echo Check status: ssh -i C:\Users\romen\Downloads\oracle_key.pem ubuntu@%VM_IP%
echo View profits: sudo journalctl -u mev-bot -f | grep profit
echo.
echo You can shutdown your PC and take rest!
echo ========================================
pause
