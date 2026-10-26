# ⚡ QUICK START GUIDE

## Step 1: Install Dependencies (30 seconds)

```bash
cd "C:\Users\romen\OneDrive\Desktop\all in one bot"
pip install web3==8.0.0 eth-account aiohttp websockets solana==0.30.1
```

## Step 2: Add Your Private Keys

### For EVM Bot (MetaMask - $31 split across 3 networks)

Edit `evm_bot/main.py` line 168-173:

```python
private_keys = {
    "arbitrum": "YOUR_ARBITRUM_PRIVATE_KEY_HERE",     # ~$10 worth
    "polygon": "YOUR_POLYGON_PRIVATE_KEY_HERE",       # ~$10 worth  
    "base": "YOUR_BASE_PRIVATE_KEY_HERE"              # ~$10 worth
}
```

**How to get private keys from MetaMask:**
1. Open MetaMask
2. Click 3 dots → Account Details → Export Private Key
3. Enter password
4. Copy the key (starts with numbers, no "0x")

### For Solana Bot (Phantom - $21 SOL)

Edit `solana_bot/main.py` line 137:

```python
await bot.initialize("path/to/your/phantom/keystore.json")
```

**How to export Phantom keypair:**
1. Open Phantom
2. Settings → Advanced → Export Primary Key Pair
3. Save as JSON file
4. Update path in code

## Step 3: Test Run (1 minute)

```bash
# Test EVM bot
python evm_bot/main.py

# In another terminal, test Solana bot
python solana_bot/main.py
```

Watch the logs for:
- ✅ "Initializing..."
- ✅ "Loaded wallet"
- ✅ "Starting monitoring"

## Step 4: Deploy to Oracle Cloud (5 minutes)

### Create Free Oracle Cloud VM:

1. Go to https://cloud.oracle.com
2. Sign up for free tier
3. Create Compute Instance:
   - **Image**: Ubuntu 22.04
   - **Shape**: VM.Standard.A1.Flex (2 OCPU, 24 GB RAM)
   - **Availability**: Any
4. Add SSH key or use password
5. Launch instance

### Deploy Bots:

```bash
# SSH into your Oracle VM
ssh -i your-key ubuntu@your-vm-ip

# Clone or upload bot files
# Then run:
cd deployment
chmod +x oracle_cloud_setup.sh
./oracle_cloud_setup.sh
```

## Step 5: Monitor Profits

```bash
# Check EVM bot logs
journalctl -u evm-mev-bot -f

# Check Solana bot logs
journalctl -u solana-mev-bot -f

# Check status
systemctl status evm-mev-bot
systemctl status solana-mev-bot
```

## 🎯 What to Expect

**First Hour:**
- Bot initializes and starts monitoring
- May take 5-30 minutes for first opportunity
- Watch for "💰 Sandwich profit" or similar messages

**First Day:**
- 1-10 profitable transactions
- $5-20 total profit (varies by network activity)

**First Week:**
- Bots learn optimal gas prices
- $50-150 total profit expected

## 🔧 Troubleshooting

**"Connection refused" error:**
- Check RPC URLs in config/networks.json
- Try alternative RPC endpoints

**"Insufficient balance" error:**
- Ensure wallet has native token for gas:
  - Arbitrum/Base: 0.01 ETH minimum
  - Polygon: 10 MATIC minimum
  - Solana: 0.5 SOL minimum

**No profits after 24 hours:**
- Increase min_profit threshold in config
- Check network activity (low volume = fewer opportunities)
- Verify private keys are correct

## 📊 Profit Tracking

Profits are logged in:
- `logs/mev_bot.log` - EVM profits
- `logs/solana_bot.log` - Solana profits

Look for lines like:
```
💰 Sandwich profit: $12.45 | Total: $12.45
```

## 🚀 You're Ready!

1. Add private keys
2. Test locally
3. Deploy to Oracle Cloud
4. Watch profits grow!

**Good luck! 🍀**
