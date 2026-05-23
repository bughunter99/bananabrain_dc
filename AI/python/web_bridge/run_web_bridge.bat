@echo off
setlocal

set PORT=8013
python manage.py runserver 127.0.0.1:%PORT% --noreload

:eof
endlocal
