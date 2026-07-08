; Inno Setup Script for RTX Pharma System
; Requires Inno Setup 6+ (https://jrsoftware.org/isdl.php)

#define MyAppName "RTX - نظام إدارة الصيدلية"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "RTX"
#define MyAppURL "https://github.com/alfryasr42-sudo/pharma"
#define MyAppExeName "PharmaSys.exe"
; Build 32-bit (x86) for Windows 7 compatibility
; Source path: dist_x86\PharmaSys.exe + api-ms-win-core-path-l1-1-0.dll
#define MyAppAssocName MyAppName + " File"

[Setup]
AppId={{B8F4A3D2-5E7C-4A9B-8D1F-2C3E4F5A6B7C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\RTX Pharma
DisableProgramGroupPage=yes
DisableDirPage=no
PrivilegesRequired=admin
OutputDir=dist
OutputBaseFilename=RTX_Setup_v{#MyAppVersion}
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "arabic"; MessagesFile: "compiler:Languages\Arabic.isl"

[Tasks]
Name: "desktopicon"; Description: "إنشاء اختصار على سطح المكتب"; GroupDescription: "اختصارات:"; Flags: checkedonce

[Files]
Source: "dist_x86\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist_x86\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{autostartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "تشغيل النظام"; Flags: postinstall nowait skipifsilent shellexec

[UninstallRun]
Filename: "{cmd}"; Parameters: "/C taskkill /F /IM PharmaSys.exe 2>NUL"; Flags: hidden runhidden

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Create data directory for first run
    if not DirExists(ExpandConstant('{app}\data')) then
      CreateDir(ExpandConstant('{app}\data'));
  end;
end;
