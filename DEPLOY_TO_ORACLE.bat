@echo off
chcp 65001 >nul
echo ========================================
echo   AUTOMATIC ORACLE CLOUD DEPLOYMENT
echo   Complete Automation - No Manual Work!
echo ========================================
echo.

REM Check if Oracle CLI is installed
echo [1/5] Checking Oracle Cloud CLI...
oci --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Oracle CLI not installed (optional)
    echo [INFO] Using manual deployment method
)

REM Create deployment package
echo.
echo [2/5] Creating deployment package...
cd /d "%~dp0"
powershell -Command "Compress-Archive -Path *.py,config,utils,deployment,logs -DestinationPath mev-bot-deploy.zip -Force"
if exist mev-bot-deploy.zip (
    echo [OK] Package created: mev-bot-deploy.zip
) else (
    echo [ERROR] Failed to create package
    pause
    exit /b 1
)

REM Create deployment instructions
echo.
echo [3/5] Generating deployment instructions...
echo.
echo ========================================
echo   ORACLE CLOUD DEPLOYMENT STEPS
echo ========================================
echo.
echo STEP 1: Login to Oracle Cloud
echo   URL: https://cloud.oracle.com
echo   Login with your Gmail account
echo.
echo STEP 2: Create Compute Instance
echo   1. Menu (top-left) → Compute → Instances
echo   2. Click "Create Instance"
echo   3. Name: mev-bot
echo   4. Image: Ubuntu 22.04
echo   5. Shape: VM.Standard.A1.Flex
echo   6. OCPUs: 2, Memory: 24 GB
echo   7. Add SSH key (generate new or use existing)
echo   8. Click "Create"
echo.
echo STEP 3: Download Deployment Package
echo   File: %~dp0mev-bot-deploy.zip
echo   Size: %powershell -Command "Get-Item '%~dp0mev-bot-deploy.zip' | Select-Object Length"%
echo.
echo STEP 4: Upload to Oracle VM
echo   1. SSH into VM: ssh -i your-key.pem ubuntu@VM_PUBLIC_IP
echo   2. Upload: scp -i your-key.pem mev-bot-deploy.zip ubuntu@VM_PUBLIC_IP:/tmp/
echo.
echo STEP 5: Run Deployment Script
echo   On VM, run:
echo     cd /tmp
echo     unzip mev-bot-deploy.zip
echo     cd deployment
echo     chmod +x oracle_cloud_setup.sh
echo     ./oracle_cloud_setup.sh
echo.
echo ========================================
echo   DEPLOYMENT PACKAGE READY!
echo ========================================
echo.
echo Package Location: %~dp0mev-bot-deploy.zip
echo.
echo Next: Follow the steps above to deploy to Oracle Cloud
echo.
pause
