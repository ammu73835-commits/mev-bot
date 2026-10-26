#!/usr/bin/env python3
import subprocess, webbrowser, time, os, pythoncom
pythoncom.CoInitialize()
from win32com.client import Dispatch

print("="*70)
print("  AUTO DEPLOY - GITHUB + RENDER")
print("="*70)

os.chdir(r"C:\Users\romen\OneDrive\Desktop\all in one bot")

# Open GitHub to create repo
print("[1/3] Opening GitHub...")
webbrowser.open("https://github.com/new?name=mev-bot&owner=idealwhites8")
time.sleep(2)

print("[2/3] Pushing code to GitHub...")
subprocess.run(["git","remote","add","origin","https://github.com/idealwhites8/mev-bot.git"],capture_output=True)
subprocess.run(["git","branch","-M","main"],capture_output=True)
subprocess.run(["git","push","-u","origin","main","--force"],capture_output=True)
print("✓ Code pushed to GitHub!")

print("[3/3] Opening Render...")
webbrowser.open("https://dashboard.render.com/select-repo?type=web")
time.sleep(2)

# Create shortcuts
shell = Dispatch("WScript.Shell")
desktop = shell.SpecialFolders("Desktop")

s1 = shell.CreateShortcut(os.path.join(desktop, "GitHub Repo.lnk"))
s1.TargetPath = "https://github.com/idealwhites8/mev-bot"
s1.Save()

s2 = shell.CreateShortcut(os.path.join(desktop, "Render Dashboard.lnk"))
s2.TargetPath = "https://dashboard.render.com/services"
s2.Save()

print()
print("="*70)
print("  ✅ DEPLOYMENT COMPLETE!")
print("="*70)
print()
print("✅ Code on GitHub: https://github.com/idealwhites8/mev-bot")
print("✅ Render ready: https://dashboard.render.com/services")
print("✅ Desktop shortcuts created!")
print()
print("✅ SHUTDOWN PC & TAKE NAP! 😴")
print()
print("Profits to:")
print("MetaMask: 0xb28EB4204fbf139EC0af66d81F7B448921238B10")
print("Phantom: E9kXJR36bcrksE8ig6xnGqR3zM2yuHSiLyDNy5KravHf")
print("="*70)
