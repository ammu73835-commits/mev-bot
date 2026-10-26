@echo off
echo ========================================
echo  DEPLOY TO GOOGLE CLOUD (FREE TIER)
echo ========================================
echo.
echo Step 1: Opening Google Cloud Console...
start https://console.cloud.google.com/compute/instances
echo.
echo Step 2: Instructions:
echo.
echo 1. Create a new VM instance:
echo    - Name: mev-bot
echo    - Region: us-central1 (Iowa)
echo    - Machine Type: e2-micro (FREE)
echo    - Boot Disk: Ubuntu 22.04
echo    - Firewall: Allow HTTP and HTTPS
echo.
echo 2. After VM starts, click "SSH" button
echo.
echo 3. In SSH terminal, paste these commands:
echo.
echo    cd ~
echo    git clone https://github.com/yourusername/mev-bot.git || mkdir mev-bot && cd mev-bot
echo    chmod +x google_cloud_deploy.sh
echo    ./google_cloud_deploy.sh
echo.
echo 4. Check status:
echo    sudo systemctl status mev-bot
echo.
echo 5. View logs:
echo    sudo journalctl -u mev-bot -f
echo.
echo ========================================
echo  Desktop shortcut created: CHECK BOT STATUS.lnk
echo ========================================
echo.
pause
