#define MyAppName "OpenDesk"
#define MyAppVersion "1.0"
#define MyAppPublisher "Saúl Méndez"
#define MyAppExeName "OpenDesk.exe"

[Setup]
AppId={{9B3F9E3F-0C3F-4E1B-9F3A-2B3D1A7D9E11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
PrivilegesRequired=admin
OutputDir=C:\Users\saul.mendez\Documents\OpenDesk\installer
OutputBaseFilename=OpenDeskSetup
SetupIconFile=C:\Users\saul.mendez\Documents\OpenDesk\assets\icons\opendesk.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "C:\Users\saul.mendez\Documents\OpenDesk\dist\OpenDesk\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\OpenDesk"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\OpenDesk"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir OpenDesk"; Flags: nowait postinstall skipifsilent