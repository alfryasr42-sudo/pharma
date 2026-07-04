; Inno Setup Script for PharmaSys
; Download Inno Setup from https://jrsoftware.org/isdl.php
; Compile: right-click this file → Compile

#define MyAppName "PharmaSys"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "alfryasr42"
#define MyAppURL "https://github.com/alfryasr42-sudo/pharma"
#define MyAppExeName "PharmaSys.exe"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=installer
OutputBaseFilename=PharmaSys_Setup_v{#MyAppVersion}
Compression=lzma
SolidCompression=yes
SetupIconFile=resources\icons\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "تشغيل البرنامج"; Flags: postinstall nowait skipifsilent
