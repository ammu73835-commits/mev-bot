# Recreates the "BOT LIVE MONITOR" desktop shortcut.
$ws = New-Object -ComObject WScript.Shell
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$lnk = $ws.CreateShortcut("$env:USERPROFILE\Desktop\BOT LIVE MONITOR.lnk")
$lnk.TargetPath = "powershell.exe"
$lnk.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$root\BOT_LIVE_MONITOR.ps1`""
$lnk.WorkingDirectory = $root
$lnk.WindowStyle = 1
$lnk.Description = "MEV Bot live cloud monitor - refreshes every second"
$lnk.Save()
Write-Host "Desktop shortcut created: BOT LIVE MONITOR.lnk"
