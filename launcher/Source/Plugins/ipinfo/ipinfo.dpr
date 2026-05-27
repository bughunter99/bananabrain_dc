library ipinfo;

uses
  SysUtils,
  windows,
  winsock,
  Classes,
  asmhelper,
  util,
  logger,
  streaming,
  schelper,
  scinfo,
  offsets;

{$R *.res}

function IntToIP(ip:cardinal):String;
begin
  result:=inttostr(ip shr  0 and $FF)+'.'+
          inttostr(ip shr  8 and $FF)+'.'+
          inttostr(ip shr 16 and $FF)+'.'+
          inttostr(ip shr 24 and $FF);
end;

type TPacketHeader=packed record
   Null:Cardinal;
   Checksum:Word;
   Length:Word;
   Sent:word;
   Recved:word;
   CommandClass:byte;
   Command:byte;
   SenderID:byte;
   Resend:byte;
 end;

function IsValidPacket(sock: TSocket; var Buf; len, flags: Integer;
  var from: TSockAddr; var fromlen: Integer;size:integer):boolean;
var header:^TPacketHeader;
begin
  result:=false;
  header:=@buf;
  if header=nil then exit;
  if size<sizeof(TPacketHeader) then exit;
  if size<>Header.Length+4 then exit;
  if Header.Null<>0 then exit;
  result:=true;
end;

procedure LogPacket(sock: TSocket; var Buf; len, flags: Integer;
  var from: TSockAddr; var fromlen: Integer;size:integer);
var s:string;
    header:^TPacketHeader;
begin
  header:=@buf;
  s:=StrToHex(MemToStr(Buf,size));
  insert(' Data:',s,sizeof(TPacketHeader)*2+1);
  insert('Header:',s,1);
  s:='Class:'+inttostr(Header.CommandClass)+' '+
      'Command:'+inttostr(Header.Command)+' '+
      'SenderID:'+inttostr(Header.SenderID)+' '+
      'Length:'+inttostr(Header.Length)+' '+
      s;
  s:='From:'+inttoip(Cardinal(from.sin_addr.S_addr))+' '+s;
  Log(s);
end;

procedure AnalyzeNamepacket(sock: TSocket; var Buf; len, flags: Integer;
  var from: TSockAddr; var fromlen: Integer;size:integer);
var header:^TPacketHeader;
    s:string;
begin
  header:=@buf;
  if header.Command<>$07 then exit;
  s:=MemToStr(buf,size);
  delete(s,1,sizeof(TPacketHeader));
  Str_FitZeroTerminated(s);
  Log('Nick: '+s+' IP: '+IntToIP(Cardinal(from.sin_addr.S_addr)));
end;


function myrecvfrom(sock: TSocket; var Buf; len, flags: Integer;
  var from: TSockAddr; var fromlen: Integer): Integer; stdcall;
begin
  result:=recvfrom(sock,Buf,len,flags,from,fromlen);
  try
    if IsValidPacket(sock,Buf,len,flags,from,fromlen,result)
      then begin
        LogPacket(sock,Buf,len,flags,from,fromlen,result);
        AnalyzeNamepacket(sock,Buf,len,flags,from,fromlen,result);
      end
      else Log('From:'+inttoip(Cardinal(from.sin_addr.S_addr))+' '+StrToHex(MemToStr(Buf,result)));
  except
    on e:exception do
      LogException(e);
  end;
end;

type tmythread=class(TThread)
  protected
    procedure Execute; override;
end;

var PatchAddr:cardinal;
    ProcAddr:pointer;
{ tmythread }

procedure tmythread.Execute;
begin
  inherited;
  while true do
    begin
      sleep(1000);
      try
        if getasynckeystate(vk_f11)<>0 then LocalTextOut('Hi');
      except
      end;
      if GetModuleHandle('battle.snp')<>0 then
        try
           WriteString(PatchAddr,MemToStr(ProcAddr,sizeof(ProcAddr)));
        except
        end;
    end;
end;

begin
  OpenScInfo(0);
  Addresses:=Addresses1153;
  PatchAddr:=$1903A37C;
  ProcAddr:=@myrecvfrom;
  Tmythread.Create(false);
end.
