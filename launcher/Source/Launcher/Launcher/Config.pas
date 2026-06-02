unit Config;

interface
uses windows,inifiles,registry,sysutils,launcher_game;

Type TSettings=record
      StartMinimized:boolean;
      MinimizeOnRun:boolean;
      RunScOnStartup:boolean;
      GameDataPort:integer;
      Autoupdate:boolean;
      WarnNoAdmin:boolean;
      procedure Load;
      procedure Save;
    end;
    
var Settings:TSettings;
  ini:TCustomIniFile;
implementation

function GetLauncherIniFilePath: String;
var ExeName: String;
begin
  ExeName:=ChangeFileExt(ExtractFileName(ParamStr(0)), '');
  if ExeName=''
    then ExeName:='Chaoslauncher';
  result:=IncludeTrailingPathDelimiter(ExtractFilePath(ParamStr(0)))+ExeName+'.ini';
end;

{ TSettings }

procedure TSettings.Load;
var reg:TRegistry;
begin
  StartMinimized:=ini.ReadBool('Launcher','StartMinimized',false);
  MinimizeOnRun:=ini.ReadBool('Launcher','MinimizeOnRun',false);
  RunScOnStartup:=ini.ReadBool('Launcher','RunScOnStartup',false);
  AutoUpdate:=ini.ReadBool('Launcher','AutoUpdate',false);
  WarnNoAdmin:=ini.ReadBool('Launcher','WarnNoAdmin',true);
  reg:=nil;
  try
    reg:=TRegistry.create;
    reg.RootKey:=HKEY_CURRENT_USER;
    reg.OpenKeyReadOnly('Software\Battle.net\Configuration');
    if reg.ValueExists('Game Data Port')
      then Settings.GameDataPort:=reg.ReadInteger('Game Data Port')
      else Settings.GameDataPort:=6112;
  finally
    reg.free;
  end;
end;

procedure TSettings.Save;
var reg:TRegistry;
begin
  ini.WriteBool('Launcher','StartMinimized',StartMinimized);
  ini.WriteBool('Launcher','MinimizeOnRun',MinimizeOnRun);
  ini.WriteBool('Launcher','RunScOnStartup',RunScOnStartup);
  ini.WriteBool('Launcher','AutoUpdate',Autoupdate);
  ini.WriteBool('Launcher','WarnNoAdmin',WarnNoAdmin);
  reg:=nil;
  try
    reg:=TRegistry.create;
    reg.RootKey:=HKEY_CURRENT_USER;
    reg.OpenKey('Software\Battle.net\Configuration',true);
    reg.WriteInteger('Game Data Port',Settings.GameDataPort);
  finally
    reg.free;
  end;
end;

initialization
  ini:=TIniFile.create(GetLauncherIniFilePath);
finalization
  ini.free;
  ini:=nil;
end.
