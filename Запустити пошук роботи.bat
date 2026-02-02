@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Поточна директорія: %CD%
echo.
echo Запуск бота...
uv run python bot.py
pause
