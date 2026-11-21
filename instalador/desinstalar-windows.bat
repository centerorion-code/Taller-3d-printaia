@echo off
rem SPDX-License-Identifier: AGPL-3.0-only
rem Copyright (C) 2026 Leo y colaboradores de taller-3d
rem Desinstalador de taller-3d para Windows: abre desinstalar.ps1 con PowerShell.
rem Para ver lo que quitaria sin cambiar nada: desinstalar-windows.bat -Prueba
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0desinstalar.ps1" %*
echo.
pause
