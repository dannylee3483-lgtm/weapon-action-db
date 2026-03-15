@echo off
chcp 65001 >nul
title Weapon Action DB — 레퍼런스 수집기

cd /d "%~dp0"

:: Python 확인
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [오류] Python이 설치되어 있지 않습니다.
    pause & exit /b 1
)

:: Claude CLI 확인
claude --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [오류] 'claude' 명령을 찾을 수 없습니다.
    echo  Claude Code CLI가 설치되어 있는지 확인하세요.
    pause & exit /b 1
)

echo.
echo  ============================================
echo    Weapon Action DB - 레퍼런스 수집기
echo    Claude Code CLI 사용 (추가 과금 없음)
echo  ============================================
echo.
echo  옵션:
echo    -c [카테고리]   무기 카테고리 지정
echo    -g [게임명]     게임 지정
echo    -m [메카닉]     메카닉 키워드 지정
echo    -q [검색어]     자유 검색어
echo    -n [숫자]       수집할 수 (기본 3, 최대 8)
echo    --dry-run       저장 없이 미리보기
echo.
echo  예시:
echo    -c 카타나 -n 5
echo    -g "Sekiro" -n 3
echo    -m parry -n 6
echo    -c 대검 -g "Elden Ring" -n 3
echo    -q "공중 콤보 메카닉" -n 4
echo.

set /p ARGS=  인수 입력 (Enter = 도움말):
if "%ARGS%"=="" (
    python collect.py --help
) else (
    python collect.py %ARGS%
)

echo.
pause
