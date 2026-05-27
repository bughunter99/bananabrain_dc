//Types
//BOOL=32bit boolean, b=0 => false, all other => true
//PChar=char*
//  * When passed to a function the destination is only valid until the called function terminates
//  * When the plugin has to change the data, change it at the destination, not the pointer itself
//  * For writable PChars the buffersize is given. One additional byte for \0 is available
//All callingconventions are Standard Call
//Be carefull and don't write to fields  which are marked as readonly
//If your plugin need additional files use the PluginPath you get passed in LoadInfo/InjectedInfo to locate them. Don't assume the plugin is in the same directory as the launcher or Starcraft.

type TCommandCallback=procedure(Command:PChar;var Handled:BOOL;UserData:pointer);stdcall;
type TCallbackHandle:Cardinal;

type TDisplayLocalTextMessageFunc=procedure(Msg:PChar);stdcall;
     TRegisterCallbackFunc       =function (Event:PChar;CallBack:pointer;UserData:pointer;Priority:integer):TCallbackHandle;stdcall;
     TUnRegisterCallbackFunc     =function (CallbackHandle:TCallbackHandle);stdcall;
     TPluginCompatibilityCheckCallback=procedure(var Compatibility:integer;const Info:TPluginCompatibilityCheckInfo;const PluginInfo:TPluginInfo;UserData:pointer);stdcall;
     TAddLadderFunc              =function AddLadder(Name:PChar;const GameVersion:TVersion;PluginCompatibilityCheck:TPluginCompatibilityCheckCallback;UserData:pointer):BOOL;stdcall;
type TVersion=packed array[0..3]of Word;

type TPluginCompatibilityCheckInfo=packed record
  StructSize:Cardinal;//sizeof(TPluginCompatibilityCheckInfo)
  LauncherApiMajor:Word;//Major version of LauncherAPI, Must be equal to expected version
  LauncherApiMinor:Word;//Minor version of LauncherAPI, Must more or equal than the expected version
  PluginExecutable:PChar;//Absolute Path to checked Plugin including Filename
  PluginPath:PChar;//Absolute Path to checked Plugin
  GameVersion:TVersion;
end;
 
type TLoadInfo=packed record//All readonly
  StructSize:Cardinal;//sizeof(TLoadInfo)
  LauncherApiMajor:Word;//Major version of LauncherAPI, Must be equal to expected version
  LauncherApiMinor:Word;//Minor version of LauncherAPI, Must more or equal than the expected version
  LauncherExecutable:PChar;//Absolute Path to Launcher including Filename
  LauncherPath:PChar;//Absolute Path to launcher
  PluginExecutable:PChar;//Absolute Path to Plugin including Filename
  PluginPath:PChar;//Absolute Path to Plugin
  GamePath:PChar;//Absolute Path to Starcraft
  AddLadderFunc:TAddLadderFunc;//Function published by Launcher which allows adding custom ladders
end;

Type TRunInfo=packed record//All readonly
  StructSize:Cardinal;//sizeof(TRunInfo)
  LauncherApiMajor:Word;//see TLoadInfo
  LauncherApiMinor:Word;//see TLoadInfo
  LauncherExecutable:PChar;//see TLoadInfo
  LauncherPath:PChar;//see TLoadInfo
  PluginExecutable:PChar;//see TLoadInfo
  PluginPath:PChar;//see TLoadInfo
  GamePath:PChar;//see TLoadInfo
  GameExecutable:PChar;//Absolute Path to Starcraft including Filename
  GameVersion:TVersion;//executed Game Version
  GameProcessID:Cardinal;//Process ID of the game
  GameProcessHandle:THandle;//Plugin is responsable for closing the handle!!!
  GameMainThreadID:Cardinal;//ThreadID of MainThread of the game
  GameMainThreadHandle:THandle;//Plugin is responsable for closing the handle!!!
  IsLateActivation:BOOL;//Game already resumed? i.e. passive Mode
  RegisterCallback:TRegisterCallbackFunc;//function published by the launcher to register a callback at some events
  UnregisterCallback:TUnregisterCallbackFunc;//function published by the launcher to unregister a callback
end;

Type TInjectedInfo=packed record//All readonly
  StructSize:Cardinal;//sizeof(TInjectedInfo)
  LauncherApiMajor:Word;//see TLoadInfo
  LauncherApiMinor:Word;//see TLoadInfo
  LauncherExecutable:PChar;//see TLoadInfo
  LauncherPath:PChar;//see TLoadInfo
  PluginExecutable:PChar;//see TLoadInfo
  PluginPath:PChar;//see TLoadInfo
  GamePath:PChar;//see TLoadInfo
  GameExecutable:PChar;//see TRunInfo
  GameVersion:TVersion;//see TRunInfo
  GameProcessID:Cardinal;//see TRunInfo
  GameProcessHandle:THandle;//see TRunInfo, can be Pseudohandle to current Process
  GameMainThreadID:Cardinal;//see TRunInfo
  GameMainThreadHandle:THandle;//see TRunInfo
  IsLateActivation:BOOL;//see TRunInfo
  RegisterCallback:TRegisterCallbackFunc;//see TRunInfo
  UnregisterCallback:TUnregisterCallbackFunc;//see TRunInfo
  DisplayLocalTextMessage:TDisplayLocalTextMessageFunc;//Displays a textmessage only visible to the local user
end;

