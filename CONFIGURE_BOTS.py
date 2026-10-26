"""
QUICK BOT CONFIGURATOR
- Enter your keys once
- Automatically configures everything
- Ready to extract money immediately
"""

import json
from pathlib import Path

def main():
    print("=" * 60)
    print("🤖 MEV BOT CONFIGURATOR")
    print("=" * 60)
    print()
    
    # Get EVM private key
    print("1️⃣  META MASK PRIVATE KEY (EVM Chains)")
    print("   → Export from MetaMask: 3 dots → Account Details → Export Private Key")
    print("   → Same key works for Arbitrum, Polygon, Base")
    evm_key = input("\n   Paste private key (no 0x prefix): ").strip()
    
    if not evm_key:
        print("❌ No key provided!")
        return
    
    # Get Solana keypair
    print("\n2️⃣  PHANTOM KEYPAIR (Solana)")
    print("   → Export from Phantom: Settings → Advanced → Export Primary Key Pair")
    print("   → Save as JSON file, then provide path")
    
    solana_choice = input("\n   Option A: Paste JSON array\n   Option B: Provide file path\n   Choose (A/B): ").strip().upper()
    
    if solana_choice == "A":
        json_array = input("\n   Paste JSON array [123,456,...]: ").strip()
        # Save to file
        keypair_path = Path("phantom_key.json")
        import json as j
        data = j.loads(json_array)
        with open(keypair_path, 'w') as f:
            j.dump(data, f)
        print(f"   ✅ Saved to {keypair_path}")
    else:
        solana_choice = "B"
        keypair_path = input("\n   Provide file path: ").strip()
    
    # Save configuration
    config = {
        "evm_private_key": evm_key,
        "solana_keypair_path": str(keypair_path) if solana_choice == "B" else "phantom_key.json",
        "auto_restart": True,
        "max_retries": 999
    }
    
    config_file = Path("config/bot_config.json")
    config_file.parent.mkdir(exist_ok=True)
    
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("\n" + "=" * 60)
    print("✅ CONFIGURATION COMPLETE!")
    print("=" * 60)
    print("\n🚀 Bots are now configured and ready!")
    print("\n📊 Your wallets:")
    print(f"   EVM: {evm_key[:10]}...{evm_key[-10:]}")
    print(f"   Solana: {config['solana_keypair_path']}")
    print("\n💰 To start extracting money:")
    print("   python AUTOMATED_LAUNCHER.py")
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
