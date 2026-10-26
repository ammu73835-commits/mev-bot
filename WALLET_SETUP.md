# 💰 WALLET SETUP GUIDE

## Your Current Funds

- **MetaMask**: $31 Polygon (MATIC)
- **Phantom**: $21 Solana (SOL)

## 🎯 Wallet Allocation Strategy

### MetaMask ($31) - Split Across 3 Networks

| Network | Allocation | Purpose | Minimum Gas Reserve |
|---------|-----------|---------|---------------------|
| Arbitrum | ~$10 (0.005 ETH) | Sandwich attacks, arbitrage | 0.002 ETH |
| Polygon | ~$10 (10 MATIC) | High-frequency MEV | 5 MATIC |
| Base | ~$10 (0.005 ETH) | Low gas, good opportunities | 0.002 ETH |

**Total**: $30 used, $1 buffer

### Phantom ($21) - All on Solana

| Network | Allocation | Purpose | Minimum Gas Reserve |
|---------|-----------|---------|---------------------|
| Solana | $21 (~0.14 SOL) | Front-run, JIT liquidity | 0.5 SOL |

**Note**: You may need to add more SOL for optimal operation

## 📝 How to Setup MetaMask for Multiple Networks

### 1. Add Arbitrum Network

**Network Details:**
- Network Name: Arbitrum One
- RPC URL: `https://arb1.arbitrum.io/rpc`
- Chain ID: `42161`
- Currency Symbol: ETH
- Block Explorer: `https://arbiscan.io`

**Steps:**
1. Open MetaMask
2. Click network dropdown → "Add Network" → "Add a network manually"
3. Enter details above
4. Click Save

### 2. Add Base Network

**Network Details:**
- Network Name: Base Mainnet
- RPC URL: `https://mainnet.base.org`
- Chain ID: `8453`
- Currency Symbol: ETH
- Block Explorer: `https://basescan.org`

**Steps:** Same as above

### 3. Polygon Already Added

Should already be in your MetaMask as "Polygon Mainnet"

## 💸 Fund Your Networks

### From Your $31 MATIC on Polygon:

1. **Bridge to Arbitrum:**
   - Go to https://bridge.arbitrum.io
   - Connect MetaMask (on Polygon)
   - Bridge ~0.005 ETH worth to Arbitrum
   - Or use AnyIn bridge for cheaper fees

2. **Bridge to Base:**
   - Go to https://bridge.base.org
   - Connect MetaMask (on Polygon)
   - Bridge ~0.005 ETH worth to Base

3. **Keep on Polygon:**
   - Keep ~10 MATIC on Polygon network

### Alternative: Buy Directly

Use a DEX on each network to buy small amounts:
- Arbitrum: Use Camelot or Uniswap
- Polygon: Use QuickSwap
- Base: Use Aerodrome or Uniswap

## 🔑 Export Private Keys for Bot

### For Each Network:

1. Open MetaMask
2. Switch to the network (Arbitrum/Polygon/Base)
3. Click 3 dots (top right) → Account Details
4. Click "Export Private Key"
5. Enter password
6. **Copy the key** (long string of numbers/letters)

### Add to Bot Configuration:

Edit `evm_bot/main.py`:

```python
private_keys = {
    "arbitrum": "PASTE_ARBITRUM_KEY_HERE",  # No "0x" prefix
    "polygon": "PASTE_POLYGON_KEY_HERE",     # Same key works for all EVM!
    "base": "PASTE_BASE_KEY_HERE"            # Actually same key!
}
```

**Note**: MetaMask uses the same private key across all EVM networks!
You only need ONE key - it works on Arbitrum, Polygon, Base, etc.

## 🟣 Phantom Wallet Setup (Solana)

### Export Keypair:

1. Open Phantom
2. Click 3 dots → Settings
3. Scroll to "Advanced"
4. Click "Export Primary Key Pair"
5. Enter password
6. **Download JSON file**

### Add to Bot:

Edit `solana_bot/main.py`:

```python
await bot.initialize("C:/path/to/your/phantom-key.json")
```

Or copy the key and create a file:

```python
# Create ke.json in project folder
# Paste the key array from Phantom export
```

## ✅ Verification Checklist

Before running bots:

- [ ] MetaMask has ETH on Arbitrum (≥0.002 ETH)
- [ ] MetaMask has MATIC on Polygon (≥5 MATIC)
- [ ] MetaMask has ETH on Base (≥0.002 ETH)
- [ ] Phantom has SOL (≥0.5 SOL)
- [ ] Private key exported and added to bot
- [ ] Keypair JSON path configured for Solana
- [ ] Test with small amounts first!

## 🔒 Security Tips

1. **Use Separate Wallets**: Don't use your main savings wallet
2. **Minimum Funds**: Only add what the bot needs
3. **Monitor Regularly**: Check transactions daily
4. **Withdraw Profits**: Move profits to cold storage weekly
5. **Keep Keys Secret**: Never share private keys

## 🚀 Ready to Start!

Once wallets are funded and keys are configured:

1. Run `python evm_bot/main.py` to test EVM bot
2. Run `python solana_bot/main.py` to test Solana bot
3. Monitor logs for successful transactions
4. Deploy to Oracle Cloud for 24/7 operation

**Good luck! Start extracting profits! 🎯**
