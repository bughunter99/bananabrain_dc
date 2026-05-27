unit JoinAlert;

interface

implementation
uses main,offsets,sound,config,scinfo,util,sysutils;
var PlayerCount:byte;

procedure TestJoinAlert();
var temp:byte;
    i:Cardinal;
    NewPlayerCount:byte;
    NewOpenCount:byte;
begin
 if not settings.JoinAlert then exit;
 if not IsLobby
   then begin
     PlayerCount:=0;
     exit;
   end;
 NewPlayerCount:=0;
 NewOpenCount:=0;
 for i:=0 to 7 do
  begin
   temp:=Trainer.Byte[Addresses.LobbyPlayerinfo+i*36];
   if temp=2 then inc(newplayercount);
   if temp=6 then inc(newopencount);
  end;
 if (NewPlayerCount>PlayerCount)//More Players
     and (NewPlayerCount>1)and(PlayerCount>0)//Not directly after joining yourself
     and not(ScActive and Settings.JoinAlertOnlyOutside)
     then begin
       if (newopencount=0)
         then PlaySound('JoinAlertFull',1,true)
         else PlaySound('JoinAlert',1,true);
     end;
 PlayerCount:=NewPlayerCount;
end;

initialization
 AddTimerHandler(TestJoinAlert,[pmLauncher]);
finalization
end.
