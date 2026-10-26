Set objWSH = CreateObject("WScript.Shell")
Set objShortcut = objWSH.CreateShortcut("C:\Users\romen\Desktop\MEV Bot Status Monitor.lnk")
objShortcut.TargetPath = "C:\Users\romen\OneDrive\Desktop\all in one bot\CHECK_BOT_STATUS.bat"
objShortcut.WorkingDirectory = "C:\Users\romen\OneDrive\Desktop\all in one bot"
objShortcut.Description = "MEV Bot Status Monitor - Check your bots anytime"
objShortcut.Save
WScript.Echo "Desktop shortcut created successfully!"