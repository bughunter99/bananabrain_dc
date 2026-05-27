unit Launcher_Game;

interface

const GameName='Starcraft';
      GameShortName='SC';
function GamePath:String;
procedure LoadGameInfo;
procedure SetGamePath(NewPath:String);
function GameFindProcessID:Cardinal;
procedure GameListVersions;

implementation
uses windows,sysutils,registry,plugins,versions,util;

var FGamePath:String;

function GamePath:String;
begin
  result:=FGamePath
end;

procedure UpdateGamePath;
var
  reg:TRegistry;
  installPath:String;
begin
  FGamePath:='';

  // First try the 32-bit registry view because classic StarCraft installs
  // are commonly written there and this launcher is currently built as 64-bit.
  reg:=nil;
  try
    reg:=TRegistry.Create(KEY_READ or KEY_WOW64_32KEY);
    reg.RootKey:=HKEY_LOCAL_MACHINE;
    if reg.OpenKeyReadOnly('SOFTWARE\Blizzard Entertainment\Starcraft') then
    begin
      if reg.ValueExists('InstallPath') then
      begin
        installPath:=reg.ReadString('InstallPath');
        if installPath<>'' then
        begin
          if installPath[length(installPath)]<>'\' then installPath:=installPath+'\';
          FGamePath:=installPath;
          exit;
        end;
      end;
    end;
  finally
    reg.free;
  end;

  // Fallback: native view.
  reg:=nil;
  try
    reg:=TRegistry.Create(KEY_READ or KEY_WOW64_64KEY);
    reg.RootKey:=HKEY_LOCAL_MACHINE;
    if reg.OpenKeyReadOnly('SOFTWARE\Blizzard Entertainment\Starcraft') then
    begin
      if reg.ValueExists('InstallPath') then
      begin
        installPath:=reg.ReadString('InstallPath');
        if installPath<>'' then
        begin
          if installPath[length(installPath)]<>'\' then installPath:=installPath+'\';
          FGamePath:=installPath;
        end;
      end;
    end;
  finally
    reg.free;
  end;
end;

procedure SetGamePath(NewPath:String);
var reg:TRegistry;
begin
  reg:=nil;
  try
    if(NewPath<>'')and
      (NewPath[length(NewPath)]<>'\')
      then NewPath:=NewPath+'\';
    reg:=TRegistry.create;
    reg.RootKey:=HKEY_LOCAL_MACHINE;
    reg.OpenKey('SOFTWARE\Blizzard Entertainment\Starcraft',true);
    reg.WriteString('InstallPath',copy(NewPath,1,length(NewPath)-1));//Remove trailing \
    reg.WriteString('Program',NewPath+'Starcraft.exe');
    FGamePath:=NewPath;
  finally
    reg.free;
  end;
end;

procedure LoadGameInfo;
begin
  UpdateGamePath;
end;

function GameFindProcessID:Cardinal;
var wnd:hwnd;
begin
  wnd:=FindWindow('SWarClass',nil);
  if wnd=0 then result:=0;
  GetWindowThreadProcessId(Wnd, @result);
end;

procedure GameListVersions;
var error:integer;
    SRec:TSearchRec;
    GameVersion:TGameVersion;
begin
  error:=FindFirst(GamePath+'Starcraft*.exe',faAnyFile and not faDirectory,SRec);
  while error=0 do
   begin
    GameVersion.Filename:=GamePath+SRec.Name;
    GameVersion.Version:=stringreplace(GetLocalizedVersionValue(GameVersion.Filename,'ProductVersion'),'Version ','',[]);
    Str_FitZeroTerminated( GameVersion.Version);
    GameVersion.Name:='Starcraft '+GameVersion.Version;
    GameVersion.Ladder:=nil;
    AddGameVersion(GameVersion);
    error:=FindNext(SRec);
   end;
  if (Error<>ERROR_NO_MORE_FILES)and(Error<>ERROR_FILE_NOT_FOUND)and(Error<>ERROR_PATH_NOT_FOUND)
    then MessageBox(0,PChar('Search for Game executables failed '+GetErrorString(Error)), 'Error', MB_OK + MB_ICONSTOP);
end;


begin
  LoadGameInfo;
end.
