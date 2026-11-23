#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
"""Guardia de seguridad de taller-3d (hooks).

Modos:
  pre-commit  Antes de escribir archivos en la PC con device_commit_files: revisa los G-code,
              proyectos .3mf y perfiles de Orca que se van a escribir, y bloquea si no pasan.
  pre-write   Lo mismo para Write / Edit / MultiEdit (Claude Code en la propia PC).
  pre-bash    Antes de un comando de terminal (Bash o device_bash): bloquea arrancar impresiones
              por red, subir modelos o G-code a internet, escribir en la carpeta de Orca y leer,
              copiar o empaquetar OrcaSlicer.conf (o la carpeta de datos de Orca entera).
  pre-stage   Antes de traer archivos de la PC (device_stage_files): no deja traer OrcaSlicer.conf,
              sus copias ni nada de la carpeta de datos de Orca fuera de user/ y system/.
  pre-read    Lo mismo para Read y Grep (Claude Code en la propia PC).
  post-slice  Después de laminar: recuerda revisar el G-code antes de entregarlo.

Tampoco deja traer, leer, copiar ni escribir la conexión con la tienda (credenciales-tienda.json, con la contraseña de
aplicación de WordPress): la usa solo el conector local taller3d-tienda y la guarda el usuario en una terminal.

Nunca deja escribir en los perfiles de sistema de Orca, en sus plugins ni en su configuración.
Con un archivo de impresión 3D (G-code, .3mf o perfil) falla cerrado: si no lo puede leer o
revisar, no lo deja escribir. Con cualquier otro archivo o comando, ante un error propio deja
pasar, para no trabar trabajos que no tienen que ver con la impresión 3D.
"""
from __future__ import annotations

import fnmatch
import io
import json
import posixpath
import re
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "skills" / "impresion-3d" / "scripts"))

# --- Comandos de terminal -------------------------------------------------------------------
PATRONES_IMPRESION = [
    r"/printer/print/(start|resume)", r"/printer/gcode/script", r"sdcard_print_file", r"/api/job\b",
    r"/api/v1/job\b", r"print-after-upload", r"print=true", r"\bm24\b",
    r"/api/files/(local|sdcard)/[^\s]*\s.*select", r'"command"\s*:\s*"(start|print)"',
    r"\b(project_file|gcode_file)\b",
]
HERRAMIENTAS_RED = (r"\b(curl|wget|http|https|xh|nc|ncat|netcat|socat|websocat|wscat|httpie|requests|"
                    r"urllib|aiohttp|httpx|websocket|mosquitto_pub|paho|mqtt|invoke-webrequest|"
                    r"invoke-restmethod|iwr|irm)\b")
# Al principio de un comando (o después de ; | & o paréntesis)
INICIO = r"(?:^|[;&|(`]\s*|\b(?:sudo|exec|xargs)\s+)"
# Opciones de curl y wget que suben archivos. Distinguen mayúsculas: -T y -F suben, -t y -f no.
SUBIDA_CURL = re.compile(r"\b(curl|wget)\b[^|;&]*(\s-[a-zA-Z]*[TF]|--upload-file|--form\b|--data[\w-]*\s*=?\s*@"
                         r"|\s-[a-zA-Z]*d\s*@|--json\s+@|--post-file|--body-file)")
SUBIDA = [
    r"\b(scp|rsync)\b.*\s[\w.-]+(@[\w.-]+)?:",
    INICIO + r"(s?ftp|lftp|ncftp\w*|tftp)\b",
    r"\b\w+\.(post|put|patch)\(",
    r"\brclone\s+(copy|copyto|move|moveto|sync)\b",
    r"\b(aws\s+s3\s+(cp|mv|sync)|gsutil\s+(cp|mv|rsync)|gcloud\s+storage\s+cp|az\s+storage\s+blob\s+upload)\b",
    r"\bgh\s+(gist\s+create|release\s+upload)\b",
    r"\b(nc|ncat|netcat|socat)\b[^|;&]*<|\|\s*(nc|ncat|netcat|socat)\b",
    INICIO + r"(https?|xh|http(ie)?)\s+(-\S+\s+)*(post|put|patch)\b",
    r"invoke-(webrequest|restmethod)\b.*-(infile|method\s+(post|put))",
]
ARCHIVOS_3D = r"\.(stl|3mf|gcode|gco|gc|g|bgcode|step|stp|obj|amf|ply|blend)\b|orcaslicer|/mnt/user-data/uploads"
CARPETA_ORCA = re.compile(r"orcaslicer[/\\]+(user|system|orca_plugins|resources)\b|data_dir[/\\]+(user|system|orca_plugins)\b"
                          r"|orca_plugins|orcaslicer\.conf")
