@echo off
setlocal

cd /d "%~dp0"

set "DJANGO_HOST=127.0.0.1"
set "DJANGO_PORT=8001"

if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
)

echo [ai_dc2] Applying Django migrations
python manage.py migrate --noinput

if errorlevel 1 (
  echo.
  echo [ai_dc2] Migration step failed.
  pause
  exit /b 1
)

echo [ai_dc2] Starting Django web bridge on http://%DJANGO_HOST%:%DJANGO_PORT%
python manage.py runserver --noreload %DJANGO_HOST%:%DJANGO_PORT%

if errorlevel 1 (
  echo.
  echo [ai_dc2] Server stopped with an error. Check Python/Django installation.
  pause
)

endlocal
