@echo off
setlocal

set PORT=8013
if not "%1"=="" set PORT=%1

cd /d "%~dp0"

set VENV_PYTHON=%USERPROFILE%\Envs\v1\Scripts\python.exe
if exist "%VENV_PYTHON%" (
    echo [web_bridge] Using venv: %VENV_PYTHON%
    "%VENV_PYTHON%" manage.py runserver 127.0.0.1:%PORT% --noreload
    goto :eof
)

echo [web_bridge] venv not found, trying system python...
python manage.py runserver 127.0.0.1:%PORT% --noreload

:eof
endlocal