RE_TOKEN = re.compile(r'"[^"]*"|\'[^\']*\'|[^\s"\']+')
COPIAN = {"cp", "mv", "install", "ln", "rsync", "scp", "ditto", "copy-item", "move-item", "copy", "move", "xcopy",
          "robocopy", "cpi", "mi"}
TOCAN = {"rm", "rmdir", "unlink", "truncate", "shred", "dd", "touch", "mkdir", "chmod", "chown", "patch", "unzip",
         "7z", "remove-item", "del", "erase", "rd", "ri", "set-content", "add-content", "out-file", "new-item", "ni",
         "sc", "ac"}
PREFIJOS = {"sudo", "env", "exec", "command", "nohup", "time", "doas"}
ESCRIBE_SCRIPT = re.compile(r"write_(text|bytes)|open\([^)]*['\"][wax]|writefilesync|copyfile|shutil\.(copy|move)"
                            r"|\[io\.file\]::write")

# --- Archivos -------------------------------------------------------------------------------
EXT_GCODE = (".gcode", ".gco", ".gc", ".g")
RE_PERFIL_USUARIO = re.compile(r"/user/[^/]+/(process|filament|machine)/(?:[^/]+/)*[^/]+\.json$")
RE_PERFIL_SISTEMA = re.compile(r"/system/[^/]+/(machine|process|filament)/(?:[^/]+/)*[^/]+\.json$")


def bloquear(mensaje: str) -> None:
    print(mensaje, file=sys.stderr)
    sys.exit(2)


def normalizar(ruta: str) -> str:
    """Ruta en minúsculas, con / y sin . ni .. (sin tocar el disco)."""
    r = str(ruta).replace("\\", "/").strip().lower()
    unidad = ""
    m = re.match(r"^([a-z]:)(/.*)?$", r)
    if m:
        unidad, r = m.group(1), m.group(2) or "/"
    return unidad + (posixpath.normpath(r) if r else r)


def zona_prohibida(bajo: str) -> str | None:
    if re.search(r"/(orcaslicer|data_dir)/system(/|$)", bajo) or RE_PERFIL_SISTEMA.search(bajo):
        return "no se tocan los perfiles de sistema de Orca"
    if "orcaslicer" in bajo and "/resources/profiles/" in bajo:
        return "no se tocan los perfiles que vienen con Orca"
    if "/orca_plugins/" in bajo or bajo.endswith("/orca_plugins"):
        return "no se instalan plugins de Orca (si querés uno, instalalo vos desde Orca)"
    if _es_nombre_conf(bajo.rsplit("/", 1)[-1], True):
        return "no se toca la configuración de Orca"
    return None


def tipo_de_archivo(bajo: str) -> str | None:
    if bajo.endswith(".bgcode"):
        return "bgcode"
    if bajo.endswith(EXT_GCODE):
        return "gcode"
    if bajo.endswith(".3mf"):
        return "3mf"
    if bajo.endswith(".json") and ("/orcaslicer/user/" in bajo or "/data_dir/user/" in bajo
                                   or RE_PERFIL_USUARIO.search(bajo)):
        return "perfil"
    return None


def parece_gcode(datos: bytes) -> bool:
    lineas = [x.split(";", 1)[0].strip() for x in datos[:200_000].decode("utf-8", "replace").splitlines()]
    comandos = [x for x in lineas if x]
    return sum(bool(re.match(r"(N\d+\s*)?[GM]\d", x, re.I)) for x in comandos[:300]) >= 3


def _rechazos(hallazgos: list[dict]) -> list[str]:
    import comun
    return [h["mensaje"] for h in hallazgos if h["gravedad"] == comun.RECHAZO]


# Dónde puede haber datos de impresoras del usuario (taller-3d/impresoras/*.json): las copias traídas de la
# PC y las salidas en el espacio de Claude. El plugin no trae impresoras; si no hay datos, límites genéricos.
RAICES_DATOS = [Path("/mnt/user-data/uploads"), Path("/mnt/user-data/outputs")]


def _impresoras_del_usuario() -> list[dict]:
    import comun
    carpetas = []
    for raiz in RAICES_DATOS:
        for patron in ("taller-3d/impresoras", "*/taller-3d/impresoras", "*/*/taller-3d/impresoras"):
            try:
                carpetas += [c for c in raiz.glob(patron) if c.is_dir()]
            except OSError:
                continue
    return comun.impresoras_en(carpetas)


