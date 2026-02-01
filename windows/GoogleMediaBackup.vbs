Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\danie\Desktop\Projects\google-media-backup\windows"
WshShell.Run """C:\Users\danie\AppData\Local\Programs\Python\Python311\pythonw.exe"" ""C:\Users\danie\Desktop\Projects\google-media-backup\windows\run.pyw""", 0, False
