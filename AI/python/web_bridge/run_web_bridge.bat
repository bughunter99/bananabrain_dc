@echo off
setlocal

set PORT=8013
set URL=http://127.0.0.1:%PORT%/

rem ── 서버를 별도 콘솔 창에서 시작 ─────────────────────────────────────────
start "ai_dc web bridge" python manage.py runserver 127.0.0.1:%PORT% --noreload

rem ── 서버 초기화 대기 (3초) ────────────────────────────────────────────────
timeout /t 3 /nobreak > nul

rem ── Brave 브라우저로 접속 ────────────────────────────────────────────────
set BRAVE1=C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe
set BRAVE2=C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe

if exist "%BRAVE1%" (
    start "" "%BRAVE1%" %URL%
) else if exist "%BRAVE2%" (
    start "" "%BRAVE2%" %URL%
) else (
    echo Brave 브라우저를 찾을 수 없어 기본 브라우저로 열겠습니다.
    start "" %URL%
)

endlocal