Type TPluginInfo=packed record
  StructSize:Cardinal;//READONLY, sizeof(TPluginInfo)
  PluginName:PChar;//RW, 256 bytes Memory
  VersionName:PChar;//RW, 256 bytes Memory, Auto prefilled from Versioninfo-Ressource
  Version:TVersion;//RW, Auto prefilled from Versioninfo-Ressource
  Author:PChar;//RW, 256 bytes Memory
  Description:PChar;//RW, 64k bytes Memory
  UpdateUrl:PChar;//RW, 1024 bytes Memory
  PublicKey:PChar;//RW, 2048 bytes Memory
  BanRisk:integer;//RW, 0=low(no injection),1=medium(injection but no hooks or hooks outside Game-Code),2=high(hooks),-1 Unknown
  IndependentModule:BOOL;//RW, Continues working after launcher terminates
  NeedsInjection:BOOL;//RW,Should the launcher inject the plugin?
  AllowLateActivation:BOOL;//RW, Allow late execution when Starcraft already runs
  NonHooking:BOOL;//RW, Hooks no starcraft functions, be carefull in conjunction with RegisterCallback, as that can add hooks too
  GivesAdvantage:BOOL;//RW, For plugins like BWCoach, also makes the plugin incompatible with ICCup etc
  HasConfig:BOOL;//RW, Plugin has a config
end;

type TInjectedPluginInfo=packed record
  StructSize:Cardinal;//READONLY, sizeof(TInjectedPluginInfo)
end;

//Called when the launcher loads the plugin in the process of the launcher
function Chl1_Load(const LoadInfo:TLoadInfo;var PluginInfo:TPluginInfo):BOOL;stdcall;
begin
  result:=false;
  //Check API versions
  if (LoadInfo.LauncherApiMajor<>WANTED_MAJOR)or(LoadInfo.LauncherApiMinor<WANTED_MINOR)then exit;//failure=>return false
  //Fill PluginInfo
  if (PluginInfo.StructSize<sizeof(TPluginInfo))then exit;//failure=>return false;
  StrPLCopy(PluginInfo.PluginName,'SamlePlugin',256);
  StrPLCopy(PluginInfo.Version,'0.1',256);
  StrPLCopy(PluginInfo.Author,'PluginMaker');
  StrPLCopy(PluginInfo.Description,'Boring plugin which does nothing :(',$10000);//64k
  //StrPLCopy(PluginInfo.UpdateUrl,'http://www.example.com/PluginUpdate',1024);//Update formatspecification will be published later
  //StrPLCopy(PluginInfo.PublicKey,'KeyData',2048);//Signature for Update, published later
  PluginInfo.BanRisk:=0;//0=low(no injection),1=medium(injection but no hooks or hooks outside Game-Code),2=high(hooks)
  PluginInfo.IndependentModule:=false;//Continues working after launcher terminates
  PluginInfo.NeedsInjection:=false;//Should the launcher inject the plugin?
  PluginInfo.AllowLateActivation:=true;//Allow late execution when Starcraft already runs
  PluginInfo.NonHooking:=true;//Hooks no starcraft functions, be carefull in conjunction with RegisterCallback, as that can add hooks too
  PluginInfo.GivesAdvantage:=false;//For plugins like BWCoach, also makes the plugin incompatible with ICCup etc
  PluginInfo.Compatibility:=1 shl 10{=1.15.2};//Bitfield for Versions
  PluginInfo.HasConfig:=true;

  //Create a copy of the passed variables in LoadInfo and PluginInfo. The pointers(PChar) become invalid after this function exits.
  //todo
  
  //Do general initialization of your plugin here
  
  result:=true;//OK
end;


function Chl1_Injected(const InjectedInfo:TInjectedInfo;var InjectedPluginInfo:TInjectedPluginInfo):BOOL;stdcall;
begin
  //Called after loading the Plugin in the Starcraft process
  //RunInfo.IsLataActivation indicates if the game is still suspended
  //Read Info from InjectedInfo
    //Create a copy of the passed variables in InjectedInfo. The pointers(PChar) become invalid after this function exits.
    //todo
  //Write Info to InjectedPluginInfo
    //Nothing to do here yet
  //Do initialization inside the game Process here.
  //Chl1_Load has not been called for this instance of the Plugin.
  result:=true;//OK
end;

function Chl1_Run(const RunInfo:TRunInfo):BOOL;stdcall;
begin
  //Called when Starcraft has started in the process of the launcher
  //RunInfo.IsLataActivation indicates if the game is still suspended
  //Read Info from RunInfo
    //ToDo
  //Init all game related functions of your plugin here
  result:=true;//OK
end;

procedure Chl1_ShowConfig();stdcall;
begin
  //show config dialog here
end;

procedure Chl1_IsCompatible(var Compatibility:integer;const GameVersion:TVersion;Ladder:PChar);stdcall;
begin
  //return 3 for always on/required, don't use this without a good cause
  //return 2 for fully compatible
  //return 1 for partially compatible
  //return 0 for incompatible
  //Normally you can ignore the Ladder-Param, usefull for plugins which only work on a certain ladder
  if (GameVersion[0]=1)and(GameVersion[1]=15)and(GameVersion[2]=2)and(GameVersion[3]=1)
    then Compatibility:=2//Fully compatible with 1.15.2.1
    else Compatibility:=0;//incompatible with all other versions
end;

exports Chl1_Load,Chl1_Injected,Chl1_Run,Chl1_ShowConfig,Chl1_IsCompatible;