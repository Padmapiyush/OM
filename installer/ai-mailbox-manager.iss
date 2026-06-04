[Setup]
AppName=AI Mailbox Manager
AppVersion=0.1.0
DefaultDirName={localappdata}\AI Mailbox Manager
DefaultGroupName=AI Mailbox Manager
OutputBaseFilename=AI-Mailbox-Manager-Setup
Compression=lzma
SolidCompression=yes

[Files]
Source: "..\backend\*"; DestDir: "{app}\backend"; Flags: recursesubdirs ignoreversion
Source: "..\frontend\dist\*"; DestDir: "{app}\frontend"; Flags: recursesubdirs ignoreversion skipifsourcedoesntexist
Source: "..\manifests\outlook-addin.xml"; DestDir: "{app}\manifests"; Flags: ignoreversion

[Icons]
Name: "{group}\Start AI Mailbox Manager"; Filename: "{app}\run-backend.bat"

[Run]
Filename: "{app}\run-backend.bat"; Description: "Start local AI Mailbox Manager service"; Flags: postinstall nowait skipifsilent
