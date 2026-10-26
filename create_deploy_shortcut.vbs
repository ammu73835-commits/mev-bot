Set objWSH = CreateObject("WScript.Shell")
Set objShortcut = objWSH.CreateShortcut("C:\Users\romen\Desktop\1-CLICK DEPLOY TO ORACLE.lnk")
objShortcut.TargetPath = "C:\Users\romen\OneDrive\Desktop\all in one bot\DEPLOY_EVERYTHING.bat"
objShortcut.WorkingDirectory = "C:\Users\romen\OneDrive\Desktop\all in one bot"
objShortcut.Description = "Fully Automated Oracle Cloud Deployment"
objShortcut.Save
WScript.Echo "Desktop shortcut created: 1-CLICK DEPLOY TO ORACLE.lnk"