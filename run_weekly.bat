@echo off
REM Entry point for Windows Task Scheduler. Runs from this script's own folder
REM regardless of the working directory Task Scheduler starts it in.
cd /d "%~dp0"
call venv\Scripts\activate.bat
python main.py
