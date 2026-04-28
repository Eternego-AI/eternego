; Inno Setup script — wraps the PyInstaller eternego.exe into a Windows installer.
; Compile from CI: iscc /DAppVersion=v0.1.0-rc1 packaging\windows-installer.iss

#ifndef AppVersion
  #define AppVersion "v0.0.0-dev"
#endif

[Setup]
AppName=Eternego
AppVersion={#AppVersion}
AppPublisher=Eternego AI
AppPublisherURL=https://eternego.ai
DefaultDirName={autopf}\Eternego
DefaultGroupName=Eternego
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=Eternego-{#AppVersion}-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
SetupIconFile=build\icon\eternego.ico
UninstallDisplayIcon={app}\eternego.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "dist\eternego.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Eternego"; Filename: "{app}\eternego.exe"; Parameters: "launch"; IconFilename: "{app}\eternego.exe"
Name: "{group}\Uninstall Eternego"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Eternego"; Filename: "{app}\eternego.exe"; Parameters: "launch"; IconFilename: "{app}\eternego.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\eternego.exe"; Parameters: "launch"; Description: "Launch Eternego now"; Flags: nowait postinstall skipifsilent
