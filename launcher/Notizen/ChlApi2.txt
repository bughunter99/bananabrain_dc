//Types 
//BOOL=32bit boolean, b=0 => false, all other => true 
//PChar=char* 
//  * When passed to a function the destination is only valid until the called function terminates 
//  * For writable PChars the buffersize is given. One additional byte for \0 is available 
//All callingconventions are Standard Call 
//Be carefull and don't write to params marked as readonly
//If your module need additional files use the ModulePath you get passed in LoadInfo/InjectedInfo to locate them. Don't assume the module is in the same directory as the launcher or the game. 

type TCommandCallback=procedure(Command:PChar;var Handled:BOOL;UserData:pointer);stdcall; 
type TCallbackHandle:Cardinal; 
type TVersion=packed array[0..3]of Word;

type TGameVersion=record
  StructSize:Cardinal;//sizeof(TGameVersion) 
  Game:PChar;
  Version:TVersion;
 end;
 
type TModuleInfo=packed record
  StructSize:Cardinal;//sizeof(TModuleInfo) 
  Executable:PChar;
  Path:PChar;
 end;
 
type TGameInfo=packed record
  Game:PChar;
  Version:TVersion;
  Executable:PChar;
  Path:PChar;
 end;

type TDisplayLocalTextMessage    =function (Msg:PChar):BOOL;stdcall; 
     TRegisterCallback           =function (Event:PChar;CallBack:pointer;UserData:pointer;Priority:integer):TCallbackHandle;stdcall; 
     TUnRegisterCallbackFunc     =function (CallbackHandle:TCallbackHandle);stdcall; 
     TLadderCompatibilityCheck   =procedure(Compatibility:integer;const Info:TLadderCompatibilityCheckInfo;const PluginInfo:TPluginInfo;UserData:pointer);stdcall; 
     TAddLadder                  =function (Name:PChar;const GameVersion:TGameVersion;PluginCompatibilityCheck:TPluginCompatibilityCheckCallback;UserData:pointer):BOOL;stdcall; 
	 TAddPlugin                  =function (const PluginInfo:TPluginInfo):BOOL;
  
type TLoadInfo=packed record
  StructSize:Cardinal;//sizeof(TLoadInfo) 
  LauncherApiMajor:Word;//Major version of LauncherAPI, Must be equal to expected version 
  LauncherApiMinor:Word;//Minor version of LauncherAPI, Must more or equal than the expected version 
  LauncherExecutable:PChar;//Absolute Path to Launcher including Filename 
  LauncherPath:PChar;//Absolute Path to launcher 
  ModuleExecutable:PChar;//Absolute Path to Module including Filename 
  ModulePath:PChar;//Absolute Path to Module
  DataPath:PChar;//Put any files to which you require write access here
  AddLadder:TAddLadder;//Function published by Launcher which allows adding custom ladders
  AddPlugin:TAddPlugin;//Function published by Launcher which allows to add a plugin
end; 

Type TRunInfo=packed record//All readonly 
  StructSize:Cardinal;//sizeof(TRunInfo) 
  LauncherApiMajor:Word;//see TLoadInfo 
  LauncherApiMinor:Word;//see TLoadInfo 
  LauncherExecutable:PChar;//see TLoadInfo 
  LauncherPath:PChar;//see TLoadInfo 
  ModuleExecutable:PChar;//see TLoadInfo 
  ModulePath:PChar;//see TLoadInfo 
  Game:PChar;//see TLoadInfo
  GamePath:PChar;//see TLoadInfo 
  GameExecutable:PChar;//Absolute Path to the game including Filename 
  GameVersion:TVersion;//executed Game Version 
  GameProcessID:Cardinal;//Process ID of the game 
  GameProcessHandle:THandle;//Handle only valid until function terminates 
  GameMainThreadID:Cardinal;//ThreadID of MainThread of the game 
  GameMainThreadHandle:THandle;//Handle only valid until function terminates 
  IsLateActivation:BOOL;//Game already resumed? i.e. passive Mode 
  RegisterCallback:TRegisterCallbackFunc;//function published by the launcher to register a callback at some events 
  UnregisterCallback:TUnregisterCallbackFunc;//function published by the launcher to unregister a callback 
end; 

Type TPluginInfo=packed record 
  StructSize:Cardinal;//READONLY, sizeof(TPluginInfo) 
  Game:PChar;
  PluginName:PChar;//Set to NIL for autofill from Versioninfo-Ressource
  VersionName:PChar;//Set to NIL for autofill from Versioninfo-Ressource
  Version:TVersion;//Set to 0.0.0.0 for autofill from Versioninfo-Ressource
  Author:PChar;//Set to NIL for autofill from Versioninfo-Ressource("CompanyName") 
  Description:PChar;//Set to NIL for autofill from Versioninfo-Ressource("FileDescription") 
  UpdateUrl:PChar;//Update Url, begins with a special protocolspecifier or NIL for no autoupdate
  PublicKey:PChar;//Key for signed updates, nil for no signatures
  BanRisk:integer;//0=none(no interaction with SC whatsoever),1=low(no injection),2=medium(injection but no hooks or hooks outside Game-Code),3=high(hooks),-1 Unknown 
  IndependentModule:BOOL;//RW, Continues working after launcher terminates 
  NeedsInjection:BOOL;//RW,Should the launcher inject the module?
  AllowLateActivation:BOOL;//RW, Allow late execution when the game already runs 
  NonHooking:BOOL;//RW, Hooks no game functions, be carefull in conjunction with RegisterCallback, as that can add hooks too 
  GivesAdvantage:BOOL;//RW, For plugins like BWCoach, also makes the plugin incompatible with ICCup etc 
  ConfigHandler:TConfigHandler;//Callback for the config button, NIL=No config dialog
  RunHandler:TRunHandler;//Called in launcher process after the game process has been created, but is still suspended, or later if AllowLateActivation is true
  InjectedHandler:TInjectedHandler;//Called in game process directly before the entrypoint of the game is executed, or later if AllowLateActivation is true
  CompatibleHandler:TPluginCompatibleHandler;
