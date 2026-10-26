#!/usr/bin/env python3
"""Creates the final desktop shortcuts for the MEV bot (cloud + status)."""
import os

import pythoncom
from win32com.client import Dispatch

pythoncom.CoInitialize()

BASE = r"C:\Users\romen\OneDrive\Desktop\all in one bot"
shell = Dispatch("WScript.Shell")
desktop = shell.SpecialFolders("Desktop")

shortcuts = [
    # name, target, description
    ("MEV CLOUD STATUS.lnk",
     os.path.join(BASE, "CHECK_CLOUD_STATUS.bat"),
     "Live status: local bots + GitHub cloud runs"),
    ("GitHub Cloud Bot.lnk",
     "https://github.com/ammu73835-commits/mev-bot/actions",
     "Watch the bot running on GitHub's cloud + logs"),
    ("RENDER DEPLOY (1 click).lnk",
     "https://render.com/deploy?repo=https://github.com/ammu73835-commits/mev-bot",
     "Optional: deploy the same bot to Render"),
    ("Render Dashboard.lnk",
     "https://dashboard.render.com/",
     "Render dashboard"),
]

for name, target, desc in shortcuts:
    path = os.path.join(desktop, name)
    sc = shell.CreateShortcut(path)
    sc.TargetPath = target
    sc.Description = desc
    sc.WorkingDirectory = BASE
    sc.Save()
    print(f"created: {name} -> {target}")

print("\nAll shortcuts:", len(shortcuts))
for f in sorted(os.listdir(desktop)):
    if f.endswith(".lnk"):
        print("  -", f)
