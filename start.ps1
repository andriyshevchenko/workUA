# Встановлення UTF-8 кодування для емоджі
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'

# Перехід в директорію скрипта
Set-Location $PSScriptRoot

Write-Host "Поточна директорія: $PWD" -ForegroundColor Cyan
Write-Host ""
Write-Host "Запуск бота..." -ForegroundColor Green

uv run python bot.py

Write-Host ""
Write-Host "Завершено." -ForegroundColor Yellow
