@echo off
net session >nul 2>&1
if %errorlevel% neq 0 (
	powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
	exit /b
)

cd /d D:\data3\bwapid_ai_dc\launcher\Source\Launcher\Launcher
start D:\WPy32-3680\python-3.6.8\python.exe chaoslauncher_cli.py --ini "D:\data3\bwapid_ai_dc\launcher\Source\Launcher\Launcher\Chaoslauncher.ini" --sc2-quick-probe

timeout 3

@echo off
net session >nul 2>&1
if %errorlevel% neq 0 (
	powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
	exit /b
)

cd /d D:\data3\bwapid_ai_dc\launcher\Source\Launcher\Launcher
start D:\WPy32-3680\python-3.6.8\python.exe chaoslauncher_cli.py --ini "D:\data3\bwapid_ai_dc\launcher\Source\Launcher\Launcher\Chaoslauncher2.ini" --sc2-quick-probe



cd /d D:\data3\bwapid_ai_dc\AI\python\web_bridge

set "DJANGO_HOST=127.0.0.1"
set "DJANGO_PORT=8001"

python manage.py migrate --noinput

if errorlevel 1 (
  echo.
  echo [ai_dc2] Migration step failed.
  pause
  exit /b 1
)

echo [ai_dc2] Starting Django web bridge on http://%DJANGO_HOST%:%DJANGO_PORT%
start python manage.py runserver --noreload %DJANGO_HOST%:%DJANGO_PORT%

if errorlevel 1 (
  echo.
  echo [ai_dc2] Server stopped with an error. Check Python/Django installation.
  pause
)

start "" "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" "%DJANGO_HOST%:%DJANGO_PORT%"

endlocal


