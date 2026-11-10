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
; One single JARVIS-AI-Setup.exe. The 2 GB built-in AI model is too big for one
; installer file (Inno and GitHub both cap files at 2 GB), so Setup downloads it
; automatically during installation. Nothing to install by hand.
ExtraDiskSpaceRequired=2100000000
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
Source: "{tmp}\Hermes-3-Llama-3.2-3B.Q4_K_M.gguf"; DestDir: "{app}\_internal\models"; Flags: external ignoreversion deleteafterinstall
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

[Code]
var
  DownloadPage: TDownloadWizardPage;

function OnDownloadProgress(const Url, FileName: String; const Progress, ProgressMax: Int64): Boolean;
begin
  Result := True;
end;

procedure InitializeWizard;
begin
  DownloadPage := CreateDownloadPage('Downloading JARVIS built-in AI',
    'Hermes 3 (about 2 GB). This happens once; JARVIS then works fully offline.', @OnDownloadProgress);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = wpReady then begin
    DownloadPage.Clear;
    DownloadPage.Add('https://huggingface.co/NousResearch/Hermes-3-Llama-3.2-3B-GGUF/resolve/main/Hermes-3-Llama-3.2-3B.Q4_K_M.gguf',
      'Hermes-3-Llama-3.2-3B.Q4_K_M.gguf', '');
    DownloadPage.Show;
    try
      try
        DownloadPage.Download;
      except
        if DownloadPage.AbortedByUser then
          Log('Download aborted by user.')
        else
          SuppressibleMsgBox('Could not download the built-in AI: ' + AddPeriod(GetExceptionMessage) + #13#10 + 'Check your internet connection and click Next to try again.', mbCriticalError, MB_OK, IDOK);
        Result := False;
      end;
    finally
      DownloadPage.Hide;
    end;
  end;
end;
