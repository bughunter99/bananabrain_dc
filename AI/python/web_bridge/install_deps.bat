@echo off
echo [install_deps] Django 설치 중...
python -m pip install -r "%~dp0requirements.txt"
echo.
echo [install_deps] 완료. run_web_bridge.bat 으로 실행하세요.
pause
