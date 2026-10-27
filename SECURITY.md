# SECURITY — read this before funding anything

## Incident: keys leaked by committing them to a PUBLIC repository

On **2026-10-26** both wallets were drained. There was no exploit in the strategy:
the private keys were committed to this repository while it was **public**.

Exposed material (still present in the git history):

| File | Secret |
| --- | --- |
| `config/bot_config.json` | `evm_private_key`, `solana_keypair` |
| `phantom_key.json` | Solana secret key |
| `EVERYTHING_READY.md`, `FINAL_STATUS*.md`, `YOUR_COMPLETE_SUMMARY.md`, `✅_FINAL_CLARIFICATION.md` | the same keys, copied into docs |

### Timeline (all UTC, 2026-10-26)

| Time | Event |
| --- | --- |
| 04:34:53 | Commit `824b4e5` created with the keys inside |
| **04:55:20** | Repository published **PUBLIC** on GitHub |
| **04:55:31** | First Solana sweep: 0.2047 SOL → 0.005 SOL |
| 04:55:39 | 0.005 → 0.001 SOL |
| 04:55:42 / 04:55:44 | Two more attempts (fee-only) |
| **04:55:46** | Final sweep: 0.0009 SOL → **0** |
| 07:51:11 | Ethereum: 0-value probe into the now-empty wallet (still watched) |

Every lamport ended at the collector
`9NQWw786tA8gCiU7nXct28yoUssKVZ3kfBT5qUfewrZr`; every EVM chain
(BSC, Polygon, Arbitrum, Base, Ethereum) reads **0 native** with a handful of
outgoing nonces. **11 seconds** elapsed between publication and the first drain
transaction — the signature of an automated GitHub key sweeper, which polls new
public repositories and immediately signs a sweep from every key it finds.

The engine was **dry-run** at the time (`ARB_CONTRACT` undeployed, no repo
secrets), so it could not have sent anything.

## Consequences

* `0xb28EB4204fbf139EC0af66d81F7B448921238B10` (EVM) and
  `E9kXJR36bcrksE8ig6xnGqR3zM2yuHSiLyDNy5KravHf` (Solana) are **burned forever**.
  The sweeper keeps polling them: any future deposit is taken within seconds.
* Scrubbing the files does **not** un-leak the keys — they live in git history,
  in forks and in third-party caches. Rotation is the only fix.

## Rules that now apply

1. **Keys live only in environment variables / GitHub Secrets.** Never in a
   tracked file. `config/bot_config.json` and `phantom_key.json` are now
   git-ignored; copy `config/bot_config.example.json` and keep the copy local.
2. **Repository visibility: public, and that is now safe.** GitHub Actions is
   unlimited-free only on public repos (private = 2,000 min/month, which cannot
   run a 24/7 bot). It is safe because the fresh deployment keys exist ONLY in
   GitHub Secrets (encrypted server-side) and in git-ignored local files. The
   only keys in git history belong to the two burned, always-empty wallets
   above — worthless to any sweeper. The `hooks/pre-commit` secret scan blocks
   any future key from entering a commit.
3. **A new keypair per deployment.** Reusing a leaked key is equivalent to
   publishing it again.
4. **Check before every commit:**

   ```powershell
   git diff --cached | Select-String -Pattern '0x[0-9a-fA-F]{64}|[1-9A-HJ-NP-Za-km-z]{80,}'
   ```

5. **Fund only what the strategy needs.** An exposed key can only ever cost you
   the balance that sits behind it.

## Rotation checklist

```powershell
# 1. brand-new wallets (never reuse the old ones)
python -c "from eth_account import Account; a = Account.create(); print(a.key.hex(), a.address)"
python -c "from solders.keypair import Keypair; k = Keypair(); print(k)"

# 2. store them as repository secrets (private repo only)
gh secret set PRIVATE_KEY --body "0x..."
gh secret set SOLANA_PRIVATE_KEY --body "..."
gh secret set ARB_CONTRACT --body "0x..."   # after deploying ArbExecutor.sol
gh secret set LIVE --body "1"               # removes the dry-run

# 3. make the repo private (removes the history exposure)
gh repo edit ammu73835-commits/mev-bot --visibility private --accept-visibility-change-consequences
```

Until step 2 is complete the engine runs **dry-run**: it quotes, applies the
profit gate and never signs.
