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

:: yt-dlp 설치 확인
python -m yt_dlp --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [yt-dlp] 설치 중...
    python -m pip install yt-dlp
)

:: YouTube URL 워처 백그라운드 실행
start "YouTube URL Watcher" /min python yt_watcher.py

:: 서버 실행
python server.py
pause
