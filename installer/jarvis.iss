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
; The built-in AI makes the app ~2.3 GB, above Inno's 2 GB single-file limit,
; so Setup is split: JARVIS-AI-Setup.exe + JARVIS-AI-Setup-1.bin (keep them together).
DiskSpanning=yes
DiskSliceSize=max
WizardStyle=modern
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
Source: "..\dist\JARVIS-AI\*.gguf"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion nocompression skipifsourcedoesntexist
Source: "..\dist\JARVIS-AI\*.onnx"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion nocompression skipifsourcedoesntexist

[Icons]
Name: "{group}\JARVIS AI"; Filename: "{app}\{#AppExe}"
Name: "{group}\Uninstall JARVIS AI"; Filename: "{uninstallexe}"
Name: "{autodesktop}\JARVIS AI"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon
Name: "{userstartup}\JARVIS AI"; Filename: "{app}\{#AppExe}"; Tasks: startup

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch JARVIS AI"; Flags: nowait postinstall skipifsilent
