#Requires -Version 5.1
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
<#
.SYNOPSIS
  Instalador de taller-3d para Windows 10 y 11 (x64 o ARM64).

.DESCRIPTION
  Primero revisa que la PC alcance (sistema, procesador, memoria, placa de video, disco, internet y
  permisos): si no alcanza, no cambia nada. Después revisa qué tenés instalado, saltea lo que ya está
  y hace solo lo que falta:
    1. Te muestra el aviso de uso y te pide que escribas ACEPTO.
    2. Si la app de Claude es la versión empaquetada de Windows (MSIX), te ofrece mover la carpeta de
       datos de Orca fuera de AppData y dejar un acceso en el lugar de siempre. Sin esto, Orca no ve
       los perfiles que escribe Claude.
    3. OrcaSlicer 2.5.1: si no lo tenés, baja el instalador oficial de GitHub, verifica su huella
       SHA-256 y su firma digital (ORCASLICER PTE. LTD.) y lo abre para que lo instales vos.
    4. orca-mcp 0.1.0 (la conexión entre Claude y Orca) con uv. Si no tenés uv, baja la versión
       oficial y verifica su huella.
    5. Crea la carpeta de trabajo con su configuración inicial.
    6. Agrega orca-mcp a la app de Claude, con copia de respaldo, si querés.

  No borra nada tuyo: lo que reemplaza va a la Papelera. Anota lo que instala en
  %LOCALAPPDATA%\taller-3d\instalado.txt para que desinstalar.ps1 pueda quitarlo.

.PARAMETER Prueba
  Muestra lo que haría, sin cambiar nada.

.PARAMETER Orca
  Ruta a un orca-slicer.exe que ya tengas (por ejemplo, uno portable). Saltea la búsqueda.

.PARAMETER CarpetaTrabajo
  Carpeta del taller. Por defecto: Documentos\Taller 3D.

.PARAMETER SinApp
  No tocar la configuración de la app de Claude.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File .\instalar.ps1 -Prueba
#>
[CmdletBinding()]
param(
    [switch]$Prueba,
    [string]$Orca,
    [string]$CarpetaTrabajo,
    [switch]$SinApp
)

Set-StrictMode -Version 1.0
$ErrorActionPreference = 'Stop'

$VersionPlugin = '0.1.6'
$OrcaVersion = '2.5.1'
$OrcaBase = "https://github.com/OrcaSlicer/OrcaSlicer/releases/download/v$OrcaVersion"
$OrcaArchivos = @{
    x64   = @{ Archivo = 'OrcaSlicer_Windows_Installer_V2.5.1_x64.exe'; Mb = 152
               Sha256 = 'BFBDCD51FDFE8AF1A9922BC0AEC979E02C9207EF1934413AD320E7E7AB0818AF' }
    arm64 = @{ Archivo = 'OrcaSlicer_Windows_Installer_V2.5.1_arm64.exe'; Mb = 138
               Sha256 = 'DBC0370EF9D6873D093BCBA31B45F40BBB5647AA276666A826AAEB7521791AF8' }
}
# Huella de OrcaSlicer.dll de la 2.5.1 oficial: sirve para reconocer la versión que ya está instalada.
$HuellasDll251 = @(
    'FD1C5A81F8B67C042CB4AA643F4EA6F4D5D89538DE0D902EE9531394158921ED',   # x64
    'D82F8566BA6EF93423840A69382D0B8005A5734C43ECF0F44BF90A5A8F320FCC'    # ARM64
)
$OrcaFirmante = 'ORCASLICER PTE. LTD.'
$UvVersion = '0.13.9'
$UvBase = "https://github.com/astral-sh/uv/releases/download/$UvVersion"
$UvArchivos = @{
    x64   = @{ Archivo = 'uv-x86_64-pc-windows-msvc.zip'
               Sha256 = 'EDD61F7F5728A56CC62455386661860BDFC7BAB65872F39B0C25BDCC1D8E1BEB' }
    arm64 = @{ Archivo = 'uv-aarch64-pc-windows-msvc.zip'
               Sha256 = '72EED595983A4D7D22D79F21065B0F4479CC7E5C7A89104BB410C8F47559A878' }
}
$OrcaMcpVersion = '0.1.0'

