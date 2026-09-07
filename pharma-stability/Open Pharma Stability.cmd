@echo off
cd /d "%~dp0"
python -X utf8 launcher.py
if errorlevel 1 pause
