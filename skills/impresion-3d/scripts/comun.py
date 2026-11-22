# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
"""Utilidades comunes de los scripts de taller-3d (solo biblioteca estándar)."""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

VERSION_PLUGIN = "0.1.23"
VERSION_ORCA = "2.5.1"

SCRIPTS = Path(__file__).resolve().parent
SKILL = SCRIPTS.parent
DATOS = SKILL / "datos"
REFERENCIAS = SKILL / "references"
# El catálogo va en partes de menos de 200 KB (límite de archivos del directorio de plugins de Anthropic)
CATALOGO = REFERENCIAS / f"catalogo-orca-{VERSION_ORCA}"

APROBADO, ADVERTENCIA, RECHAZO = "aprobado", "advertencia", "rechazo"
CODIGO_SALIDA = {APROBADO: 0, ADVERTENCIA: 1, RECHAZO: 2}
TITULO = {
    APROBADO: "APROBADO",
    ADVERTENCIA: "CON ADVERTENCIAS",
    RECHAZO: "RECHAZADO",
}


def cargar_json(ruta: Path | str):
    """JSON en UTF-8 (con o sin BOM) o UTF-16 (lo que deja PowerShell al redirigir con >)."""
    datos = Path(ruta).read_bytes()
    if datos[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return json.loads(datos.decode("utf-16"))
    return json.loads(datos.decode("utf-8-sig"))


# Boquilla al final del nombre de un perfil de máquina: "0.4 nozzle", "(0.4 nozzle)", "HF0.4 nozzle", "0.4mm nozzle".
RE_BOQUILLA = re.compile(r"\s*[(\[]?\s*(?:hf\s*)?\d+(?:[.,]\d+)?\s*(?:mm)?\s*nozzle\s*(?:hf)?\s*[)\]]?\s*$", re.I)
RE_NUMERO_BOQUILLA = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:mm)?\s*nozzle", re.I)


def slug(texto, vacio: str = "pieza") -> str:
    """Nombre para carpetas y archivos: minúsculas, sin acentos, palabras unidas con guiones."""
    import unicodedata
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")
    return t[:60].strip("-") or vacio


def plano(texto) -> str:
    """Texto para comparar nombres: sin espacios de más y sin distinguir mayúsculas."""
    return re.sub(r"\s+", " ", str(texto or "")).strip().casefold()


def modelo_de_perfil(nombre) -> str:
    """'Creality Hi 0.4 nozzle' o 'Creality K1 (0.4 nozzle)' → el modelo, sin la boquilla."""
    return RE_BOQUILLA.sub("", re.sub(r"\s+", " ", str(nombre or "")).strip()).strip()


