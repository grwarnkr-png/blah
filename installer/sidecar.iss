; Inno Setup script for Sidecar Desktop.
; Compiled automatically by .github/workflows/build-installer.yml into
; SidecarDesktopSetup.exe. Produces a normal install wizard (no console slit):
; it lays down the project files, makes shortcuts, and offers to run setup.

#define MyAppName "Sidecar Desktop"
#define MyAppVersion "0.1.0"

[Setup]
AppId={{B8F4B2A1-5C3D-4E8F-9A2B-7D1E6F3C9A40}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Sidecar Desktop
DefaultDirName={localappdata}\SidecarDesktop
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=output
OutputBaseFilename=SidecarDesktopSetup
WizardStyle=modern
Compression=lzma2
SolidCompression=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "runsetup"; Description: "Set up now (installs VirtualBox + builds the Windows VM; this takes a while and downloads a few GB)"; GroupDescription: "After installing:"

[Files]
Source: "..\sidecar\*";        DestDir: "{app}\sidecar"; Flags: recursesubdirs ignoreversion
Source: "..\setup\*";          DestDir: "{app}\setup";   Flags: recursesubdirs ignoreversion
Source: "..\docs\*";           DestDir: "{app}\docs";    Flags: recursesubdirs ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}";         Flags: ignoreversion
Source: "..\start-sidecar.cmd";DestDir: "{app}";         Flags: ignoreversion
Source: "..\README.md";        DestDir: "{app}";         Flags: ignoreversion

[Icons]
Name: "{group}\Set up Sidecar Desktop"; Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\setup\auto-setup.ps1"""; \
  WorkingDir: "{app}\setup"; Comment: "Install VirtualBox + build the VM"
Name: "{group}\Troubleshooting"; Filename: "{app}\docs\TROUBLESHOOTING.md"
Name: "{group}\Uninstall Sidecar Desktop"; Filename: "{uninstallexe}"
Name: "{userdesktop}\Set up Sidecar Desktop"; Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\setup\auto-setup.ps1"""; \
  WorkingDir: "{app}\setup"; Tasks: desktopicon

[Run]
Filename: "powershell.exe"; \
  Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\setup\auto-setup.ps1"""; \
  WorkingDir: "{app}\setup"; \
  Description: "Set up Sidecar Desktop now"; \
  Flags: nowait postinstall skipifsilent; Tasks: runsetup
