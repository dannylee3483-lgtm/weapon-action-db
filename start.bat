@echo off
chcp 65001 >nul
title Weapon Action DB Server

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [오류] Python이 설치되어 있지 않습니다.
    echo  https://www.python.org 에서 설치 후 다시 실행하세요.
    echo.
    pause
    exit /b 1
)

cd /d "%~dp0"
python server.py
pause
