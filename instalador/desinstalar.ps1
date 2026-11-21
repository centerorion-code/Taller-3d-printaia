#Requires -Version 5.1
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
<#
.SYNOPSIS
  Desinstalador de taller-3d para Windows.

.DESCRIPTION
  Deshace solo lo que anotó instalar.ps1 en %LOCALAPPDATA%\taller-3d\instalado.txt, en orden inverso:
  la entrada de orca-mcp en la app de Claude, orca-mcp, la copia de uv que bajó y la unión de la carpeta
  de datos de Orca (los datos vuelven a AppData). Lo que se borra va a la Papelera.
  OrcaSlicer, tu carpeta de trabajo (piezas, respaldos y configuración) y tus perfiles de Orca NO se
  tocan, salvo que lo pidas con -Orca o -Todo y lo confirmes.

.PARAMETER Prueba
  Muestra lo que quitaría, sin cambiar nada.

.PARAMETER Orca
  También abre el desinstalador de OrcaSlicer, si lo instaló instalar.ps1.

.PARAMETER Todo
  También manda la carpeta de trabajo a la Papelera (pide confirmación aparte).
#>
[CmdletBinding()]
param(
    [switch]$Prueba,
    [switch]$Orca,
    [switch]$Todo
)

Set-StrictMode -Version 1.0
$ErrorActionPreference = 'Stop'

$Estado = Join-Path $env:LOCALAPPDATA 'taller-3d'
$Manifiesto = Join-Path $Estado 'instalado.txt'
$ClavesDesinstalar = @(
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*'
)

