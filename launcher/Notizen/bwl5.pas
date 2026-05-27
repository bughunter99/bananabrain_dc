//   BOOL    =32Bit Boolean type, 0=false, other=true
//   Word    =unsigned 16bit integer
//   Integer =signed pointersized integer
//   Cardinal=unsigned pointersized integer
//   PChar   =pointer to char(s)

type TVersion=packed array[0..3]of Word;

//Compatibility Info
type  TCompatibility=type integer;
const coUnknown            = 0;
      coForbidden          = 1;
      coIncompatible       = 2;
      coPartiallyCompatible= 3;
      coCompatible         = 4;
      coRequired           = 5;

//Banrisk levels
type TBanRisk=type integer;
const brUnknown            = 0;
      brNone               = 1;
      brLow                = 2;
      brMedium             = 3;
      brHigh               = 4;

type TLogImportance=type integer;// RFC 3164
const
     liEmergency           = 0; //system is unusable
     liAlert               = 1; //action must be taken immediately
     liCritical            = 2; //critical conditions
     liError               = 3; //error conditions
     liWarning             = 4; //warning conditions
     liNotice              = 5; //normal but significant condition
     liInformational       = 6; //informational messages
     liDebug               = 7; //debug-level messages

type TExecutionContext=type integer;
const
     ecUnknown             = 0;
     ecLauncher            = 1;
     ecInjected            = 2;

type TLogFunction=function(Importance:TLogImportance;Message:PChar;Plugin:PChar;):BOOL;stdcall;

type TLoadData=packed record
  StructSize:integer;
  ApiVersion:integer;
  LauncherExecutable:PChar;
  LauncherPath:PChar;
  PluginExecutable:PChar;
  PluginPath:PChar;
  DataPath:PChar;
  ExecutionContext:TExecutionContext;
  Log:TLogFunction;
 end;

type TRunData=packed record
  StructSize:integer;
  GameExeVersion:TVersion;
  GameStormVersion:TVersion;
  ProcessID:Cardinal;
  ProcessHandle:THandle;
  ThreadID:Cardinal;
  ThreadHandle:THandle;
  GameExecutable:PChar;
  GamePath:PChar;
  IsLateActivation:BOOL;
 end;

type TPluginInfo=packed record
  StructSize:integer;
  HasConfig:BOOL;
  LauncherInject:integer;
  Name:PChar;
  Description:PChar;
  Author:PChar;
  Version:TVersion;
  UpdateUrl:PChar;
  UpdateSig:PChar;
  UnloadWhenIdle:BOOL;
  UnloadDuringGame:BOOL;
  BanRisk:TBanRisk;
  LauncherInject:TLauncherInject;
  Injected:BOOL;
  AllowLateActivation:BOOL;
  PatchesCode:BOOL;
  GivesAdvantage:BOOL;
 end;

type TConfigData=packed record
  StructSize:integer;
  LauncherWindow:HWND;
 end;

type TVersionData=packed record
  StructSize:integer;
  GameExeVersion:TVersion;
  GameStormVersion:TVersion;
  GameExecutable:PChar;
  GamePath:PChar;
 end;

function BWL5_Load(const LoadData:TLoadData):BOOL;stdcall;
procedure BWL5_Unload;stdcall;
function BWL5_GetInfo(var PluginInfo:TPluginInfo):BOOL;stdcall;
procedure BWL5_OpenConfig(const ConfigData:TConfigData);stdcall;
function BWL5_RunSuspended(const RunData:TRunData):BOOL;stdcall;
function BWL5_RunWindowCreated(const RunData:TRunData):BOOL;stdcall;
function BWL5_Compatible(const VersionData:TVersionData):TCompatibility;stdcall;