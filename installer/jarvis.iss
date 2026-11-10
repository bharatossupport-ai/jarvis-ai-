; Inno Setup script -> Output\JARVIS-AI-Setup.exe
; Build: run packaging\build_windows.bat (it calls this), or: iscc installer\jarvis.iss
#define AppName "JARVIS AI"
#define AppVersion "1.0.0"
#define AppExe "JARVIS-AI.exe"

[Setup]
AppId={{A4E578BA-23A6-46F5-A3C9-BF7EA6B09266}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Priyanshu
DefaultDirName={autopf}\JARVIS AI
DefaultGroupName=JARVIS AI
OutputDir=..\Output
OutputBaseFilename=JARVIS-AI-Setup
SetupIconFile=..\assets\jarvis.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/fast
SolidCompression=no
; Fully offline installer: the 2 GB built-in AI is inside. Files are capped at 2 GB
; (GitHub and Inno), so Setup is split into JARVIS-AI-Setup.exe + .bin parts.
; Keep all of them in the same folder and run the .exe.
DiskSpanning=yes
DiskSliceSize=1900000000
WizardStyle=modern
; Always let the user choose the install folder
DisableDirPage=no
DisableProgramGroupPage=yes
DisableWelcomePage=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequiredOverridesAllowed=dialog
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "startup"; Description: "Start JARVIS when Windows starts"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "..\dist\JARVIS-AI\*"; DestDir: "{app}"; Excludes: "*.gguf,*.onnx"; Flags: recursesubdirs ignoreversion
; model weights don't compress, so skip compression for speed
Source: "..\models\Hermes-3-Llama-3.2-3B.Q4_K_M.gguf"; DestDir: "{app}\_internal\models"; Flags: ignoreversion nocompression
Source: "..\packaging\redist\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall skipifsourcedoesntexist
Source: "..\dist\JARVIS-AI\*.onnx"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion nocompression skipifsourcedoesntexist

[Icons]
Name: "{group}\JARVIS AI"; Filename: "{app}\{#AppExe}"
Name: "{group}\Uninstall JARVIS AI"; Filename: "{uninstallexe}"
Name: "{autodesktop}\JARVIS AI"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon
Name: "{userstartup}\JARVIS AI"; Filename: "{app}\{#AppExe}"; Tasks: startup

[Run]
; Microsoft C++ runtime used by the built-in AI engine (silent, skipped if already present)
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; StatusMsg: "Installing Microsoft C++ runtime..."; Flags: waituntilterminated skipifdoesntexist
Filename: "{app}\{#AppExe}"; Description: "Launch JARVIS AI"; Flags: nowait postinstall skipifsilent