$Estado = Join-Path $env:LOCALAPPDATA 'taller-3d'
$Manifiesto = Join-Path $Estado 'instalado.txt'
$Registro = Join-Path $Estado ('instalacion-{0}.log' -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
$ClavesDesinstalar = @(
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*'
)

# --- Ayudas ---------------------------------------------------------------------------------------
function Paso([string]$Texto) { Write-Host ''; Write-Host "== $Texto" -ForegroundColor Cyan }
function Info([string]$Texto) { Write-Host "   $Texto" }
function Aviso([string]$Texto) { Write-Host "   $Texto" -ForegroundColor Yellow }
function EnPrueba([string]$Texto) { Write-Host "   [prueba] $Texto" -ForegroundColor DarkYellow }

function Fila([bool]$Ok, [string]$Que, [string]$Detalle) {
    $marca = '[falta]'
    $color = 'Yellow'
    if ($Ok) { $marca = '[ok]   '; $color = 'Green' }
    $texto = "   $marca $Que"
    if ($Detalle) { $texto = "$texto`: $Detalle" }
    Write-Host $texto -ForegroundColor $color
}

function Preguntar([string]$Texto) {
    if ($Prueba) { EnPrueba "$Texto (s/N): se asume NO"; return $false }
    $r = [string](Read-Host "   $Texto (s/N)")
    return ($r.Trim().ToLowerInvariant() -in @('s', 'si', 'sí', 'y', 'yes'))
}

function EscribirTexto([string]$Ruta, [string]$Texto) {
    $carpeta = Split-Path -Parent $Ruta
    if ($carpeta -and -not (Test-Path -LiteralPath $carpeta)) {
        New-Item -ItemType Directory -Path $carpeta -Force | Out-Null
    }
    # UTF-8 sin BOM: la app de Claude no lee JSON con BOM.
    [System.IO.File]::WriteAllText($Ruta, $Texto, (New-Object System.Text.UTF8Encoding($false)))
}

function Anotar([string]$Tipo, [string]$Valor) {
    if ($Prueba) { return }
    if (-not (Test-Path -LiteralPath $Estado)) { New-Item -ItemType Directory -Path $Estado -Force | Out-Null }
    [System.IO.File]::AppendAllText($Manifiesto, "$Tipo`t$Valor`r`n", (New-Object System.Text.UTF8Encoding($false)))
}

function LeerJson([string]$Ruta) {
    try { return (Get-Content -LiteralPath $Ruta -Raw -Encoding UTF8 | ConvertFrom-Json) } catch { return $null }
}

function EntradasDesinstalar {
    # Una por programa instalado. Se lee clave por clave: Get-ItemProperty sobre "Uninstall\*" puede
    # cortar toda la lista ("Specified cast is not valid") si un programa dejó un valor mal guardado.
    foreach ($raiz in $ClavesDesinstalar) {
        foreach ($k in @(Get-ChildItem -Path ($raiz -replace '\\\*$', '') -ErrorAction SilentlyContinue)) {
            try {
                [pscustomobject]@{
                    DisplayName     = [string]$k.GetValue('DisplayName')
                    DisplayVersion  = [string]$k.GetValue('DisplayVersion')
                    DisplayIcon     = [string]$k.GetValue('DisplayIcon')
                    InstallLocation = [string]$k.GetValue('InstallLocation')
                    UninstallString = [string]$k.GetValue('UninstallString')
                }
            } catch { }
        }
    }
}

function CarpetaDe([string]$Ruta) {
    try { return (Split-Path -Parent $Ruta) } catch { return $null }
}

function AppDeClaudeAbierta {
    # Solo la app de escritorio (Tienda o clásica), no Claude Code, que también se llama claude.exe.
    $p = @(Get-Process -Name 'claude' -ErrorAction SilentlyContinue | Where-Object {
        $ruta = [string]$_.Path
        (-not $ruta) -or $ruta -like '*\WindowsApps\*' -or $ruta -like '*\AnthropicClaude\*'
    })
    return ($p.Count -gt 0)
}

function TienePropiedad($Objeto, [string]$Nombre) {
    return ($null -ne $Objeto -and $Objeto -is [psobject] -and $null -ne $Objeto.PSObject.Properties[$Nombre])
}

function Bajar([string]$Url, [string]$Destino) {
    $curl = Join-Path $env:SystemRoot 'System32\curl.exe'
    if (Test-Path -LiteralPath $curl) {
        & $curl -fL --retry 3 --progress-bar -o $Destino $Url
        if ($LASTEXITCODE -ne 0) { throw "No pude bajar $Url (curl terminó con el código $LASTEXITCODE)." }
    } else {
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
        $antes = $ProgressPreference
        $ProgressPreference = 'SilentlyContinue'
        try { Invoke-WebRequest -Uri $Url -OutFile $Destino -UseBasicParsing } finally { $ProgressPreference = $antes }
    }
}

function HuellaOk([string]$Ruta, [string]$Esperada) {
    return ((Get-FileHash -LiteralPath $Ruta -Algorithm SHA256).Hash -eq $Esperada.ToUpperInvariant())
}

function Arquitectura {
    $a = $null
    try { $a = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString() } catch { $a = $null }
    if (-not $a) { $a = $env:PROCESSOR_ARCHITECTURE; if ($env:PROCESSOR_ARCHITEW6432) { $a = $env:PROCESSOR_ARCHITEW6432 } }
    if ($a -match '^(X64|AMD64)$') { return 'x64' }
    if ($a -match '^ARM64$') { return 'arm64' }
    return $null
}

function EsEnlace([string]$Ruta) {
    $i = Get-Item -LiteralPath $Ruta -Force -ErrorAction SilentlyContinue
    return [bool]($i -and ($i.Attributes -band [System.IO.FileAttributes]::ReparsePoint))
}

function DestinoDeEnlace([string]$Ruta) {
    $i = Get-Item -LiteralPath $Ruta -Force -ErrorAction SilentlyContinue
    if ($i -and $i.Target) { return [string](@($i.Target)[0]) }
    return $null
}

# --- Qué hay instalado --------------------------------------------------------------------------------
function DatosDeOrca([string]$Exe) {
    # Orca portable: si hay una carpeta data_dir al lado del programa, usa esa.
    $portable = Join-Path (Split-Path -Parent $Exe) 'data_dir'
    if (Test-Path -LiteralPath $portable -PathType Container) { return $portable }
    $real = Join-Path $env:APPDATA 'OrcaSlicer'
    $destino = DestinoDeEnlace $real
    if ($destino) { return $destino }
    return $real
}

function VersionDeOrca([string]$Exe, [string]$DeRegistro) {
    $dll = Join-Path (Split-Path -Parent $Exe) 'OrcaSlicer.dll'
    if (Test-Path -LiteralPath $dll) {
        if ($HuellasDll251 -contains (Get-FileHash -LiteralPath $dll -Algorithm SHA256).Hash) { return $OrcaVersion }
    }
    if ($DeRegistro) { return $DeRegistro }
    return 'desconocida'
}

function NuevoOrca([string]$Exe, [string]$Origen, [string]$DeRegistro) {
    $ruta = (Resolve-Path -LiteralPath $Exe).Path
    return [pscustomobject]@{ Exe = $ruta; Origen = $Origen; Version = (VersionDeOrca $ruta $DeRegistro); Datos = (DatosDeOrca $ruta) }
}

function BuscarOrca {
    $vistos = @{}
    $hallados = New-Object System.Collections.ArrayList
    $candidatos = New-Object System.Collections.ArrayList
    foreach ($e in @(EntradasDesinstalar)) {
        if ([string]$e.DisplayName -notmatch 'Orca\s*Slicer') { continue }
        $carpeta = [string]$e.InstallLocation
        if (-not $carpeta -and $e.DisplayIcon) {
            $carpeta = CarpetaDe (([string]$e.DisplayIcon -replace ',\s*-?\d+$', '').Trim('"'))
        }
        if (-not $carpeta -and $e.UninstallString) {
            $carpeta = CarpetaDe (([string]$e.UninstallString).Trim().Trim('"'))
        }
        if ($carpeta) { [void]$candidatos.Add(@((Join-Path $carpeta.Trim('"') 'orca-slicer.exe'), [string]$e.DisplayVersion)) }
    }
    foreach ($c in @((Join-Path $env:ProgramFiles 'OrcaSlicer'), (Join-Path $env:LOCALAPPDATA 'Programs\OrcaSlicer'),
                     (Join-Path $env:USERPROFILE 'scoop\apps\orcaslicer\current'))) {
        [void]$candidatos.Add(@((Join-Path $c 'orca-slicer.exe'), ''))
    }
    if (${env:ProgramFiles(x86)}) { [void]$candidatos.Add(@((Join-Path ${env:ProgramFiles(x86)} 'OrcaSlicer\orca-slicer.exe'), '')) }
    foreach ($c in $candidatos) {
        $exe = $c[0]
        if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { continue }
        $clave = (Resolve-Path -LiteralPath $exe).Path.ToLowerInvariant()
        if ($vistos.ContainsKey($clave)) { continue }
        $vistos[$clave] = $true
        [void]$hallados.Add((NuevoOrca $exe 'instalado' $c[1]))
    }
    return $hallados
}

function OrcaDeTienda {
    $p = Get-ChildItem -LiteralPath (Join-Path $env:LOCALAPPDATA 'Packages') -Directory -Filter '*OrcaSlicer*' -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $p) { return $null }
    $version = $null
    try {
        $pkg = Get-AppxPackage -Name '*OrcaSlicer*' -ErrorAction Stop | Select-Object -First 1
        if ($pkg) { $version = [string]$pkg.Version }
    } catch { $version = $null }
    return [pscustomobject]@{ Paquete = $p.Name; Version = $version }
}

