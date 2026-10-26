#!/usr/bin/env python3
"""
MEV BOT - LIVE STATUS (local PC + GitHub cloud)
Shows: local bot processes, cloud (GitHub Actions) runs, repo link.
"""
import json
import os
import subprocess
import sys

REPO = "ammu73835-commits/mev-bot"
ACTIONS_URL = f"https://github.com/{REPO}/actions"


def count_local_python():
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=20,
        ).stdout
        return len([l for l in out.splitlines() if l.strip().startswith('"python.exe"')])
    except Exception:
        return -1


def cloud_runs(limit=5):
    try:
        out = subprocess.run(
            ["gh", "run", "list", "--repo", REPO, "--limit", str(limit),
             "--json", "status,conclusion,createdAt,displayTitle,url,databaseId"],
            capture_output=True, text=True, timeout=45,
        ).stdout
        return json.loads(out) if out.strip().startswith("[") else []
    except Exception:
        return []


def main():
    local = count_local_python()
    runs = cloud_runs()

    print("=" * 74)
    print("  MEV BOT - LIVE STATUS REPORT")
    print("=" * 74)
    print(f"  Repo (cloud):  https://github.com/{REPO}")
    print(f"  Cloud runs:    {ACTIONS_URL}")
    print("-" * 74)

    if local > 0:
        print(f"  LOCAL PC      : {local} bot process(es) RUNNING  [PC must stay on]")
    else:
        print("  LOCAL PC      : no bot processes (PC bots stopped)")

    if runs:
        print("-" * 74)
        print("  GITHUB CLOUD  : (runs even when your PC is OFF)")
        for r in runs:
            state = r.get("status") or "?"
            concl = r.get("conclusion") or ""
            stamp = (r.get("createdAt") or "")[:19].replace("T", " ")
            flag = "LIVE " if state == "in_progress" else ("OK   " if concl == "success" else "     ")
            print(f"   [{flag}] {stamp}Z  {state}{('/' + concl) if concl else ''}")
        live = [r for r in runs if r.get("status") == "in_progress"]
        print("-" * 74)
        if live:
            print(f"  >>> CLOUD BOT IS LIVE RIGHT NOW: {live[0]['url']}")
        else:
            print(f"  >>> No run in progress. Next scheduled run takes over automatically.")
    else:
        print("-" * 74)
        print("  GITHUB CLOUD  : could not read runs (gh CLI not logged in?)")

    print("=" * 74)
    print("  Wallet (MetaMask): 0xb28EB4204fbf139EC0af66d81F7B448921238B10")
    print("  Wallet (Phantom) : E9kXJR36bcrksE8ig6xnGqR3zM2yuHSiLyDNy5KravHf")
    print("=" * 74)


if __name__ == "__main__":
    main()
    if "--pause" in sys.argv:
        input("\nPress Enter to close...")