Add-Type -AssemblyName Microsoft.VisualBasic
function APapelera([string]$Ruta) {
    if (Test-Path -LiteralPath $Ruta -PathType Container) {
        [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory($Ruta, 'OnlyErrorDialogs', 'SendToRecycleBin')
    } elseif (Test-Path -LiteralPath $Ruta) {
        [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($Ruta, 'OnlyErrorDialogs', 'SendToRecycleBin')
    }
}

function EsEnlace([string]$Ruta) {
    $i = Get-Item -LiteralPath $Ruta -Force -ErrorAction SilentlyContinue
    return [bool]($i -and ($i.Attributes -band [System.IO.FileAttributes]::ReparsePoint))
}

function Abiertos([string[]]$Procesos, [string]$Nombre) {
    $lista = @(Get-Process -Name $Procesos -ErrorAction SilentlyContinue)
    if ($Nombre -eq 'la app de Claude') {
        # Solo la app de escritorio (Tienda o clásica): Claude Code también se llama claude.exe.
        $lista = @($lista | Where-Object {
            $ruta = [string]$_.Path
            (-not $ruta) -or $ruta -like '*\WindowsApps\*' -or $ruta -like '*\AnthropicClaude\*'
        })
    }
    return ($lista.Count -gt 0)
}

function EsperarCerrado([string[]]$Procesos, [string]$Nombre) {
    while (Abiertos $Procesos $Nombre) {
        $r = [string](Read-Host "   Cerrá $Nombre del todo y apretá Enter (o escribí SALTEAR)")
        if ($r.Trim() -eq 'SALTEAR') { return $false }
    }
    return $true
}

function DentroDe([string]$Ruta, [string]$Base) {
    # ¿$Ruta está adentro de $Base (y no es $Base)? Sin tocar el disco.
    try {
        $sep = [System.IO.Path]::DirectorySeparatorChar
        $r = [System.IO.Path]::GetFullPath($Ruta).TrimEnd($sep).ToLowerInvariant()
        $b = [System.IO.Path]::GetFullPath($Base).TrimEnd($sep).ToLowerInvariant()
        return $r.StartsWith($b + $sep)
    } catch { return $false }
}

function EntradasDesinstalar {
    # Clave por clave: Get-ItemProperty sobre "Uninstall\*" corta toda la lista ante un valor mal guardado.
    foreach ($raiz in $ClavesDesinstalar) {
        foreach ($k in @(Get-ChildItem -Path ($raiz -replace '\\\*$', '') -ErrorAction SilentlyContinue)) {
            try {
                [pscustomobject]@{
                    DisplayName     = [string]$k.GetValue('DisplayName')
                    InstallLocation = [string]$k.GetValue('InstallLocation')
                    UninstallString = [string]$k.GetValue('UninstallString')
                }
            } catch { }
        }
    }
}

if (-not (Test-Path -LiteralPath $Manifiesto)) {
    Write-Host "No encontré $Manifiesto`: no hay nada instalado por instalar.ps1."
    exit 0
}
$lineas = @(Get-Content -LiteralPath $Manifiesto -Encoding UTF8 | Where-Object { $_ -match "`t" } | ForEach-Object {
    $partes = $_ -split "`t", 2
    [pscustomobject]@{ Tipo = $partes[0].Trim(); Valor = $partes[1].Trim() }
})
[array]::Reverse($lineas)

Write-Host '== Esto es lo que instaló taller-3d:'
foreach ($l in $lineas) {
    switch ($l.Tipo) {
        'carpeta' { if ($Todo) { Write-Host "   carpeta de trabajo (con -Todo): $($l.Valor)" } else { Write-Host "   (se conserva) carpeta de trabajo: $($l.Valor)" } }
        'orca-instalado' { if ($Orca) { Write-Host "   OrcaSlicer (con -Orca): $($l.Valor)" } else { Write-Host "   (se conserva) OrcaSlicer: $($l.Valor)" } }
        'union' { Write-Host "   carpeta de datos de Orca movida (vuelve a AppData): $($l.Valor -replace '\|', ' -> ')" }
        'uv' { Write-Host "   orca-mcp (instalado con uv)" }
        'mcp-app' { Write-Host "   entrada de orca-mcp en la app de Claude: $($l.Valor)" }
        default { Write-Host "   $($l.Tipo): $($l.Valor)" }
    }
}
if ($Prueba) { Write-Host 'Modo prueba: no cambié nada.'; exit 0 }
$r = [string](Read-Host '¿Lo quito? Lo que se borra va a la Papelera. Escribí QUITAR para confirmar')
if ($r.Trim() -cne 'QUITAR') { Write-Host 'No cambié nada.'; exit 0 }

$pendientes = $false
foreach ($l in $lineas) {
    try {
        switch ($l.Tipo) {
            'mcp-app' {
                if (-not (Test-Path -LiteralPath $l.Valor)) { break }
                if (-not (EsperarCerrado @('claude') 'la app de Claude')) { Write-Host "   Quedó la entrada en $($l.Valor)"; $pendientes = $true; break }
                $respaldo = '{0}.respaldo-{1}' -f $l.Valor, (Get-Date -Format 'yyyyMMdd-HHmmss')
                Copy-Item -LiteralPath $l.Valor -Destination $respaldo
                $datos = Get-Content -LiteralPath $l.Valor -Raw -Encoding UTF8 | ConvertFrom-Json
                $servidores = $null
                if ($datos -is [psobject] -and $datos.PSObject.Properties['mcpServers']) { $servidores = $datos.mcpServers }
                if ($servidores -is [psobject] -and $servidores.PSObject.Properties['orca-mcp']) {
                    $servidores.PSObject.Properties.Remove('orca-mcp')
                    [System.IO.File]::WriteAllText($l.Valor, (ConvertTo-Json -InputObject $datos -Depth 64),
                        (New-Object System.Text.UTF8Encoding($false)))
                }
                Write-Host "Quitado orca-mcp de la app de Claude (respaldo: $respaldo)."
            }
            'uv' {
                $partes = $l.Valor -split '\|', 2
                $uvExe = $partes[1]
                if (-not $uvExe -or -not (Test-Path -LiteralPath $uvExe)) {
                    $c = Get-Command uv -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
                    $uvExe = $null
                    if ($c) { $uvExe = $c.Path }
                }
                if ($uvExe) {
                    & $uvExe tool uninstall $partes[0]
                    if ($LASTEXITCODE -eq 0) { Write-Host "Quitado: $($partes[0])" }
                    else { Write-Host "   uv no pudo quitar $($partes[0]) (código $LASTEXITCODE)."; $pendientes = $true }
                } else { Write-Host "   No encontré uv para quitar $($partes[0])."; $pendientes = $true }
            }
            'union' {
                $partes = $l.Valor -split '\|', 2
                $real = $partes[0]
                $nuevo = $partes[1]
                # Solo la unión que hace el instalador: %APPDATA%\OrcaSlicer -> una carpeta dentro de tu perfil.
                $esperada = Join-Path $env:APPDATA 'OrcaSlicer'
                if (-not $nuevo -or $real.TrimEnd('\') -ne $esperada.TrimEnd('\') -or -not (DentroDe $nuevo $env:USERPROFILE)) {
                    Write-Host "   No toco '$($l.Valor)': no es la unión que hace el instalador."; $pendientes = $true; break
                }
                if (-not (EsEnlace $real)) { break }
                if (-not (Test-Path -LiteralPath $nuevo -PathType Container)) {
                    Write-Host "   No encuentro $($nuevo): dejo la unión como está."; $pendientes = $true; break
                }
                if (-not (EsperarCerrado @('orca-slicer', 'OrcaSlicer') 'OrcaSlicer')) { $pendientes = $true; break }
                # 1) copia completa al lado de la unión; 2) se saca la unión; 3) la copia toma su lugar.
                $copia = "$real.taller-3d-vuelta"
                if (Test-Path -LiteralPath $copia) { throw "Ya existe $copia (de un intento anterior): revisala y borrala antes." }
                Copy-Item -LiteralPath $nuevo -Destination $copia -Recurse -Force -ErrorAction Stop
                $enOrigen = @(Get-ChildItem -LiteralPath $nuevo -Recurse -Force -File -ErrorAction Stop).Count
                $enCopia = @(Get-ChildItem -LiteralPath $copia -Recurse -Force -File -ErrorAction Stop).Count
                if ($enOrigen -ne $enCopia) {
                    Remove-Item -LiteralPath $copia -Recurse -Force -ErrorAction SilentlyContinue
                    throw "La copia salió incompleta ($enCopia de $enOrigen archivos): dejo todo como estaba."
                }
                [System.IO.Directory]::Delete($real)
                try {
                    Rename-Item -LiteralPath $copia -NewName (Split-Path -Leaf $real) -ErrorAction Stop
                } catch {
                    New-Item -ItemType Junction -Path $real -Target $nuevo | Out-Null
                    throw "No pude poner la copia en su lugar ($($_.Exception.Message)): volví a dejar la unión."
                }
                $guardada = '{0}.ya-devuelto-{1}' -f $nuevo, (Get-Date -Format 'yyyyMMdd-HHmmss')
                Rename-Item -LiteralPath $nuevo -NewName (Split-Path -Leaf $guardada) -ErrorAction SilentlyContinue
                Write-Host "Datos de Orca de vuelta en $real."
                Write-Host "   Dejé una copia en $guardada por las dudas: borrala cuando veas que Orca anda bien."
            }
            'orca-instalado' {
                if (-not $Orca) { break }
                $carpeta = Split-Path -Parent $l.Valor
                $entrada = @(EntradasDesinstalar) | Where-Object {
                    [string]$_.DisplayName -match 'Orca\s*Slicer' -and (
                        ([string]$_.InstallLocation).Trim('"').TrimEnd('\') -eq $carpeta -or
                        ([string]$_.UninstallString) -like "*$carpeta*")
                } | Select-Object -First 1
                if ($entrada -and $entrada.UninstallString) {
                    $r2 = [string](Read-Host "   ¿Abro el desinstalador de OrcaSlicer ($carpeta)? Escribí SI")
                    if ($r2.Trim() -ceq 'SI') {
                        # "C:\...\uninst.exe" /arg  ->  programa y argumentos por separado
                        $cadena = ([string]$entrada.UninstallString).Trim()
                        if ($cadena -match '^"([^"]+)"\s*(.*)$') { $programa = $Matches[1]; $argumentos = $Matches[2] }
                        else { $programa = $cadena; $argumentos = '' }
                        if ($argumentos) { Start-Process -FilePath $programa -ArgumentList $argumentos }
                        else { Start-Process -FilePath $programa }
                        Write-Host '   Seguí los pasos del desinstalador de Orca en su ventana.'
                    }
                } else {
                    Write-Host '   No encontré el desinstalador de Orca: quitalo desde Configuración > Aplicaciones.'
                }
            }
            'carpeta' {
                if (-not $Todo -or -not (Test-Path -LiteralPath $l.Valor)) { break }
                if ((DentroDe $env:USERPROFILE $l.Valor) -or $l.Valor.TrimEnd('\') -eq $env:USERPROFILE.TrimEnd('\') -or
                    $l.Valor.TrimEnd('\').Length -le 3) {
                    Write-Host "   No mando '$($l.Valor)' a la Papelera: contiene tu carpeta personal."; break
                }
                $r2 = [string](Read-Host "   ¿Mando también la carpeta de trabajo '$($l.Valor)' a la Papelera? Escribí SI")
                if ($r2.Trim() -ceq 'SI') { APapelera $l.Valor; Write-Host "A la Papelera: $($l.Valor)" }
            }
            'archivo' {
                if (-not (DentroDe $l.Valor $Estado)) {
                    Write-Host "   No toco '$($l.Valor)': está fuera de la carpeta del instalador."; $pendientes = $true; break
                }
                if (Test-Path -LiteralPath $l.Valor) { APapelera $l.Valor; Write-Host "A la Papelera: $($l.Valor)" }
            }
            default {
                Write-Host "   No sé deshacer '$($l.Tipo)': lo dejo como está."; $pendientes = $true
            }
        }
    } catch {
        Write-Host "   No pude deshacer '$($l.Tipo)': $($_.Exception.Message)" -ForegroundColor Yellow
        $pendientes = $true
    }
}

if ($pendientes) {
    Write-Host 'Quedaron cosas sin quitar (arriba dice cuáles). La lista sigue en:'
    Write-Host "   $Manifiesto"
} else {
    APapelera $Manifiesto
    Write-Host 'Listo. Tus perfiles de Orca quedaron como estaban.'
}
Write-Host 'El plugin se quita desde la configuración de plugins de la app de Claude.'