function AppDeClaude {
    $paquetes = Join-Path $env:LOCALAPPDATA 'Packages'
    $pkg = Get-ChildItem -LiteralPath $paquetes -Directory -Filter 'Claude_pzs8sxrjxfjjc' -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $pkg) { $pkg = Get-ChildItem -LiteralPath $paquetes -Directory -Filter 'Claude_*' -ErrorAction SilentlyContinue | Select-Object -First 1 }
    if ($pkg) {
        # App empaquetada (MSIX): lee su configuración de la carpeta privada del paquete.
        return [pscustomobject]@{ Tipo = 'msix'; Config = (Join-Path $pkg.FullName 'LocalCache\Roaming\Claude\claude_desktop_config.json') }
    }
    $clasica = Join-Path $env:APPDATA 'Claude'
    if ((Test-Path -LiteralPath (Join-Path $env:LOCALAPPDATA 'AnthropicClaude')) -or (Test-Path -LiteralPath $clasica)) {
        return [pscustomobject]@{ Tipo = 'clasica'; Config = (Join-Path $clasica 'claude_desktop_config.json') }
    }
    return $null
}

function BuscarOrcaMcp {
    $c = Get-Command orca-mcp -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($c) { return $c.Path }
    $r = Join-Path $env:USERPROFILE '.local\bin\orca-mcp.exe'
    if (Test-Path -LiteralPath $r) { return $r }
    return $null
}

function BuscarUv {
    $c = Get-Command uv -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($c) { return $c.Path }
    $propio = Join-Path $Estado 'uv\uv.exe'
    if (Test-Path -LiteralPath $propio) { return $propio }
    return $null
}

function TieneWebView2 {
    $id = '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'
    foreach ($k in @("HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\$id",
                     "HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\$id",
                     "HKCU:\Software\Microsoft\EdgeUpdate\Clients\$id")) {
        $v = (Get-ItemProperty -Path $k -Name pv -ErrorAction SilentlyContinue).pv
        if ($v -and $v -ne '0.0.0.0') { return $true }
    }
    return $false
}

function ProbarInternet([string]$Url) {
    $curl = Join-Path $env:SystemRoot 'System32\curl.exe'
    if (Test-Path -LiteralPath $curl) {
        & $curl -s -o NUL --max-time 15 $Url
        return ($LASTEXITCODE -eq 0)
    }
    try { Invoke-WebRequest -Uri $Url -Method Head -UseBasicParsing -TimeoutSec 15 | Out-Null; return $true } catch { return $false }
}

function MedirPC {
    # Lee sistema, procesador, memoria, placas de video y disco libre. Lo que no se pueda leer queda vacío.
    $m = [ordered]@{ Sistema = $null; Build = 0; Procesador = $null; Nucleos = 0; RamGB = 0.0
                     Video = @(); DiscoGB = [ordered]@{}; Rdp = $false }
    try {
        $so = Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction Stop
        $m.Sistema = ([string]$so.Caption).Trim()
        $m.Build = [int]$so.BuildNumber
    } catch { $m.Sistema = $null }
    try {
        $m.RamGB = [math]::Round([double](Get-CimInstance -ClassName Win32_ComputerSystem -ErrorAction Stop).TotalPhysicalMemory / 1GB, 1)
    } catch { $m.RamGB = 0.0 }
    try {
        $cpus = @(Get-CimInstance -ClassName Win32_Processor -ErrorAction Stop)
        $m.Procesador = ([string]$cpus[0].Name).Trim()
        $m.Nucleos = [int](($cpus | Measure-Object -Property NumberOfLogicalProcessors -Sum).Sum)
    } catch { $m.Procesador = $null }
    try {
        $m.Video = @(Get-CimInstance -ClassName Win32_VideoController -ErrorAction Stop | ForEach-Object { ([string]$_.Name).Trim() } |
            Where-Object { $_ })
    } catch { $m.Video = @() }
    foreach ($ruta in @($env:ProgramFiles, $env:USERPROFILE)) {
        $unidad = Split-Path -Qualifier $ruta
        if ($m.DiscoGB.Contains($unidad)) { continue }
        try { $m.DiscoGB[$unidad] = [math]::Round((New-Object System.IO.DriveInfo($unidad)).AvailableFreeSpace / 1GB, 1) } catch { }
    }
    $m.Rdp = ([string]$env:SESSIONNAME -like 'RDP-*')
    return $m
}