def _impresora_para(modelo: str, perfil: str) -> dict:
    """Los datos de la impresora del usuario que correspondan; si no hay, límites genéricos."""
    import revisar_gcode
    return revisar_gcode.elegir_impresora(modelo, perfil, _impresoras_del_usuario()) or revisar_gcode.IMPRESORA_GENERICA


def _impresora_de_perfil(perfil: dict) -> dict:
    """La impresora de un perfil: por su perfil de máquina, su nombre, de quién hereda o sus impresoras compatibles."""
    import revisar_gcode
    candidatas = _impresoras_del_usuario()
    modelo = perfil.get("printer_model") if isinstance(perfil.get("printer_model"), str) else ""
    nombres = [perfil.get("printer_settings_id"), perfil.get("name"), perfil.get("inherits")]
    compatibles = perfil.get("compatible_printers")
    nombres += compatibles if isinstance(compatibles, list) else []
    for nombre in nombres:
        if isinstance(nombre, str) and nombre.strip():
            datos = revisar_gcode.elegir_impresora(modelo, nombre, candidatas)
            if datos:
                return datos
    return revisar_gcode.IMPRESORA_GENERICA


def _revisar_gcode(texto: str) -> list[str]:
    import revisar_gcode
    impresora = revisar_gcode.detectar_impresora(None, texto=texto, candidatas=_impresoras_del_usuario())
    return _rechazos(revisar_gcode.revisar(None, impresora, texto=texto)["hallazgos"])


def _revisar_ajustes_3mf(ajustes: dict) -> list[str]:
    """Ajustes de un proyecto .3mf: nada que ejecute código, G-code de la máquina sano y temperaturas."""
    import perfil_orca
    problemas = []
    catalogo = __import__("comun").cargar_catalogo()
    impresora = _impresora_para(str(ajustes.get("printer_model", "")), str(ajustes.get("printer_settings_id", "")))
    for clave, valor in ajustes.items():
        if clave in perfil_orca.CLAVES_QUE_EJECUTAN and perfil_orca._tiene_valor(valor):
            problemas.append(f"'{clave}' {perfil_orca.CLAVES_QUE_EJECUTAN[clave]}")
            continue
        valores = valor if isinstance(valor, list) else [valor]
        for v in valores:
            if perfil_orca.es_clave_gcode(clave, catalogo.get(clave)):
                problemas += [m for g, m in perfil_orca.revisar_fragmento(clave, v, impresora) if g == "rechazo"]
            problemas += [m for g, m in perfil_orca._seguridad(clave, str(v), impresora, None) if g == "rechazo"]
    return problemas


def _revisar_3mf(datos: bytes) -> list[str]:
    problemas = []
    with zipfile.ZipFile(io.BytesIO(datos)) as z:
        for nombre in z.namelist():
            bajo = nombre.lower()
            if bajo.endswith(".gcode"):
                problemas += [f"{nombre}: {m}" for m in _revisar_gcode(z.read(nombre).decode("utf-8", "replace"))]
            elif bajo.endswith("project_settings.config"):
                ajustes = json.loads(z.read(nombre).decode("utf-8"))
                if isinstance(ajustes, dict):
                    problemas += [f"{nombre}: {m}" for m in _revisar_ajustes_3mf(ajustes)]
    return problemas


