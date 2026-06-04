@echo off

cd /d D:\data3\bwapid_ai_dc\AI\python\web_bridge

set "DJANGO_HOST=127.0.0.1"
set "DJANGO_PORT=8001"

C:\Users\dc99.lee\Envs\v1\Scripts\python manage.py migrate --noinput

if errorlevel 1 (
  echo.
  echo [ai_dc2] Migration step failed.
  pause
  exit /b 1
)

echo [ai_dc2] Starting Django web bridge on http://%DJANGO_HOST%:%DJANGO_PORT%
start C:\Users\dc99.lee\Envs\v1\Scripts\python manage.py runserver --noreload %DJANGO_HOST%:%DJANGO_PORT%

if errorlevel 1 (
  echo.
  echo [ai_dc2] Server stopped with an error. Check Python/Django installation.
  pause
)

start "" "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" "%DJANGO_HOST%:%DJANGO_PORT%"

endlocal