function EvaluarRequisitos($M, [bool]$BajarOrca, [bool]$Bajar, [bool]$HayInternet, [bool]$EsAdministrador) {
    # Devuelve una lista de { Estado = ok | aviso | no; Texto }. "no" frena la instalación.
    $r = New-Object System.Collections.ArrayList
    if ($M.Sistema) {
        if ($M.Build -gt 0 -and $M.Build -lt 17763) {
            [void]$r.Add([pscustomobject]@{ Estado = 'aviso'; Texto = "Sistema: $($M.Sistema) (compilación $($M.Build)). Es un Windows 10 viejo: conviene actualizarlo." })
        } else {
            [void]$r.Add([pscustomobject]@{ Estado = 'ok'; Texto = "Sistema: $($M.Sistema) (compilación $($M.Build))" })
        }
    }
    if (-not $M.Procesador) {
        [void]$r.Add([pscustomobject]@{ Estado = 'aviso'; Texto = 'Procesador: no lo pude leer.' })
    } elseif ($M.Nucleos -lt 2) {
        [void]$r.Add([pscustomobject]@{ Estado = 'aviso'; Texto = "Procesador: $($M.Procesador), $($M.Nucleos) núcleo. Va a laminar lento." })
    } elseif ($M.Nucleos -lt 4) {
        [void]$r.Add([pscustomobject]@{ Estado = 'aviso'; Texto = "Procesador: $($M.Procesador), $($M.Nucleos) núcleos. Alcanza; las piezas grandes laminan más lento." })
    } else {
        [void]$r.Add([pscustomobject]@{ Estado = 'ok'; Texto = "Procesador: $($M.Procesador), $($M.Nucleos) núcleos" })
    }
    if ($M.RamGB -le 0) {
        [void]$r.Add([pscustomobject]@{ Estado = 'aviso'; Texto = 'Memoria: no la pude leer. Orca pide 4 GB como mínimo.' })
    } elseif ($M.RamGB -lt 3.5) {
        [void]$r.Add([pscustomobject]@{ Estado = 'no'; Texto = "Memoria: $($M.RamGB) GB. Orca pide 4 GB como mínimo." })
    } elseif ($M.RamGB -lt 7.5) {
        [void]$r.Add([pscustomobject]@{ Estado = 'aviso'; Texto = "Memoria: $($M.RamGB) GB. Alcanza; con piezas grandes conviene 8 GB o más." })
    } else {
        [void]$r.Add([pscustomobject]@{ Estado = 'ok'; Texto = "Memoria: $($M.RamGB) GB" })
    }
    $placas = @($M.Video)
    $reales = @($placas | Where-Object { $_ -notmatch 'Microsoft (Basic Display|Basic Render|Remote Display)|Remote Desktop' })
    $listado = $placas -join ', '
    if ($reales.Count -eq 0) {
        [void]$r.Add([pscustomobject]@{ Estado = 'aviso'; Texto = "Placa de video: $(if ($listado) { $listado } else { 'no la pude leer' }). Falta el driver de video: Orca pide OpenGL 3.3 y su ventana puede no abrir. Claude lamina igual." })
    } elseif (@($reales | Where-Object { $_ -match 'VMware|VirtualBox|Parallels|Hyper-V|QXL|Red Hat|Virtio' }).Count -eq $reales.Count) {
        [void]$r.Add([pscustomobject]@{ Estado = 'aviso'; Texto = "Placa de video: $listado. Es una máquina virtual: la ventana de Orca puede no andar. Claude lamina igual." })
    } elseif (@($reales | Where-Object { $_ -notmatch 'HD Graphics (2000|3000)$|GMA|Mobile Intel\(R\) 4 Series|Intel\(R\) (G41|G43|G45|Q43|Q45|B43)' }).Count -eq 0) {
        [void]$r.Add([pscustomobject]@{ Estado = 'aviso'; Texto = "Placa de video: $listado. Es vieja y probablemente no llega a OpenGL 3.3: la ventana de Orca puede fallar. Claude lamina igual." })
    } else {
        [void]$r.Add([pscustomobject]@{ Estado = 'ok'; Texto = "Placa de video: $listado (Orca pide OpenGL 3.3: con el driver al día, alcanza)" })
    }
    if ($M.Rdp) {
        [void]$r.Add([pscustomobject]@{ Estado = 'aviso'; Texto = 'Estás por Escritorio remoto: la ventana de Orca puede no abrir así. Para laminar desde Claude no importa.' })
    }
    $minimo = 0.3
    if ($BajarOrca) { $minimo = 1.0 }
    foreach ($unidad in @($M.DiscoGB.Keys)) {
        $libre = [double]$M.DiscoGB[$unidad]
        if ($libre -lt $minimo) {
            [void]$r.Add([pscustomobject]@{ Estado = 'no'; Texto = "Disco libre en $unidad`: $libre GB. Hace falta por lo menos $minimo GB." })
        } elseif ($libre -lt 2) {
            [void]$r.Add([pscustomobject]@{ Estado = 'aviso'; Texto = "Disco libre en $unidad`: $libre GB. Alcanza justo; las piezas y respaldos también ocupan." })
        } else {
            [void]$r.Add([pscustomobject]@{ Estado = 'ok'; Texto = "Disco libre en $unidad`: $libre GB" })
        }
    }
    if ($Bajar) {
        if ($HayInternet) {
            [void]$r.Add([pscustomobject]@{ Estado = 'ok'; Texto = 'Conexión a GitHub y PyPI (para bajar Orca, uv y orca-mcp)' })
        } else {
            [void]$r.Add([pscustomobject]@{ Estado = 'no'; Texto = 'Sin conexión a github.com o pypi.org: hace falta para bajar Orca, uv y orca-mcp.' })
        }
    }
    if ($BajarOrca -and -not $EsAdministrador) {
        [void]$r.Add([pscustomobject]@{ Estado = 'aviso'; Texto = 'Tu usuario no es administrador: para instalar Orca, Windows te va a pedir la contraseña de uno. Si no la tenés, usá un Orca portable (-Orca).' })
    }
    return $r
}

function BuscarBlender {
    foreach ($e in @(EntradasDesinstalar)) {
        if ([string]$e.DisplayName -match '^Blender') { return ([string]$e.DisplayName).Trim() }
    }
    if (Get-ChildItem -LiteralPath (Join-Path $env:LOCALAPPDATA 'Packages') -Directory -Filter 'BlenderFoundation.Blender*' -ErrorAction SilentlyContinue) {
        return 'Blender (Microsoft Store)'
    }
    return $null
}

function AgregarAConfigApp([string]$Ruta, $Entrada) {
    $actual = $null
    $respaldo = $null
    if (Test-Path -LiteralPath $Ruta) {
        $texto = [string](Get-Content -LiteralPath $Ruta -Raw -Encoding UTF8)
        if ($texto.Trim()) {
            try { $actual = $texto | ConvertFrom-Json } catch {
                Aviso "La configuración actual no es JSON válido: no la toco. Agregá la entrada de arriba a mano en $Ruta"
                return
            }
        }
        $respaldo = '{0}.respaldo-{1}' -f $Ruta, (Get-Date -Format 'yyyyMMdd-HHmmss')
        Copy-Item -LiteralPath $Ruta -Destination $respaldo
        Info "Respaldo: $respaldo"
    }
    if ($null -eq $actual) { $actual = New-Object psobject }
    if (-not ($actual -is [psobject]) -or $actual -is [array]) {
        Aviso "La configuración actual no tiene el formato esperado: no la toco. Agregá la entrada de arriba a mano en $Ruta"
        return
    }
    if (-not (TienePropiedad $actual 'mcpServers')) {
        $actual | Add-Member -NotePropertyName 'mcpServers' -NotePropertyValue (New-Object psobject)
    } elseif ($null -eq $actual.mcpServers -or -not ($actual.mcpServers -is [psobject])) {
        $actual.mcpServers = New-Object psobject
    }
    $actual.mcpServers | Add-Member -NotePropertyName 'orca-mcp' -NotePropertyValue ([pscustomobject]$Entrada) -Force
    EscribirTexto $Ruta (ConvertTo-Json -InputObject $actual -Depth 64)
    $control = LeerJson $Ruta
    if (-not ((TienePropiedad $control 'mcpServers') -and (TienePropiedad $control.mcpServers 'orca-mcp'))) {
        if ($respaldo) { Copy-Item -LiteralPath $respaldo -Destination $Ruta -Force }
        throw 'No pude verificar la configuración nueva de la app: dejé la anterior.'
    }
    Anotar 'mcp-app' $Ruta
    Info 'Listo. Abrí la app de Claude de nuevo para que tome el cambio.'
}

# --- Programa ---------------------------------------------------------------------------------------
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    Write-Host 'Este instalador es para Windows. En Linux usá instalar.sh.'
    exit 1
}
$Arq = Arquitectura
if (-not $Arq) { Write-Host "No reconozco el procesador de esta PC ($env:PROCESSOR_ARCHITECTURE)."; exit 1 }
if ([Environment]::OSVersion.Version.Major -lt 10) { Write-Host 'Hace falta Windows 10 u 11.'; exit 1 }

$transcribiendo = $false
if (-not $Prueba) {
    New-Item -ItemType Directory -Path $Estado -Force | Out-Null
    try { Start-Transcript -LiteralPath $Registro | Out-Null; $transcribiendo = $true } catch { $transcribiendo = $false }
}

