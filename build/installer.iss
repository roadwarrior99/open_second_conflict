; Inno Setup script for Second Conflict
; Inno Setup 6.x — https://jrsoftware.org/isinfo.php
;
; After running PyInstaller, compile this script with Inno Setup Compiler
; (iscc.exe) or via the Inno Setup IDE.  The output installer will be placed
; in build\Output\SecondConflict-Setup.exe.

#define AppName      "Second Conflict"
#define AppVersion   "1.0.0"
#define AppPublisher "Second Conflict Project"
#define AppExeName   "Second Conflict.exe"
#define SourceDir    "..\dist\Second Conflict"

[Setup]
AppId={{8F3A2C1D-4B7E-4F9A-A1C2-3D5E6F7A8B9C}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisherURL=https://github.com/
AppSupportURL=https://github.com/
AppUpdatesURL=https://github.com/
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
; Put the installer output in build\Output\
OutputDir=Output
OutputBaseFilename=SecondConflict-Setup
; Request admin rights so the app installs to Program Files
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExeName}
; Minimum Windows version: Windows 7
MinVersion=6.1

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";    Description: "{cm:CreateDesktopIcon}";    GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Everything PyInstaller put in dist\Second Conflict\
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";            Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}";  Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";      Filename: "{app}\{#AppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up any save files the user created inside the install dir
Type: filesandordirs; Name: "{app}\*.sav"