def _numero(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


# Rangos razonables de los límites de una impresora: fuera de esto, la fuente seguramente está mal leída.
LIMITES_RAZONABLES = {"boquilla_max_c": (150, 500), "cama_max_c": (40, 150)}


def problemas_impresora(datos) -> list[str]:
    """Qué falta o está mal en los datos de una impresora. Lista vacía: están completos.

    El plugin no trae impresoras: /impresoras arma estos datos para la impresora que elige el usuario,
    leyendo su perfil de Orca e investigando las fuentes oficiales. Sin estos campos la revisión de
    seguridad no puede controlar la impresora, así que no se aceptan datos incompletos ni inventados.
    """
    if not isinstance(datos, dict):
        return ["no es un objeto JSON"]
    problemas = []
    if not str(datos.get("id") or "").strip():
        problemas.append("falta 'id'")
    if not str(datos.get("nombre") or "").strip():
        problemas.append("falta 'nombre' (marca y modelo, como el printer_model de Orca)")
    area = datos.get("area")
    claves = ("x_min", "x_max", "y_min", "y_max", "z_max")
    if not isinstance(area, dict):
        problemas.append("falta 'area' (x_min, x_max, y_min, y_max y z_max, en mm)")
    elif not all(_numero(area.get(k)) for k in claves):
        problemas.append("'area' tiene que tener x_min, x_max, y_min, y_max y z_max con números")
    elif (area["x_max"] <= area["x_min"] or area["y_max"] <= area["y_min"] or not 0 < area["z_max"] <= 3000
          or area["x_max"] - area["x_min"] > 3000 or area["y_max"] - area["y_min"] > 3000):
        problemas.append("el área no tiene sentido: revisá las medidas")
    limites = datos.get("limites")
    if not isinstance(limites, dict):
        problemas.append("falta 'limites' (boquilla_max_c y cama_max_c, del fabricante)")
    else:
        for clave, (minimo, maximo) in LIMITES_RAZONABLES.items():
            valor = limites.get(clave)
            if not _numero(valor):
                problemas.append(f"falta limites.{clave} (dato oficial del fabricante, en °C)")
            elif not minimo <= valor <= maximo:
                problemas.append(f"limites.{clave}={valor} está fuera de lo razonable ({minimo}-{maximo} °C): "
                                 "revisá la fuente")
    fuentes = datos.get("fuentes")
    if not isinstance(fuentes, list) or not any(isinstance(f, str) and f.startswith(("https://", "http://"))
                                                for f in fuentes):
        problemas.append("falta 'fuentes' con al menos un enlace oficial (de dónde salen los límites)")
    margen = datos.get("margen_mm", 5)
    if not _numero(margen) or not 0 <= margen <= 50:
        problemas.append("'margen_mm' tiene que ser un número entre 0 y 50")
    return problemas


def cargar_impresora(ruta: Path | str) -> dict:
    """Carga los datos de una impresora desde su JSON (taller-3d/impresoras/<id>.json de la carpeta de
    trabajo, traído al espacio de Claude). Rechaza datos incompletos."""
    archivo = Path(str(ruta)).expanduser()
    if archivo.suffix.lower() != ".json" or not archivo.is_file():
        raise SystemExit(
            f"No encuentro los datos de la impresora '{ruta}'. El plugin no trae impresoras cargadas: "
            "se arman con /impresoras para la impresora que elijas (se toma de Orca y se investiga en internet) "
            "y quedan en taller-3d/impresoras/ de la carpeta de trabajo. Pasá la ruta a ese JSON.")
    try:
        datos = cargar_json(archivo)
    except ValueError as error:
        raise SystemExit(f"Los datos de la impresora ({archivo.name}) no son un JSON válido: {error}")
    faltan = problemas_impresora(datos)
    if faltan:
        raise SystemExit(f"Los datos de la impresora ({archivo.name}) están incompletos: {'; '.join(faltan)}. "
                         "Completalos con /impresoras (fuentes oficiales o preguntando): no se inventan límites.")
    return datos


def impresoras_en(carpetas) -> list[dict]:
    """Datos de impresora completos que haya en esas carpetas (los incompletos se ignoran)."""
    encontradas = []
    for carpeta in carpetas:
        carpeta = Path(carpeta)
        if not carpeta.is_dir():
            continue
        for archivo in sorted(carpeta.glob("*.json")):
            try:
                datos = cargar_json(archivo)
            except (OSError, ValueError):
                continue
            if not problemas_impresora(datos):
                encontradas.append(datos)
    return encontradas


def cargar_materiales() -> dict:
    return {k: v for k, v in cargar_json(DATOS / "materiales.json").items() if not k.startswith("_")}


_ALIAS_MATERIAL = [
    (r"PETG[- ]?CF", "PETG-CF"),
    (r"PLA[- ]?CF", "PLA-CF"),
    (r"PET[- ]?G", "PETG"),
    (r"\bPLA\+?", "PLA"),
    (r"\bTPU|\bTPE|FLEX", "TPU"),
    (r"\bABS", "ABS"),
    (r"\bASA", "ASA"),
    (r"\bPC\b|POLICARBONATO|POLYCARBONATE", "PC"),
    (r"\bPA\d*\b|NYLON|NAILON", "PA"),
]


def normalizar_material(texto: str | None) -> str | None:
    """Devuelve la clave de materiales.json que corresponde a un texto libre o a un nombre de perfil."""
    if not texto:
        return None
    t = str(texto).upper().replace('"', " ")
    for patron, clave in _ALIAS_MATERIAL:
        if re.search(patron, t):
            return clave
    return None


_catalogo: dict | None = None


def cargar_catalogo() -> dict:
    """Los 1015 parámetros de Orca, juntando las partes de references/catalogo-orca-<versión>/."""
    global _catalogo
    if _catalogo is None:
        partes = sorted(CATALOGO.glob("parametros-*.json"), key=lambda p: int(p.stem.rsplit("-", 1)[1]))
        if not partes:
            raise FileNotFoundError(f"No encuentro el catálogo de parámetros en {CATALOGO}")
        juntos: dict = {}
        for parte in partes:
            juntos.update(cargar_json(parte)["parametros"])
        _catalogo = juntos
    return _catalogo


def salir(estado: str) -> None:
    sys.exit(CODIGO_SALIDA[estado])


def peor(*estados: str) -> str:
    orden = [APROBADO, ADVERTENCIA, RECHAZO]
    return max(estados, key=orden.index) if estados else APROBADO


def formato_duracion(segundos: float | None) -> str:
    if segundos is None:
        return "desconocido"
    segundos = int(round(segundos))
    h, resto = divmod(segundos, 3600)
    m, s = divmod(resto, 60)
    if h:
        return f"{h} h {m:02d} min"
    if m:
        return f"{m} min {s:02d} s"
    return f"{s} s"


def parse_duracion_orca(texto: str) -> float | None:
    """'1d 2h 3m 4s' -> segundos."""
    total, hallado = 0.0, False
    for valor, unidad in re.findall(r"(\d+(?:\.\d+)?)\s*([dhms])", texto):
        hallado = True
        total += float(valor) * {"d": 86400, "h": 3600, "m": 60, "s": 1}[unidad]
    return total if hallado else None
