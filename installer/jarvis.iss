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
Compression=lzma2/max
SolidCompression=yes
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
Source: "..\dist\JARVIS-AI\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\JARVIS AI"; Filename: "{app}\{#AppExe}"
Name: "{group}\Uninstall JARVIS AI"; Filename: "{uninstallexe}"
Name: "{autodesktop}\JARVIS AI"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon
Name: "{userstartup}\JARVIS AI"; Filename: "{app}\{#AppExe}"; Tasks: startup

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch JARVIS AI"; Flags: nowait postinstall skipifsilent

[Code]
function OllamaInstalled(): Boolean;
begin
  Result := FileExists(ExpandConstant('{localappdata}\Programs\Ollama\ollama.exe'))
         or FileExists(ExpandConstant('{autopf}\Ollama\ollama.exe'));
end;

procedure CurStepChanged(CurStep: TSetupStep);
var R: Integer;
begin
  if (CurStep = ssPostInstall) and (not OllamaInstalled()) then
    if MsgBox('JARVIS needs Ollama for its local AI. Open the Ollama download page now?' + #13#10 +
              'After installing, run:  ollama pull gemma3:1b', mbConfirmation, MB_YESNO) = IDYES then
      ShellExec('open', 'https://ollama.com/download/windows', '', '', SW_SHOWNORMAL, ewNoWait, R);
end;
