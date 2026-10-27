' Silent 24/7 auto-start for the MEV money extractor (no console window).
' Runs MONEY_EXTRACTOR_247.py hidden; logs go to logs\extractor_247.log
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
here = fso.GetParentFolderName(WScript.ScriptFullName)
logFile = here & "\logs\extractor_247.log"
If Not fso.FolderExists(here & "\logs") Then fso.CreateFolder(here & "\logs")
' avoid double-starting: check for the running process first
already = False
Set wmi = GetObject("winmgmts:\\.\root\cimv2")
Set procs = wmi.ExecQuery("SELECT CommandLine FROM Win32_Process WHERE Name = 'python.exe' OR Name = 'pythonw.exe'")
For Each p In procs
    If Not IsNull(p.CommandLine) Then
        If InStr(p.CommandLine, "MONEY_EXTRACTOR_247") > 0 Then already = True
    End If
Next
If Not already Then
    shell.Run "cmd /c cd /d """ & here & """ && python MONEY_EXTRACTOR_247.py >> """ & logFile & """ 2>&1", 0, False
End If
