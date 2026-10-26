# 🐧 LINUX DEPLOYMENT GUIDE

---

## ✅ **QUICK START (30 SECONDS):**

```bash
# Option 1: Simple (manual run)
chmod +x run_bots_linux.sh
./run_bots_linux.sh

# Option 2: Professional (systemd service - recommended)
sudo cp mev-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mev-bot
sudo systemctl start mev-bot
sudo systemctl status mev-bot
```

---

## 📋 **WHAT THE SCRIPT DOES:**

```
✅ Checks Python installation
✅ Creates virtual environment
✅ Installs all dependencies
✅ Starts BSC bot (background)
✅ Starts EVM bot (background)
✅ Starts Solana bot (background)
✅ All bots run 24/7 automatically
```

---

## 📋 **SYSTEMD SERVICE (BEST FOR 24/7):**

```bash
# Install service
sudo cp mev-bot.service /etc/systemd/system/

# Enable auto-start on boot
sudo systemctl enable mev-bot

# Start service
sudo systemctl start mev-bot

# Check status
sudo systemctl status mev-bot

# View logs
sudo journalctl -u mev-bot -f

# Restart if needed
sudo systemctl restart mev-bot

# Stop service
sudo systemctl stop mev-bot
```

---

## 📊 **CHECK STATUS:**

```bash
# View logs (simple method)
tail -f bsc.log
tail -f evm.log
tail -f solana.log

# View logs (systemd method)
sudo journalctl -u mev-bot -f

# Check running processes
ps aux | grep python

# View all logs
cat bsc.log evm.log solana.log
```

---

## 📋 **WHAT THE SCRIPT DOES:**

```
✅ Checks Python installation
✅ Creates virtual environment
✅ Installs all dependencies
✅ Starts BSC bot (background)
✅ Starts EVM bot (background)
✅ Starts Solana bot (background)
✅ All bots run 24/7 automatically
```

---

## 🖥️ **SUPPORTED LINUX DISTROS:**

```
✅ Ubuntu 20.04/22.04 (recommended)
✅ Debian 11/12
✅ Linux Mint
✅ Kali Linux
✅ Pop!_OS
✅ Oracle Cloud Ubuntu (FREE tier)
✅ Any apt-based distro
```

---

## ☁️ **ORACLE CLOUD DEPLOY (OPTIONAL):**

```bash
# If you want to deploy to Oracle Cloud later:
# 1. Create VM (Ubuntu 22.04, 2 OCPU, 24 GB RAM)
# 2. SSH into VM:
ssh -i oracle_key.pem ubuntu@YOUR_VM_IP

# 3. Upload bot files:
scp -i oracle_key.pem -r . ubuntu@YOUR_VM_IP:/home/ubuntu/mev-bot

# 4. Run on VM:
cd /home/ubuntu/mev-bot
./run_bots_linux.sh

# OR use systemd (recommended):
sudo cp mev-bot.service /etc/systemd/system/
sudo systemctl enable mev-bot
sudo systemctl start mev-bot
```

---

## 📊 **CHECK STATUS:**

```bash
# View logs
tail -f bsc.log
tail -f evm.log
tail -f solana.log

# Check running processes
ps aux | grep python

# View all logs
cat bsc.log evm.log solana.log
```

---

## 🛑 **STOP BOTS:**

```bash
# Stop all bots
pkill -f bsc_simple.py
pkill -f evm_simple.py
pkill -f solana_simple.py

# Or stop individually
ps aux | grep bsc_simple.py  # Get PID
kill <PID>
```

---

## 🔄 **RESTART BOTS:**

```bash
# Simply run the script again
./run_bots_linux.sh
```

---

## 💰 **YOUR WALLET ADDRESSES:**

```
MetaMask: 0xb28EB4204fbf139EC0af66d81V7B448921238B10
→ BSC, Arbitrum, Polygon, Base profits

Phantom: E9kXJR36bcrksE8ig6xnGqR3zM2yuHSiLyDNy5KravHf
→ Solana profits
```

---

## ✅ **LINUX ADVANTAGES:**

```
✅ Better performance than Windows
✅ Lower resource usage
✅ More stable 24/7 operation
✅ No Unicode encoding issues
✅ Better network handling
✅ Perfect for servers/VPS
```

---

**🚀 RUN: ./run_bots_linux.sh**

**Bots will start automatically and run 24/7!**