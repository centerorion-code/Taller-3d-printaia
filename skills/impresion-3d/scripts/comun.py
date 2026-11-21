# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
"""Utilidades comunes de los scripts de taller-3d (solo biblioteca estándar)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

VERSION_PLUGIN = "0.1.6"
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
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def impresoras_disponibles() -> list[str]:
    return sorted(p.stem for p in (DATOS / "impresoras").glob("*.json"))


def cargar_impresora(id_o_ruta: str = "ender-3-v3-plus") -> dict:
    """Carga los datos de una impresora por id (datos/impresoras/<id>.json) o por ruta."""
    ruta = Path(id_o_ruta).expanduser()
    if ruta.suffix == ".json" and ruta.exists():
        return cargar_json(ruta)
    ruta = DATOS / "impresoras" / f"{id_o_ruta}.json"
    if not ruta.exists():
        raise SystemExit(
            f"No conozco la impresora '{id_o_ruta}'. Disponibles: {', '.join(impresoras_disponibles())}. "
            "También se puede pasar la ruta a un JSON con el mismo formato."
        )
    return cargar_json(ruta)


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