try {
    # --- 0. Revisión -------------------------------------------------------------------------------
    Paso 'Revisando tu PC'
    if ($Prueba) { Info 'Modo prueba: no cambio nada, solo te muestro lo que haría.' }
    $esAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
    if ($esAdmin -and -not $Prueba) {
        Aviso 'Estás corriendo esto como administrador. No hace falta: el instalador de Orca pide permiso por su cuenta.'
        if (-not (Preguntar '¿Sigo igual?')) { exit 1 }
    }
    if (Get-Process -Name 'orca-slicer', 'OrcaSlicer' -ErrorAction SilentlyContinue) {
        if ($Prueba) { Aviso 'OrcaSlicer está abierto: para instalar de verdad hay que cerrarlo.' }
        else { Write-Host 'Cerrá OrcaSlicer antes de seguir.'; exit 1 }
    }

    if ($Orca) {
        $Orca = $Orca.Trim().Trim('"')
        if (-not (Test-Path -LiteralPath $Orca -PathType Leaf)) { Write-Host "No encuentro $Orca."; exit 1 }
        $orcas = @(NuevoOrca $Orca 'indicado' '')
    } else {
        $orcas = @(BuscarOrca)
    }
    $tienda = OrcaDeTienda
    $app = AppDeClaude
    $orcaMcp = BuscarOrcaMcp
    $uv = BuscarUv
    $webview = TieneWebView2
    $blender = BuscarBlender
    # Carpeta de trabajo: la de -CarpetaTrabajo, la de una instalación anterior o, si no hay ninguna,
    # se pregunta en el paso 5 (proponiendo Documentos\Taller 3D).
    $CarpetaElegida = [bool]$CarpetaTrabajo
    if (-not $CarpetaElegida -and (Test-Path -LiteralPath $Manifiesto)) {
        $anterior = @(Get-Content -LiteralPath $Manifiesto -Encoding UTF8 | Where-Object { $_ -like "carpeta`t*" } |
            ForEach-Object { $_.Substring(8) }) | Select-Object -Last 1
        if ($anterior -and (Test-Path -LiteralPath (Join-Path $anterior 'taller-3d\config.json'))) {
            $CarpetaTrabajo = $anterior; $CarpetaElegida = $true
        }
    }
    if (-not $CarpetaTrabajo) { $CarpetaTrabajo = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Taller 3D' }
    $Config = Join-Path $CarpetaTrabajo 'taller-3d\config.json'
    $datosReales = Join-Path $env:APPDATA 'OrcaSlicer'
    $datosNuevos = Join-Path $env:USERPROFILE 'OrcaSlicer'
    $yaMovidos = EsEnlace $datosReales
    $appTieneMcp = $false
    $configClasica = Join-Path $env:APPDATA 'Claude\claude_desktop_config.json'
    $configQueLee = $null
    if ($app -and (Test-Path -LiteralPath $app.Config)) { $configQueLee = $app.Config }
    elseif ($app -and $app.Tipo -eq 'msix' -and (Test-Path -LiteralPath $configClasica)) { $configQueLee = $configClasica }
    if ($configQueLee) {
        $cfgApp = LeerJson $configQueLee
        $appTieneMcp = (TienePropiedad $cfgApp 'mcpServers') -and (TienePropiedad $cfgApp.mcpServers 'orca-mcp')
    }
    $mejor = $orcas | Where-Object { $_.Version -eq $OrcaVersion } | Select-Object -First 1
    if (-not $mejor -and $orcas.Count -gt 0) { $mejor = $orcas[0] }

    if ($mejor) { Fila $true 'OrcaSlicer' "$($mejor.Version) en $($mejor.Exe)" }
    elseif ($tienda) { Fila $false 'OrcaSlicer' 'solo está la versión de la Microsoft Store (Claude necesita la clásica)' }
    else { Fila $false 'OrcaSlicer' '' }
    if ($webview) { Fila $true 'WebView2 (lo usa Orca)' '' } else { Fila $false 'WebView2 (lo usa Orca)' 'Orca lo pide al abrirse si falta' }
    if ($app) {
        $tipoApp = 'versión clásica'
        if ($app.Tipo -eq 'msix') { $tipoApp = 'versión empaquetada (MSIX)' }
        Fila $true 'App de escritorio de Claude' $tipoApp
        if ($app.Tipo -eq 'msix') {
            if ($yaMovidos) { Fila $true 'Datos de Orca fuera de AppData' (DestinoDeEnlace $datosReales) }
            else { Fila $false 'Datos de Orca fuera de AppData' 'hace falta para que Orca vea los perfiles de Claude' }
        }
        if ($appTieneMcp) { Fila $true 'orca-mcp conectado en la app' '' } else { Fila $false 'orca-mcp conectado en la app' '' }
    } else {
        Fila $false 'App de escritorio de Claude' 'instalala desde https://claude.ai/download'
    }
    if ($orcaMcp) { Fila $true "orca-mcp" $orcaMcp } else { Fila $false "orca-mcp $OrcaMcpVersion" '' }
    if ($uv) { Fila $true 'uv' $uv } elseif (-not $orcaMcp) { Fila $false 'uv' 'lo bajo para instalar orca-mcp' }
    if (Test-Path -LiteralPath $Config) { Fila $true 'Carpeta de trabajo y configuración' $CarpetaTrabajo }
    else { Fila $false 'Carpeta de trabajo y configuración' $CarpetaTrabajo }
    if ($blender) { Info "[opcional] $blender" } else { Info '[opcional] Blender no está; solo hace falta para formas orgánicas' }

    # --- ¿La PC se banca lo que hay que instalar? (antes de cambiar nada) ------------------------------
    Paso '¿La PC alcanza?'
    $bajarOrca = (-not $mejor) -or ($mejor.Version -ne $OrcaVersion -and $mejor.Origen -ne 'indicado')
    $bajar = $bajarOrca -or (-not $orcaMcp)
    $hayInternet = $true
    if ($bajar) { $hayInternet = (ProbarInternet 'https://github.com') -and (ProbarInternet 'https://pypi.org/simple/orca-mcp/') }
    $esAdministrador = [bool](@(whoami /groups) -match 'S-1-5-32-544')
    $requisitos = @(EvaluarRequisitos (MedirPC) $bajarOrca $bajar $hayInternet $esAdministrador)
    foreach ($q in $requisitos) {
        switch ($q.Estado) {
            'ok' { Write-Host "   [ok]         $($q.Texto)" -ForegroundColor Green }
            'aviso' { Write-Host "   [aviso]      $($q.Texto)" -ForegroundColor Yellow }
            default { Write-Host "   [no alcanza] $($q.Texto)" -ForegroundColor Red }
        }
    }
    $faltan = @($requisitos | Where-Object { $_.Estado -eq 'no' })
    if ($faltan.Count -gt 0) {
        Write-Host ''
        Write-Host 'La PC no alcanza para instalar el taller. No cambié nada.' -ForegroundColor Red
        foreach ($q in $faltan) { Write-Host "   - $($q.Texto)" }
        Write-Host 'Si lo corregís (por ejemplo, liberando disco o conectándote a internet), volvé a correr el instalador.'
        exit 1
    }

    # --- 1. Aviso de uso -----------------------------------------------------------------------------
    Paso 'Aviso de uso'
    $aviso = @((Join-Path $PSScriptRoot 'DISCLAIMER.md'), (Join-Path (Split-Path -Parent $PSScriptRoot) 'DISCLAIMER.md')) |
        Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if ($aviso) {
        Get-Content -LiteralPath $aviso -Encoding UTF8 | ForEach-Object { Write-Host $_ }
    } else {
        Write-Host 'Este software se ofrece tal cual, sin garantías. Lo usás bajo tu exclusiva cuenta y riesgo.'
        Write-Host 'La impresión 3D implica calor, electricidad y vapores: no dejes la impresora sin supervisión.'
    }
    if (-not $Prueba) {
        $r = [string](Read-Host 'Para seguir, escribí ACEPTO')
        if ($r.Trim() -cne 'ACEPTO') { Write-Host 'No se instaló nada.'; exit 1 }
    }
    $AceptacionFecha = (Get-Date).ToString('yyyy-MM-ddTHH:mm:sszzz')

    # --- 2. Datos de Orca fuera de AppData (solo con la app MSIX) -------------------------------------
    $DatosOrca = $datosReales
    if ($yaMovidos) { $DatosOrca = DestinoDeEnlace $datosReales }
    if ($app -and $app.Tipo -eq 'msix' -and -not $yaMovidos) {
        Paso 'Datos de Orca fuera de AppData'
        Info 'La app de Claude de Windows guarda en un lugar privado los archivos nuevos que crea dentro de AppData,'
        Info 'y Orca no los ve. Para que Orca vea los perfiles que arma Claude, muevo la carpeta de datos de Orca'
        Info "a $datosNuevos y dejo un acceso (unión de carpetas) en el lugar de siempre."
        Info 'Orca sigue funcionando igual y tus perfiles quedan como están.'
        if (Test-Path -LiteralPath $datosNuevos) {
            Aviso "Ya existe $datosNuevos y no lo toco. Renombralo y volvé a correr el instalador."
        } elseif ($Prueba) {
            EnPrueba "movería $datosReales a $datosNuevos y dejaría un acceso en $datosReales"
            $DatosOrca = $datosNuevos
        } elseif (Preguntar '¿La muevo?') {
            $movida = $false
            try {
                if (Test-Path -LiteralPath $datosReales) {
                    Move-Item -LiteralPath $datosReales -Destination $datosNuevos -ErrorAction Stop
                    $movida = $true
                } else {
                    New-Item -ItemType Directory -Path $datosNuevos -ErrorAction Stop | Out-Null
                }
                New-Item -ItemType Junction -Path $datosReales -Target $datosNuevos -ErrorAction Stop | Out-Null
            } catch {
                $motivo = $_.Exception.Message
                if ($movida -and -not (Test-Path -LiteralPath $datosReales)) {
                    try { Move-Item -LiteralPath $datosNuevos -Destination $datosReales -ErrorAction Stop }
                    catch {
                        throw ("No pude crear el acceso ($motivo) ni devolver la carpeta: tus datos de Orca quedaron en " +
                               "$datosNuevos. Movela a mano a $datosReales antes de abrir Orca.")
                    }
                } elseif (-not $movida -and (Test-Path -LiteralPath $datosNuevos) -and
                          -not (Get-ChildItem -LiteralPath $datosNuevos -Force -ErrorAction SilentlyContinue)) {
                    Remove-Item -LiteralPath $datosNuevos -Force -ErrorAction SilentlyContinue
                }
                throw "No pude mover la carpeta de datos de Orca: $motivo. La dejé como estaba."
            }
            Anotar 'union' "$datosReales|$datosNuevos"
            $DatosOrca = $datosNuevos
            Info "Listo: $datosReales ahora apunta a $datosNuevos."
        } else {
            Aviso 'Sin esto, Orca no va a ver los perfiles que escriba Claude. Podés volver a correr el instalador más adelante.'
        }
    }

    # --- 3. OrcaSlicer ---------------------------------------------------------------------------------
    Paso "OrcaSlicer $OrcaVersion"
    $OrcaExe = $null
    $OrcaOrigen = $null
    $OrcaVersionUsada = $null
    $instalar = $false
    if ($mejor) {
        if ($mejor.Version -eq $OrcaVersion -or $mejor.Origen -eq 'indicado') {
            Info "Uso el que ya tenés: $($mejor.Exe) ($($mejor.Version))."
            $OrcaExe = $mejor.Exe
        } else {
            Info "Tenés OrcaSlicer $($mejor.Version) en $($mejor.Exe). El taller está probado con la $OrcaVersion."
            if (Preguntar "¿Instalo la $OrcaVersion oficial? Si decís que no, uso la que tenés") { $instalar = $true }
            else { $OrcaExe = $mejor.Exe }
        }
        if ($OrcaExe) {
            $OrcaOrigen = $mejor.Origen
            $OrcaVersionUsada = $mejor.Version
            if (-not $yaMovidos -and $mejor.Datos -ne $datosReales) { $DatosOrca = $mejor.Datos }
        }
    } elseif ($tienda) {
        $vt = ''
        if ($tienda.Version) { $vt = " ($($tienda.Version))" }
        Info "Tenés OrcaSlicer de la Microsoft Store$vt. Claude no lo puede usar de forma confiable para laminar;"
        Info 'la versión clásica comparte los mismos perfiles, así que se pueden tener las dos.'
        $instalar = $true
        if (-not $Prueba -and -not (Preguntar "¿Instalo la clásica $OrcaVersion al lado?")) { $instalar = $false }
    } else {
        Info 'No encontré OrcaSlicer instalado.'
        if (Preguntar '¿Tenés OrcaSlicer portable (sin instalar) en alguna carpeta?') {
            $ruta = ([string](Read-Host '   Pegá la ruta de orca-slicer.exe')).Trim().Trim('"')
            if ($ruta -and (Test-Path -LiteralPath $ruta -PathType Leaf)) {
                $portable = NuevoOrca $ruta 'portable' ''
                $OrcaExe = $portable.Exe
                $OrcaOrigen = 'portable'
                $OrcaVersionUsada = $portable.Version
                $DatosOrca = $portable.Datos
                if ($app -and $app.Tipo -eq 'msix' -and $DatosOrca -like "$env:LOCALAPPDATA*") {
                    Aviso 'Los datos de ese Orca están dentro de AppData: Orca no va a ver los perfiles que escriba Claude.'
                    Aviso 'Mové la carpeta del Orca portable a otro lugar (por ejemplo, C:\OrcaSlicer) y volvé a correr.'
                }
            } else {
                Aviso "No encontré $ruta."
                $instalar = Preguntar "¿Instalo la $OrcaVersion oficial?"
            }
        } else {
            $instalar = $true
        }
    }

    if ($instalar) {
        $d = $OrcaArchivos[$Arq]
        $url = "$OrcaBase/$($d.Archivo)"
        Info "Instalador oficial (~$($d.Mb) MB): $url"
        if ($Prueba) {
            EnPrueba 'lo bajaría, verificaría la huella SHA-256 y la firma digital, y lo abriría para que lo instales'
            $OrcaExe = Join-Path $env:ProgramFiles 'OrcaSlicer\orca-slicer.exe'
            $OrcaOrigen = 'oficial'
            $OrcaVersionUsada = $OrcaVersion
        } else {
            $temporal = Join-Path $env:TEMP 'taller-3d'
            New-Item -ItemType Directory -Path $temporal -Force | Out-Null
            $instalador = Join-Path $temporal $d.Archivo
            Bajar $url $instalador
            if (-not (HuellaOk $instalador $d.Sha256)) {
                Remove-Item -LiteralPath $instalador -Force
                throw 'La huella SHA-256 del instalador de Orca no coincide: lo descarté. No se instaló Orca.'
            }
            Info 'Huella SHA-256 verificada.'
            $firma = Get-AuthenticodeSignature -LiteralPath $instalador
            if ($firma.Status -eq 'Valid' -and $firma.SignerCertificate.Subject -match [regex]::Escape($OrcaFirmante)) {
                Info "Firma digital verificada: $OrcaFirmante."
            } else {
                Aviso "No pude verificar la firma digital ($($firma.Status)). La huella coincide con la publicada, así que sigo."
            }
            Info 'Se abre el instalador de Orca y Windows te pide permiso. Seguí sus pasos; al final podés abrir Orca.'
            $proceso = Start-Process -FilePath $instalador -PassThru
            $proceso.WaitForExit()
            Remove-Item -LiteralPath $instalador -Force -ErrorAction SilentlyContinue
            $nuevo = @(BuscarOrca) | Where-Object { $_.Version -eq $OrcaVersion } | Select-Object -First 1
            if (-not $nuevo) {
                throw 'No encuentro Orca después de instalarlo. Si lo pusiste en otra carpeta, volvé a correr con -Orca "<ruta de orca-slicer.exe>".'
            }
            $OrcaExe = $nuevo.Exe
            $OrcaOrigen = 'oficial'
            $OrcaVersionUsada = $OrcaVersion
            Anotar 'orca-instalado' $OrcaExe
            Info "Instalado: $OrcaExe"
        }
    }
    if (-not $OrcaExe) {
        Aviso 'Sigo sin Orca: instalalo y volvé a correr el instalador (saltea lo que ya esté).'
    }
    if (-not $webview) {
        Aviso 'Orca necesita Microsoft Edge WebView2. Si al abrirlo te lo pide: https://developer.microsoft.com/microsoft-edge/webview2/'
    }

    # --- 4. orca-mcp -------------------------------------------------------------------------------------
    Paso "orca-mcp $OrcaMcpVersion (conexión Claude - Orca)"
    if ($orcaMcp) {
        Info "Ya está instalado: $orcaMcp"
    } else {
        if (-not $uv) {
            $d = $UvArchivos[$Arq]
            $carpetaUv = Join-Path $Estado 'uv'
            Info "Para instalarlo aislado uso uv $UvVersion (de Astral, el mismo que recomienda orca-mcp)."
            if ($Prueba) {
                EnPrueba "bajaría $UvBase/$($d.Archivo), verificaría la huella y lo dejaría en $carpetaUv"
            } else {
                $zip = Join-Path $env:TEMP "taller-3d\$($d.Archivo)"
                New-Item -ItemType Directory -Path (Split-Path -Parent $zip) -Force | Out-Null
                Bajar "$UvBase/$($d.Archivo)" $zip
                if (-not (HuellaOk $zip $d.Sha256)) {
                    Remove-Item -LiteralPath $zip -Force
                    throw 'La huella SHA-256 de uv no coincide: lo descarté. No se instaló orca-mcp.'
                }
                Expand-Archive -LiteralPath $zip -DestinationPath $carpetaUv -Force
                Remove-Item -LiteralPath $zip -Force
                Anotar 'archivo' $carpetaUv
                $uv = Join-Path $carpetaUv 'uv.exe'
                Info "uv verificado: $uv"
            }
        }
        if ($Prueba) {
            EnPrueba "uv tool install --python 3.12 orca-mcp==$OrcaMcpVersion"
        } else {
            & $uv tool install --python 3.12 "orca-mcp==$OrcaMcpVersion"
            if ($LASTEXITCODE -ne 0) { throw "uv no pudo instalar orca-mcp (código $LASTEXITCODE)." }
            Anotar 'uv' "orca-mcp|$uv"
            $bin = [string](& $uv tool dir --bin | Select-Object -First 1)
            if ($LASTEXITCODE -ne 0 -or -not $bin.Trim()) { $bin = Join-Path $env:USERPROFILE '.local\bin' }
            $orcaMcp = Join-Path $bin.Trim() 'orca-mcp.exe'
            Info "Instalado: $orcaMcp"
        }
    }
    if (-not $orcaMcp) { $orcaMcp = Join-Path $env:USERPROFILE '.local\bin\orca-mcp.exe' }

    # --- 5. Carpeta de trabajo ---------------------------------------------------------------------------
    Paso 'Carpeta de trabajo'
    if (-not $CarpetaElegida -and -not (Test-Path -LiteralPath $Config)) {
        Info 'Acá van a quedar tus diseños, impresiones (con sus vistas y G-code), respaldos y la configuración.'
        if ($Prueba) {
            EnPrueba "te preguntaría dónde guardarlos (si apretás Enter: $CarpetaTrabajo)"
        } else {
            while ($true) {
                $r = ([string](Read-Host "   ¿Dónde los guardo? Enter = $CarpetaTrabajo, o escribí otra carpeta")).Trim().Trim('"')
                if (-not $r) { break }
                if ($r.StartsWith('~')) { $r = $env:USERPROFILE + $r.Substring(1) }
                if (-not [System.IO.Path]::IsPathRooted($r) -or $r.StartsWith('\\')) {
                    Info 'Escribí la ruta completa de una carpeta de esta PC (por ejemplo D:\Impresiones 3D).'; continue
                }
                $r = [System.IO.Path]::GetFullPath($r).TrimEnd('\')
                $bajo = $r.ToLowerInvariant() + '\'
                if ((Test-Path -LiteralPath $r) -and -not (Test-Path -LiteralPath $r -PathType Container)) {
                    Info "'$r' es un archivo, no una carpeta."; continue
                }
                $prohibidas = @($env:APPDATA, $env:LOCALAPPDATA, $datosNuevos) | Where-Object { $_ } |
                    ForEach-Object { $_.ToLowerInvariant().TrimEnd('\') + '\' }
                if ($bajo -eq ($env:USERPROFILE.ToLowerInvariant().TrimEnd('\') + '\') -or
                    @($prohibidas | Where-Object { $bajo.StartsWith($_) }).Count -gt 0) {
                    Info 'Elegí una carpeta propia: ni AppData (la app de Claude no la vería), ni la de Orca, ni tu carpeta personal entera.'
                    continue
                }
                $CarpetaTrabajo = $r; $Config = Join-Path $CarpetaTrabajo 'taller-3d\config.json'; break
            }
        }
    }
    foreach ($sub in @('impresiones', 'disenos', 'respaldos', 'calibraciones', 'taller-3d\impresoras')) {
        $p = Join-Path $CarpetaTrabajo $sub
        if (Test-Path -LiteralPath $p) { continue }
        if ($Prueba) { EnPrueba "crearía $p" } else { New-Item -ItemType Directory -Path $p -Force | Out-Null }
    }
    if (Test-Path -LiteralPath $Config) {
        Info "Ya existe la configuración: $Config (no la toco)."
    } elseif ($Prueba) {
        EnPrueba "crearía $Config y historial.csv"
    } else {
        $conf = [ordered]@{
            version         = 1
            carpeta_trabajo = $CarpetaTrabajo
            aceptacion      = [ordered]@{ fecha = $AceptacionFecha; version_plugin = $VersionPlugin; texto = 'ACEPTO'; medio = 'instalar.ps1' }
            orca            = [ordered]@{ version = $OrcaVersionUsada; ejecutable = $OrcaExe; origen = $OrcaOrigen
                                          carpeta_usuario = (Join-Path $DatosOrca 'user\default') }
            impresora_por_defecto = $null
            impresoras      = @()
            costos          = [ordered]@{ moneda = 'ARS'; precio_kwh = $null; consumo_w = 180; filamentos = @{} }
            tienda          = [ordered]@{ plataforma = $null; url = $null; margen_pct = $null; costo_hora_maquina = $null
                                          embalaje = $null; redondeo = 100; demora_dias = $null; peso_embalaje_g = 50
                                          categoria_por_defecto = $null }
        }
        EscribirTexto $Config (ConvertTo-Json -InputObject $conf -Depth 10)
        EscribirTexto (Join-Path $CarpetaTrabajo 'taller-3d\historial.csv') (
            "fecha;accion;pieza_o_perfil;archivo;resultado`r`n{0};instalacion;-;-;ok`r`n" -f $AceptacionFecha)
        Anotar 'carpeta' $CarpetaTrabajo
    }
    Info "Carpeta: $CarpetaTrabajo"

    # --- 6. App de Claude ----------------------------------------------------------------------------------
    Paso 'Conexión con la app de Claude'
    $exeParaApp = $OrcaExe
    if (-not $exeParaApp) { $exeParaApp = Join-Path $env:ProgramFiles 'OrcaSlicer\orca-slicer.exe' }
    $entrada = [ordered]@{ command = $orcaMcp; env = [ordered]@{ ORCASLICER_PATH = $exeParaApp; ORCASLICER_CONFIG_DIR = $DatosOrca } }
    Info 'Esta es la entrada de orca-mcp para la app de Claude:'
    Write-Host (ConvertTo-Json -InputObject ([ordered]@{ mcpServers = [ordered]@{ 'orca-mcp' = $entrada } }) -Depth 5)
    if ($SinApp) {
        Info 'No toco la configuración de la app (-SinApp).'
    } elseif (-not $app) {
        Aviso 'No encontré la app de escritorio de Claude. Instalala desde https://claude.ai/download y volvé a correr este instalador.'
    } elseif ($appTieneMcp) {
        Info 'La app ya tiene un orca-mcp configurado: no lo cambio.'
    } elseif ($Prueba) {
        EnPrueba "la agregaría a $($app.Config), con copia de respaldo y con la app cerrada"
    } elseif (Preguntar '¿La agrego yo a la configuración de la app? (hago una copia de respaldo antes)') {
        while (AppDeClaudeAbierta) {
            Aviso 'Cerrá la app de Claude del todo (también desde el ícono junto al reloj). Lo que tenías en Claude no se pierde.'
            $r = [string](Read-Host '   Apretá Enter cuando esté cerrada, o escribí SALTEAR')
            if ($r.Trim() -eq 'SALTEAR') { break }
        }
        if (AppDeClaudeAbierta) {
            Aviso 'La app sigue abierta: no toqué su configuración. Agregá la entrada de arriba a mano, con la app cerrada.'
        } else {
            if ($app.Tipo -eq 'msix' -and -not (Test-Path -LiteralPath $app.Config) -and (Test-Path -LiteralPath $configClasica)) {
                # Sin configuración propia, la app de la Tienda lee la de la versión clásica. Si se crea una nueva
                # con solo orca-mcp, deja de ver lo que había: se parte de una copia de la clásica.
                Info 'La app de la Tienda está usando la configuración de la versión clásica: parto de una copia, así no se pierde nada.'
                New-Item -ItemType Directory -Path (Split-Path -Parent $app.Config) -Force | Out-Null
                Copy-Item -LiteralPath $configClasica -Destination $app.Config
            }
            AgregarAConfigApp $app.Config $entrada
        }
    }

    # --- 7. Resumen ---------------------------------------------------------------------------------------
    Paso 'Listo'
    Info "Orca: $exeParaApp"
    Info "Datos de Orca: $DatosOrca"
    Info "orca-mcp: $orcaMcp"
    Info "Carpeta de trabajo: $CarpetaTrabajo"
    if (-not $Prueba) { Info "Registro de la instalación: $Registro" }
    $proceso = Join-Path $DatosOrca 'user\default\process'
    $filamento = Join-Path $DatosOrca 'user\default\filament'
    Write-Host ''
    Write-Host 'Próximos pasos:'
    Write-Host '  1. Abrí OrcaSlicer una vez y agregá tu impresora con el asistente. Guardá una copia de usuario del'
    Write-Host '     perfil de la impresora, por ejemplo "Mi <modelo> 0.4 nozzle", y un perfil propio de proceso y de'
    Write-Host '     filamento: así Orca crea las carpetas de perfiles.'
    Write-Host '  2. En la app de Claude, conectá estas carpetas (menú + > Agregar carpeta), con estas rutas exactas:'
    Write-Host "     - $CarpetaTrabajo"
    Write-Host "     - $proceso"
    Write-Host "     - $filamento"
    if ($DatosOrca -ne $datosReales) {
        Write-Host '     No las conectes pasando por AppData: Orca no vería lo que escribe Claude.'
    }
    Write-Host '  3. Instalá el plugin taller-3d en Claude (si no lo hiciste) y escribí: /instalar'
    Write-Host '     Claude revisa que todo ande, registra tu impresora y hace una pieza de prueba.'
} catch {
    Write-Host ''
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'Paré acá. Lo que ya quedó hecho está anotado y se deshace con desinstalar-windows.bat.' -ForegroundColor Red
    exit 1
} finally {
    if ($transcribiendo) { Stop-Transcript | Out-Null }
}