def _revisar_perfil(bajo: str, datos: bytes) -> list[str]:
    import perfil_orca
    tipo = next((t for t, conf in perfil_orca.TIPOS.items() if f"/{conf['carpeta']}/" in bajo), None)
    if tipo is None:
        return []
    try:
        perfil = json.loads(datos.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        return [f"no es un perfil válido (JSON roto: {error})"]
    if not isinstance(perfil, dict):
        return ["no es un perfil válido (se esperaba un objeto JSON)"]
    return _rechazos(perfil_orca.validar(perfil, tipo, _impresora_de_perfil(perfil)))


def revisar_archivo(destino: str, leer) -> list[str]:
    """Problemas de un archivo que se va a escribir en `destino`. `leer()` devuelve sus bytes."""
    bajo = normalizar(destino)
    prohibida = zona_prohibida(bajo)
    if prohibida:
        return [f"{destino}: {prohibida}."]
    tipo = tipo_de_archivo(bajo)
    if tipo is None:
        return []
    if tipo == "bgcode":
        return [f"{destino}: no puedo revisar G-code binario (.bgcode); exportalo como .gcode."]
    try:
        datos = leer()
        if tipo == "gcode" and bajo.endswith((".g", ".gc")) and not parece_gcode(datos):
            return []
        if tipo == "gcode":
            motivos = _revisar_gcode(datos.decode("utf-8", "replace"))
            que = "el G-code no pasó la revisión de seguridad"
        elif tipo == "3mf":
            motivos = _revisar_3mf(datos)
            que = "el proyecto .3mf no pasó la revisión de seguridad"
        else:
            motivos = _revisar_perfil(bajo, datos)
            que = "el perfil no pasó la validación"
    except Exception as error:  # con archivos de impresión, falla cerrado
        return [f"{destino}: no pude revisarlo ({type(error).__name__}: {error}), así que no lo escribo."]
    return [f"{destino}: {que} ({'; '.join(motivos)})."] if motivos else []


# --- La conexión con la tienda ---------------------------------------------------------------------------------
# credenciales-tienda.json guarda la contraseña de aplicación de WordPress. La escribe el usuario en una terminal
# (tienda_mcp.py configurar) y la lee solo el conector local. Claude no la trae, no la lee, no la copia ni la escribe.
AVISO_TIENDA = ("taller-3d: credenciales-tienda.json guarda la contraseña de aplicación de tu tienda: no se trae, no "
                "se lee, no se copia ni se escribe desde Claude. La usa solo el conector local taller3d-tienda. Para "
                "cambiarla, el usuario corre en una terminal: python3 ~/.local/share/taller-3d/tienda_mcp.py configurar")
RE_TIENDA = re.compile(r"credenciales-tienda|\.config/taller-3d(/|$|\s|\*|\?|\[|\"|')"
                       r"|appdata[/\\]roaming[/\\]taller-3d|appdata%?[/\\]taller-3d", re.I)


def es_conexion_tienda(texto: str) -> bool:
    return bool(RE_TIENDA.search(str(texto).replace("\\", "/")))


def pre_commit(datos: dict) -> None:
    problemas = []
    for archivo in (datos.get("tool_input") or {}).get("files") or []:
        if not isinstance(archivo, dict):
            continue
        destino = str(archivo.get("devicePath", ""))
        if es_conexion_tienda(destino):
            bloquear(AVISO_TIENDA)
        bajo = normalizar(destino)
        prohibida = zona_prohibida(bajo)
        if prohibida:
            problemas.append(f"{destino}: {prohibida}.")
            continue
        if tipo_de_archivo(bajo) is None:
            continue
        if archivo.get("fileUuid"):
            problemas.append(f"{destino}: los G-code, proyectos .3mf y perfiles se escriben con stagedPath (un "
                             "archivo de /mnt/user-data/outputs), no con fileUuid, para poder revisarlos.")
            continue
        local = archivo.get("stagedPath")
        if not local:
            problemas.append(f"{destino}: falta stagedPath, no puedo revisar el archivo.")
            continue
        problemas += revisar_archivo(destino, lambda ruta=Path(local): ruta.read_bytes())
    if problemas:
        bloquear("taller-3d bloqueó la escritura en la PC:\n- " + "\n- ".join(problemas)
                 + "\nCorregí el archivo y volvé a intentarlo.")


def _contenido_editado(entrada: dict) -> bytes:
    ruta = Path(str(entrada.get("file_path", "")))
    texto = ruta.read_text(encoding="utf-8") if ruta.is_file() else ""
    for edicion in entrada.get("edits") or [entrada]:
        viejo, nuevo = str(edicion.get("old_string", "")), str(edicion.get("new_string", ""))
        if not viejo:
            texto = nuevo if not texto else texto
        elif viejo not in texto:
            raise ValueError("el texto a reemplazar no está en el archivo")
        else:
            texto = texto.replace(viejo, nuevo) if edicion.get("replace_all") else texto.replace(viejo, nuevo, 1)
    return texto.encode("utf-8")


def pre_write(datos: dict) -> None:
    entrada = datos.get("tool_input") or {}
    destino = str(entrada.get("file_path") or entrada.get("notebook_path") or "")
    if not destino:
        return
    if es_conexion_tienda(destino):
        bloquear(AVISO_TIENDA)
    if "content" in entrada:
        problemas = revisar_archivo(destino, lambda: str(entrada.get("content", "")).encode("utf-8"))
    else:
        problemas = revisar_archivo(destino, lambda: _contenido_editado(entrada))
    if problemas:
        bloquear("taller-3d bloqueó la escritura:\n- " + "\n- ".join(problemas)
                 + "\nCorregí el archivo y volvé a intentarlo.")


def _comando(entrada: dict) -> str:
    for clave in ("command", "cmd", "script"):
        if isinstance(entrada.get(clave), str):
            return entrada[clave]
    return " ".join(str(v) for v in entrada.values() if isinstance(v, str))


RE_ABRE = re.compile(r"\bopen\(([^)]*)\)")
RE_COPIA_SCRIPT = re.compile(r"(?:shutil\.(?:copy\w*|move)|copyfile|writefilesync|\[io\.file\]::write\w*)\s*\(([^)]*)\)")
RE_WRITE_METODO = re.compile(r"\.write_(?:text|bytes)\s*\(")
ESCRIBEN_PS = {"set-content", "add-content", "out-file", "sc", "ac", "new-item", "ni"}
SWITCHES_PS = {"-force", "-nonewline", "-append", "-whatif", "-confirm", "-passthru", "-noclobber"}


def _escribe_script_en_orca(c: str) -> bool:
    """¿Un script escribe en la carpeta de Orca? Mira a dónde escribe, no qué escribe: armar un config.json que
    nombra esa carpeta no es escribir en ella."""
    for m in RE_ABRE.finditer(c):
        if re.search(r"['\"][wax]", m.group(1)) and CARPETA_ORCA.search(m.group(1)):
            return True
    if any(CARPETA_ORCA.search(m.group(1)) for m in RE_COPIA_SCRIPT.finditer(c)):
        return True
    for m in RE_WRITE_METODO.finditer(c):
        inicio = max(c.rfind(";", 0, m.start()), c.rfind("\n", 0, m.start())) + 1
        if CARPETA_ORCA.search(c[inicio:m.start()]):
            return True
    return False


def _destino_ps(argumentos: list[str]) -> str | None:
    """El archivo que escribe un Set-Content, Add-Content, Out-File o New-Item de PowerShell."""
    for i, a in enumerate(argumentos):
        if a in ("-path", "-literalpath", "-filepath") and i + 1 < len(argumentos):
            return argumentos[i + 1]
    saltar = False
    for a in argumentos:
        if saltar:
            saltar = False
        elif a.startswith("-"):
            saltar = a not in SWITCHES_PS
        else:
            return a
    return None


def escribe_en_orca(comando: str) -> bool:
    """¿El comando escribe, mueve o borra algo en la carpeta de datos de Orca? (leer sí se puede)."""
    c = comando.lower()
    if not CARPETA_ORCA.search(c):
        return False
    # Redirecciones (> y >>, no 2> ni >&) y tee hacia la carpeta
    for m in re.finditer(r"(?<![0-9&>])>{1,2}\s*(\"[^\"]*\"|'[^']*'|[^\s|;&<>]+)", c):
        if CARPETA_ORCA.search(m.group(1)):
            return True
    if _escribe_script_en_orca(c):
        return True
    for tramo in re.split(r"\|\||&&|[|;&\n]", c):
        tokens = [x.strip("\"'") for x in RE_TOKEN.findall(tramo)]
        while tokens and tokens[0] in PREFIJOS:
            tokens = tokens[1:]
        if not tokens:
            continue
        programa = re.split(r"[/\\]", tokens[0])[-1]
        programa = programa[:-4] if programa.endswith(".exe") else programa
        argumentos = [x for x in tokens[1:] if not x.startswith("-")]
        if programa == "tee" and any(CARPETA_ORCA.search(a) for a in argumentos):
            return True
        if programa in COPIAN and argumentos and CARPETA_ORCA.search(argumentos[-1]):
            return True
        if programa in ESCRIBEN_PS:
            destino = _destino_ps(tokens[1:])
            if destino and CARPETA_ORCA.search(destino):
                return True
            continue
        if programa in TOCAN and any(CARPETA_ORCA.search(a) for a in tokens[1:]):
            return True
        en_lugar = any(re.fullmatch(r"-[a-z]*i\S*", x) or x.startswith("--in-place") for x in tokens[1:])
        if programa in ("sed", "perl") and en_lugar and any(CARPETA_ORCA.search(a) for a in argumentos):
            return True
        if programa == "tar" and any(re.fullmatch(r"-?[a-z]*x[a-z]*", x) for x in tokens[1:2]):
            return True
    return False


# --- OrcaSlicer.conf -------------------------------------------------------------------------
# Guarda la IP y el código de acceso de las impresoras en red. No se trae, no se copia ni se lee entero (tampoco la
# carpeta de datos de Orca completa). En la terminal de la PC solo pasan los dos comandos de
# references/impresoras.md (sección 1), exactos salvo la ruta absoluta, que sacan models y presets.machine.
# Un bloqueo que lee el texto del comando no frena todo (nombres armados con variables, búsquedas desde carpetas
# de más arriba, scripts guardados en archivos): es una red de seguridad; la regla está escrita en las skills.
CONF = "orcaslicer.conf"
AVISO_CONF = ("taller-3d: OrcaSlicer.conf guarda la IP y el código de acceso de las impresoras en red: no se trae, no "
              "se copia ni se lee entero, y tampoco la carpeta de datos de Orca completa. Con la terminal de la PC usá "
              "exactamente el comando de references/impresoras.md (skill impresion-3d), con la ruta absoluta: saca "
              "solo models y presets.machine. Si no hay terminal, preguntale al usuario qué impresoras tiene.")
LEER_CONF = {
    "linux": ("python3 -c 'import json,sys; t=\"\".join(l for l in open(sys.argv[1], encoding=\"utf-8-sig\") "
              "if not l.lstrip().startswith(\"#\")); c=json.loads(t); print(json.dumps({\"models\": "
              "c.get(\"models\", []), \"machine\": (c.get(\"presets\") or {}).get(\"machine\")}, ensure_ascii=False))' "
              "\"RUTA\""),
    "windows": ("$c = (Get-Content -Encoding UTF8 \"RUTA\" | Where-Object { $_ -notmatch '^\\s*#' } | Out-String) | "
                "ConvertFrom-Json; @{models = $c.models; machine = $c.presets.machine} | ConvertTo-Json -Depth 5 "
                "-Compress"),
}
# Ruta absoluta sin comillas, $, `, comodines, ; | & < > ni saltos de línea, que termina en OrcaSlicer.conf.
_RUTA_CONF = {
    "linux": r"/[^\"'`$;|&<>*?\[\]{}!\\\n]*/orcaslicer\.conf",
    "windows": r"[a-z]:\\[^\"'`$;|&<>*?\[\]{}!/\n]*\\orcaslicer\.conf",
}


def _permitido(sistema: str) -> re.Pattern:
    antes, despues = LEER_CONF[sistema].lower().split('"ruta"')
    antes = re.escape(antes).replace("python3", "python3?")
    return re.compile(antes + '"' + _RUTA_CONF[sistema] + '"' + re.escape(despues))


PERMITIDOS = [_permitido("linux"), _permitido("windows")]
# Programas que miran sin leer el contenido. Sobre la carpeta de datos de Orca valen solos y sin recursión.
SOLO_MIRAN = {"ls", "dir", "stat", "test", "[", "du", "test-path", "get-item", "gi", "get-childitem", "gci"}
EMPAQUETAN = {"tar", "zip", "7z", "7za", "rar", "cp", "mv", "rsync", "scp", "ditto", "robocopy", "xcopy",
              "copy-item", "cpi", "compress-archive"}
_RE_TRAMO = re.compile(r"\|\||&&|[|;&\n]")
# Una palabra de la terminal: partes entre comillas y sin comillas pegadas ("Orca"'Slicer'.conf es una sola).
_RE_PALABRA = re.compile(r"""(?:"[^"]*"|'[^']*'|[^\s"'])+""")
_RE_CORTE = re.compile(r"[=,()<>|;&`]")
_RE_RECURSIVO = re.compile(r"(^|\s)(-[a-z]*r[a-z]*|--recursive|-recurse|/s)(\s|$)|\$\(|`|-exec")
_RAICES = ("orcaslicer", "com.orcaslicer.orcaslicer", "data_dir")
# Carpeta de datos de Orca: Linux (.config y Flatpak), macOS, Windows (AppData o la que deja el instalador) y portable.
RE_DATOS_ORCA = re.compile(r"(?:^|/)(?:(?:\.config|config|application support|appdata/roaming|[a-z]:/users/[^/]+)"
                           r"/orcaslicer|data_dir)(?:/(.*))?$")


def es_comando_permitido(comando: str) -> bool:
    """¿Es uno de los dos comandos documentados para leer models y presets.machine?"""
    c = re.sub(r"\s+", " ", str(comando).strip().lower())
    return ".." not in c and any(p.fullmatch(c) for p in PERMITIDOS)


def _variantes(texto: str) -> list[str]:
    """El texto sin comillas ni ^, con \\ como separador (Windows) y con \\ como escape (bash)."""
    sin = re.sub(r"[\"'^]", "", texto.lower())
    return [sin.replace("\\", "/"), sin.replace("\\", "")]


def _es_nombre_conf(tramo_final: str, contexto_orca: bool) -> bool:
    """¿El último tramo de una ruta es (o puede ser, con comodines) OrcaSlicer.conf o una copia suya?"""
    t = str(tramo_final).lower().split(":")[0].rstrip(". ")  # flujos NTFS (::$DATA) y puntos finales de Windows
    if t.startswith(CONF) or re.match(r"orcasl~\d", t):     # .bak, .tmp y nombre corto 8.3
        return True
    comodin = any(x in t for x in "*?[")
    return comodin and contexto_orca and any(fnmatch.fnmatchcase(n, t) for n in (CONF, CONF + ".bak"))


def _es_raiz_orca(ruta: str) -> bool:
    """¿La ruta es la carpeta de datos de Orca entera (o un comodín sobre ella), no una subcarpeta?"""
    r = re.sub(r"(/(\*\*?|\.))+$", "", str(ruta).lower().rstrip("/"))
    ultimo = r.rsplit("/", 1)[-1].split(":")[-1]
    if any(x in ultimo for x in "*?["):
        return any(fnmatch.fnmatchcase(n, ultimo) for n in _RAICES)
    return ultimo in _RAICES


def _palabras(tramo: str) -> list[str]:
    """Las palabras de un tramo, sin comillas ni ^, con los espacios que van dentro de la palabra (entre comillas o
    escapados con \\)."""
    texto = tramo.replace("\\ ", "\x00")
    return [re.sub(r"[\"'^]", "", p).replace("\x00", " ") for p in _RE_PALABRA.findall(texto)]


_CD = {"cd", "pushd", "chdir", "set-location", "sl"}


def _puede_ser_raiz(carpeta: str) -> bool:
    """¿Esa carpeta es (o, con comodines, puede ser) la carpeta de datos de Orca?"""
    ultimo = carpeta.rstrip("/").rsplit("/", 1)[-1].split(":")[-1]
    if any(x in ultimo for x in "*?["):
        return any(fnmatch.fnmatchcase(n, ultimo) for n in _RAICES)
    return ultimo in _RAICES


def _comodin_de_conf(final: str) -> bool:
    """¿Un comodín que puede tomar OrcaSlicer.conf (o su .bak)?"""
    t = final.split(":")[0]
    return any(x in t for x in "*?[") and any(fnmatch.fnmatchcase(n, t) for n in (CONF, CONF + ".bak"))


def toca_conf_de_orca(comando: str) -> bool:
    """¿El comando puede leer, copiar o empaquetar OrcaSlicer.conf? Solo pasan los dos comandos documentados.
    Nombrarlo sin ruta (un grep en el código, un mensaje de commit) no cuenta, y un comodín solo cuenta sobre la
    carpeta de datos de Orca (no sobre otra que se llame parecido, como "OrcaSlicer Claude")."""
    if es_comando_permitido(comando):
        return False
    tramos = [x for x in _RE_TRAMO.split(comando.lower()) if x.strip()]
    en_raiz = False                                       # después de un cd a la carpeta de datos de Orca
    for tramo in tramos:
        palabras = _palabras(tramo)
        while palabras and palabras[0] in PREFIJOS:
            palabras = palabras[1:]
        programa = re.split(r"[/\\]", palabras[0])[-1] if palabras else ""
        programa = programa[:-4] if programa.endswith(".exe") else programa
        mira = programa in SOLO_MIRAN
        for n, palabra in enumerate(palabras):
            for variante in {palabra.replace("\\", "/"), palabra.replace("\\", "")}:
                for ruta in (x.strip() for x in _RE_CORTE.split(variante)):
                    if not ruta or (n == 0 and "/" not in ruta.strip("/")):
                        continue                          # el nombre del programa (orcaslicer --help)
                    # Una dirección web (git clone https://github.com/OrcaSlicer/OrcaSlicer) no es la carpeta de
                    # datos; file:// sí puede serlo, así que esa sigue como ruta.
                    # El esquema tiene dos letras o más: C://Users/... es una unidad de Windows, no la web.
                    web = bool(re.match(r"[a-z][a-z0-9+.-]+://", ruta)) and not ruta.startswith("file://")
                    con_carpeta = "/" in ruta or ruta.startswith("~")
                    carpeta, _, final = ruta.rstrip("/").rpartition("/")
                    if not mira and _es_nombre_conf(final, False) and (con_carpeta or en_raiz):
                        return True                       # OrcaSlicer.conf o una copia, con su carpeta
                    if not mira and _comodin_de_conf(final) and (_puede_ser_raiz(carpeta) if carpeta else en_raiz):
                        return True                       # un comodín sobre la carpeta de datos de Orca
                    if not web and _es_raiz_orca(ruta) and (con_carpeta or programa in EMPAQUETAN):
                        if not (mira and len(tramos) == 1 and not _RE_RECURSIVO.search(tramo)):
                            return True                   # la carpeta entera: copiarla, empaquetarla, recorrerla
        if programa in _CD and len(palabras) > 1:
            en_raiz = _puede_ser_raiz(palabras[1].replace("\\", "/"))
    return False


def _textos(valor):
    if isinstance(valor, str):
        yield valor
    elif isinstance(valor, dict):
        for v in valor.values():
            yield from _textos(v)
    elif isinstance(valor, list):
        for v in valor:
            yield from _textos(v)


def no_se_trae(ruta: str) -> bool:
    """OrcaSlicer.conf y sus copias (.bak, .tmp, nombre corto), y todo lo de la carpeta de datos de Orca que no sea
    user/ o system/ (ahí están los perfiles)."""
    r = normalizar(ruta).rstrip("/")
    if not r or r == ".":
        return False
    if _es_nombre_conf(r.rsplit("/", 1)[-1], True):
        return True
    m = RE_DATOS_ORCA.search(r)
    return bool(m) and not re.match(r"(user|system|resources)(/|$)", m.group(1) or "")


def pre_stage(datos: dict) -> None:
    entrada = datos.get("tool_input") or {}
    rutas = [x for clave, v in entrada.items() if clave != "artifact_ids" for x in _textos(v)]
    if any(es_conexion_tienda(r) for r in rutas):
        bloquear(AVISO_TIENDA)
    if any(no_se_trae(r) for r in rutas):
        bloquear(AVISO_CONF)


def pre_read(datos: dict) -> None:
    entrada = datos.get("tool_input") or {}
    for clave in ("file_path", "path", "notebook_path"):
        ruta = entrada.get(clave)
        if isinstance(ruta, str) and es_conexion_tienda(ruta):
            bloquear(AVISO_TIENDA)
        if isinstance(ruta, str) and ruta.strip() and (no_se_trae(ruta) or _es_raiz_orca(normalizar(ruta))):
            bloquear(AVISO_CONF)


def pre_bash(datos: dict) -> None:
    comando = _comando(datos.get("tool_input") or {})
    c = comando.lower()
    if es_conexion_tienda(comando):
        bloquear(AVISO_TIENDA)
    if toca_conf_de_orca(comando):
        bloquear(AVISO_CONF)
    if re.search(HERRAMIENTAS_RED, c) and any(re.search(p, c) for p in PATRONES_IMPRESION):
        bloquear("taller-3d: el plugin nunca arranca impresiones. Mandá el archivo a la impresora y "
                 "arrancala vos desde la pantalla o la app de la impresora.")
    sube = SUBIDA_CURL.search(comando) or any(re.search(p, c) for p in SUBIDA)
    if sube and re.search(ARCHIVOS_3D, c):
        bloquear("taller-3d: no se suben modelos, G-code ni perfiles a internet. Si querés compartir un "
                 "archivo, hacelo vos.")
    if escribe_en_orca(comando):
        bloquear("taller-3d: la carpeta de datos de Orca no se toca desde la terminal. Los perfiles se "
                 "escriben con device_commit_files, que los revisa antes.")


def post_slice(_datos: dict) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                "taller-3d: antes de entregar este G-code, traelo con device_stage_files y corré "
                "revisar_gcode.py (skill impresion-3d). Si sale RECHAZADO, no lo entregues."
            ),
        }
    }, ensure_ascii=False))


def main() -> None:
    modo = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        datos = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if not isinstance(datos, dict):
        sys.exit(0)
    acciones = {"pre-commit": pre_commit, "pre-write": pre_write, "pre-bash": pre_bash, "pre-stage": pre_stage,
                "pre-read": pre_read,
                "post-slice": post_slice}
    accion = acciones.get(modo)
    if accion is None:
        sys.exit(0)
    try:
        accion(datos)
    except SystemExit:
        raise
    except Exception as error:
        # Los archivos de impresión ya fallan cerrado en revisar_archivo; esto es un error fuera de eso.
        print(f"taller-3d (guardia): error interno, no bloqueo: {error}", file=sys.stderr)
        sys.exit(0)
    sys.exit(0)


if __name__ == "__main__":
    main()
