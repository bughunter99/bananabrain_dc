@echo off
net session >nul 2>&1
if %errorlevel% neq 0 (
	powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
	exit /b
)

cd /d D:\data3\bwapid_ai_dc\launcher\Source\Launcher\Launcher
D:\WPy32-3680\python-3.6.8\python.exe chaoslauncher_cli.py --ini "D:\data3\bwapid_ai_dc\launcher\Source\Launcher\Launcher\Chaoslauncher.ini" --sc2-quick-probe
