# 🚀 ORACLE CLOUD DEPLOYMENT - COMPLETE GUIDE

## ✅ WHAT I'VE DONE FOR YOU:

1. ✅ Fixed websockets library issue
2. ✅ Created requirements.txt for Linux
3. ✅ Updated deployment script
4. ✅ Created desktop shortcut for monitoring
5. ✅ Everything ready for 10-minute deployment

## 📋 YOUR TASK (10 MINUTES TOTAL):

### Step 1: Login to Oracle Cloud (1 min)
```
Go to: https://cloud.oracle.com
Login with your Gmail account
```

### Step 2: Create VM (3 min)
```
1. Click hamburger menu (☰)
2. Compute → Instances → Create Instance
3. Name: mev-bot
4. Image: Ubuntu 22.04
5. Shape: VM.Standard.A1.Flex
6. OCPUs: 2, Memory: 24 GB
7. Generate SSH key pair
8. Download .pem file
9. Click Create
```

### Step 3: Upload Files (2 min)
```
Use WinSCP (easiest):
1. Download: https://winscp.net
2. Install and open
3. New Site → Fill in:
   - Host: Your VM public IP
   - Username: ubuntu
   - Private key: Your .pem file
4. Login
5. Drag mev-bot-deploy.zip to /tmp folder
```

### Step 4: Deploy (2 min)
```
SSH into VM:
ssh -i your-key.pem ubuntu@YOUR_VM_IP

Run deployment:
cd /tmp
unzip mev-bot-deploy.zip
cd deployment
chmod +x complete_deploy_script.sh
./complete_deploy_script.sh
```

### Step 5: Verify (2 min)
```
Check status:
sudo systemctl status mev-bot

View profits:
sudo journalctl -u mev-bot -f | grep -i profit
```

## ✅ DONE!

Bots now run 24/7 on Oracle Cloud!
You can shutdown your PC and take rest!
Profits accumulate in your wallets automatically!
