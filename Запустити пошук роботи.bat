@echo off
cd /d "%~dp0"
powershell.exe -NoExit -ExecutionPolicy Bypass -Command "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Write-Host 'Поточна директорія:' $PWD -ForegroundColor Cyan; Write-Host ''; Write-Host 'Запуск бота...' -ForegroundColor Green; & uv run python bot.py; Write-Host ''; Write-Host 'Завершено.' -ForegroundColor Yellow"
