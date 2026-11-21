@echo off
rem SPDX-License-Identifier: AGPL-3.0-only
rem Copyright (C) 2026 Leo y colaboradores de taller-3d
rem Instalador de taller-3d para Windows: abre instalar.ps1 con PowerShell.
rem Para ver lo que haria sin cambiar nada: instalar-windows.bat -Prueba
setlocal
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar.ps1" %*
echo.
pause