end; 

type TInjectedPluginInfo=packed record 
  StructSize:Cardinal;//READONLY, sizeof(TInjectedPluginInfo) 
end; 

//Called when the launcher loads the module in the process of the launcher 
procedure Chl1_LoadModule(const LoadInfo:TLoadInfo);stdcall; 
var PluginInfo:TPluginInfo;
begin 
  result:=false; 
  //Check API versions 
  if (LoadInfo.LauncherApiMajor<>WANTED_MAJOR)or(LoadInfo.LauncherApiMinor<WANTED_MINOR)then exit;//failure=>return false 
  if LoadInfo.StructSize<sizeof(LoadInfo)then exit;//failure
  //Fill PluginInfo 
  fillchar(PluginInfo,sizeof(PluginInfo),0);
  PluginInfo.StructSize:=sizeof(TPluginInfo));
  PluginInfo.Game:='Starcraft';
  PluginInfo.PluginName:='Fastreply Plugin';
  PluginInfo.Version:=nil;//From Versioninfo
  PluginInfo.Author:=nil;//From Versioninfo
  PluginInfo.Description:='Offers a /r command for fast reply';
  PluginInfo.UpdateUrl:='bwl:http://www.example.com/PluginUpdate';
  PluginInfo.PublicKey:=nil;
  PluginInfo.BanRisk:=3;//0=none, does not interact with the game, 1=low(no injection),2=medium(injection but no hooks or hooks outside Game-Code),3=high(hooks) 
  PluginInfo.IndependentModule:=false;//Continues working after launcher terminates 
  PluginInfo.NeedsInjection:=false;//Should the launcher inject the plugin? 
  PluginInfo.AllowLateActivation:=true;//Allow late execution when the game already runs 
  PluginInfo.NonHooking:=true;//Hooks no game functions, be carefull in conjunction with RegisterCallback, as that can add hooks too 
  PluginInfo.GivesAdvantage:=false;//For plugins like BWCoach, also makes the plugin incompatible with ladders 
  PluginInfo.HasConfig:=true;
  PluginInfo.ConfigHandler:=ShowConfig;
  PluginInfo.InjectedHandler:=Injected;
  PluginInfo.RunHandler:=Run;
  PluginInfo.CompatibilityHandler:=IsCompatible;
  //the PChar pointers you pass to RegisterPlugin have to be valid until RegisterPlugin exits. After that the launcher has its own copies of them.
  RegisterPlugin(PluginInfo);

  //Create a copy of the passed variables in LoadInfo The pointers(PChar) become invalid after this function exits. 
  //todo 
  
  //Do general initialization of your module here 
  
  result:=true;//OK 
end; 


function Injected(const InjectedInfo:TInjectedInfo;var InjectedPluginInfo:TInjectedPluginInfo):BOOL;stdcall; 
begin 
  //Called after loading the module in the game process 
  //RunInfo.IsLataActivation indicates if the game is still suspended 
  //Read Info from InjectedInfo 
    //Create a copy of the passed variables in InjectedInfo. The pointers(PChar) become invalid after this function exits. 
    //todo 
  //Write Info to InjectedPluginInfo 
    //Nothing to do here yet
  //Do initialization inside the game Process here. 
  //Chl1_LoadModule has not been called for this instance of the Plugin. 
  result:=true;//OK 
end; 

function Run(const RunInfo:TRunInfo):BOOL;stdcall; 
begin 
  //Called when the game has started in the process of the launcher 
  //RunInfo.IsLataActivation indicates if the game is still suspended 
  //Read Info from RunInfo 
    //ToDo 
  //Init all game related functions of your plugin here 
  result:=true;//OK 
end; 

procedure ShowConfig();stdcall; 
begin 
  //show config dialog here 
end; 

procedure IsCompatible(var Compatibility:integer;const GameVersion:TGameVersion;Ladder:PChar);stdcall; 
begin 
  //return 4 for always on/required, don't use this setting without a good cause 
  //return 3 for fully compatible 
  //return 2 for partially compatible 
  //return 1 for incompatible 
  //return 0 for forbidden, don't use this setting without a good cause 
  //Normally you can ignore the Ladder-Param, usefull for plugins which only work on a certain ladder 
  if (GameVersion[0]=1)and(GameVersion[1]=15)and(GameVersion[2]=2)and(GameVersion[3]=1) 
    then Compatibility:=2//Fully compatible with 1.15.2.1 
    else Compatibility:=0;//incompatible with all other versions 
end; 

exports Chl1_LoadModule;