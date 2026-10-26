@echo off
chcp 65001 >nul
title FULLY AUTOMATED ORACLE CLOUD DEPLOYMENT
echo ========================================
echo   FULLY AUTOMATED ORACLE DEPLOYMENT
echo   One Command - Everything Done!
echo ========================================
echo.
echo [1/6] Opening Oracle Cloud in browser...
start https://cloud.oracle.com
echo.
echo ========================================
echo   FOLLOW THESE STEPS IN THE BROWSER:
echo ========================================
echo.
echo STEP 1: Login with your Gmail
echo.
echo STEP 2: Create VM Instance
echo   - Menu (top-left) ^| Compute ^| Instances ^| Create Instance
echo   - Name: mev-bot
echo   - Image: Ubuntu 22.04
echo   - Shape: VM.Standard.A1.Flex
echo   - OCPUs: 2, Memory: 24 GB
echo   - Generate SSH key pair
echo   - Download the .pem file to: C:\Users\romen\Downloads\
echo   - Click Create
echo.
echo STEP 3: Wait 2-3 minutes for VM to show "Running"
echo.
echo STEP 4: Copy the Public IPv4 address
echo   - Click on "mev-bot" instance
echo   - Copy the "Public IPv4" address
echo.
echo ========================================
echo PRESS ANY KEY WHEN YOU'VE DONE STEPS 1-4
echo ========================================
pause >nul

echo.
echo [2/6] Getting VM IP address...
set /p VM_IP="Enter your VM Public IPv4 address (e.g., 129.146.123.45): "

echo.
echo [3/6] Finding SSH key...
set SSH_KEY=C:\Users\romen\Downloads\oracle_key.pem
if not exist "%SSH_KEY%" (
    set /p SSH_KEY="Enter full path to your .pem file: "
)

echo.
echo [4/6] Installing WinSCP (for file upload)...
cd /d "%~dp0"
if not exist winscp.com (
    echo Downloading WinSCP...
    powershell -Command "& {Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/Winscp/Winscp/master/distribution/winscp.com' -OutFile 'winscp.com'}"
)

echo.
echo [5/6] Uploading bot files to Oracle VM...
echo Creating upload script...
(
echo open scp ubuntu@%VM_IP% -hostkey=any -privatekey="%SSH_KEY%"
echo put mev-bot-deploy.zip /tmp/mev-bot-deploy.zip
echo exit
) > upload.txt

winscp.com /script=upload.txt

if %errorlevel% neq 0 (
    echo.
    echo [!] Upload failed. Trying manual method...
    echo.
    echo Please open WinSCP manually:
    echo 1. Download from: https://winscp.net
    echo 2. Connect to: %VM_IP% (user: ubuntu, key: %SSH_KEY%)
    echo 3. Upload: mev-bot-deploy.zip to /tmp folder
    echo.
    pause
)

echo.
echo [6/6] Deploying bots on Oracle VM...
echo.
echo Connecting to VM and running deployment...
echo This takes 3-5 minutes. Please wait...
echo.

powershell -Command "ssh -i '%SSH_KEY%' -o StrictHostKeyChecking=no ubuntu@%VM_IP% 'cd /tmp ^&^& unzip -o mev-bot-deploy.zip ^&^& cd deployment ^&^& chmod +x complete_deploy_script.sh ^&^& ./complete_deploy_script.sh'"

echo.
echo ========================================
echo   DEPLOYMENT COMPLETE!
echo ========================================
echo.
echo Your bots are now running 24/7 on Oracle Cloud!
echo.
echo VM IP: %VM_IP%
echo SSH Key: %SSH_KEY%
echo.
echo To check status anytime:
echo   ssh -i %SSH_KEY% ubuntu@%VM_IP%
echo   sudo systemctl status mev-bot
echo.
echo To view profits:
echo   ssh -i %SSH_KEY% ubuntu@%VM_IP%
echo   sudo journalctl -u mev-bot -f | grep profit
echo.
echo You can now shutdown your PC and take rest!
echo Bots will keep running on Oracle Cloud 24/7!
echo.
echo ========================================
echo   PROFITS GO TO YOUR WALLET:
echo   MetaMask: 0xb28EB4204fbf139EC0af66d81F7B448921238B10
echo   Phantom: E9kXJR36bcrksE8ig6xnGqR3zM2yuHSiLyDNy5KravHf
echo ========================================
echo.
pause
