@echo off
chcp 65001 >nul
title StoryCanvas
cd /d "%~dp0"
python launcher.py
pause