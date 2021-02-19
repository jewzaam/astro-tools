Dim oShell
Set objFSO=CreateObject("Scripting.FileSystemObject")

' collect arguments
dim argNo

' Build command string from arguments.  See README.txt for argument requirements.
strCommand = "python ""APT-to-Discord.py"" "

' send first 8 args separately followed by all other args at once.

for argNo = 1 to 8
    strCommand = strCommand & """" & wScript.arguments(argNo-1) & """ "
next

' build "message" argument from all remaining arguments
strCommand = strCommand & " """
for argNo = 9 to wScript.arguments.count
    strCommand = strCommand & wScript.arguments(argNo-1) & " "
next
strCommand = strCommand & """"

' to debug, what command was run
outFile="APT-to-Discord-vbs.log"
Set objFile = objFSO.CreateTextFile(outFile,True)
objFile.Write strCommand & vbCrLf
objFile.Close

Set oShell = WScript.CreateObject ("WScript.Shell")
oShell.run strCommand
Set oShell = Nothing
