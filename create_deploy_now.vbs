Set objWSH = CreateObject("WScript.Shell")
Set objShortcut = objWSH.CreateShortcut("C:\Users\romen\Desktop\DEPLOY NOW.lnk")
objShortcut.TargetPath = "C:\Users\romen\OneDrive\Desktop\all in one bot\SIMPLE_DEPLOY.bat"
objShortcut.WorkingDirectory = "C:\Users\romen\OneDrive\Desktop\all in one bot"
objShortcut.Description = "Deploy to Oracle Cloud - 10 minutes"
objShortcut.Save
WScript.Echo "Desktop shortcut created: DEPLOY NOW.lnk"