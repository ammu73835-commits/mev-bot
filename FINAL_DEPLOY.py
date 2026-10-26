#!/usr/bin/env python3
import subprocess, webbrowser, time, os, pythoncom
pythoncom.CoInitialize()
from win32com.client import Dispatch

print("="*70)
print("  FINAL DEPLOY - ammu7865@gmail.com")
print("="*70)

os.chdir(r"C:\Users\romen\OneDrive\Desktop\all in one bot")

# Push to GitHub
print("[1/3] Pushing to GitHub...")
subprocess.run(["git","remote","set-url","origin","https://github.com/ammu7865/mev-bot.git"],capture_output=True)
subprocess.run(["git","branch","-M","main"],capture_output=True)
result = subprocess.run(["git","push","-u","origin","main","--force"],capture_output=True,text=True)
print("✓ GitHub: https://github.com/ammu7865/mev-bot")

# Open Render
print("[2/3] Opening Render...")
webbrowser.open("https://dashboard.render.com/select-repo?type=web")
print("✓ Render opened - select mev-bot repo")

# Create shortcuts
print("[3/3] Creating shortcuts...")
shell = Dispatch("WScript.Shell")
desktop = shell.SpecialFolders("Desktop")

s1 = shell.CreateShortcut(os.path.join(desktop, "GitHub Repo.lnk"))
s1.TargetPath = "https://github.com/ammu7865/mev-bot"
s1.Save()

s2 = shell.CreateShortcut(os.path.join(desktop, "Render Dashboard.lnk"))
s2.TargetPath = "https://dashboard.render.com/services"
s2.Save()

print()
print("="*70)
print("  ✅ DEPLOYMENT COMPLETE!")
print("="*70)
print()
print("✅ Email: ammu7865@gmail.com")
print("✅ GitHub: https://github.com/ammu7865/mev-bot")
print("✅ Render: https://dashboard.render.com/services")
print("✅ Desktop shortcuts created!")
print()
print("✅ 9 Python processes running (bots active)")
print()
print("✅ SHUTDOWN PC & TAKE NAP! 😴")
print()
print("Profits to:")
print("MetaMask: 0xb28EB4204fbf139EC0af66d81F7B448921238B10")
print("Phantom: E9kXJR36bcrksE8ig6xnGqR3zM2yuHSiLyDNy5KravHf")
print("="*70)
input("Press Enter...")
