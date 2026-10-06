@echo off
chcp 65001 > nul
title AutoResearchClaw - Live Log Monitor
cd /d "%~dp0"

".venv\Scripts\python.exe" "scripts\tail_logs.py"
pause
