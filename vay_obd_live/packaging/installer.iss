; -----------------------------------------------------------------------
;  Vay OBD Live — Inno Setup script
;
;  Wraps the PyInstaller output (dist\Vay_OBD_Live) into a Windows installer:
;     - installs to Program Files\Vay_OBD_Live
;     - per-user Start Menu entry
;     - optional desktop shortcut (checkbox in installer)
;     - registers an uninstaller in Add/Remove Programs
;
;  Build with: ISCC.exe packaging\installer.iss
;  (build.bat runs this for you.)
; -----------------------------------------------------------------------

#define AppName        "Vay OBD Live"
#define AppShortName   "Vay_OBD_Live"
#define AppVersion     "0.1.0"
#define AppPublisher   "Vay"
#define AppExeName     "Vay_OBD_Live.exe"
; Keep this GUID stable across versions so upgrades are recognized; this
; is the same GUID the previous TSDiag installer used so installs cleanly
; carry over.
#define AppId          "{{B5D7F3C2-1F4E-4B8D-9C2E-7E9F5A3D8B2A}"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://vay.io
DefaultDirName={autopf}\{#AppShortName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\dist_installer
OutputBaseFilename=Vay_OBD_Live-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
UninstallDisplayIcon={app}\{#AppExeName}
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Pull everything from the PyInstaller --onedir output.
Source: "..\dist\Vay_OBD_Live\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";          Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";    Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove anything PyInstaller writes to %LOCALAPPDATA% on launch.
Type: filesandordirs; Name: "{userappdata}\{#AppShortName}"
