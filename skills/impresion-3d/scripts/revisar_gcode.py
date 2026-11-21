#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
"""Revisión de seguridad de un G-code antes de entregarlo o imprimirlo.

Revisa:
  - temperaturas de boquilla y cama contra la impresora y el material;
  - movimientos fuera del área de impresión (X, Y, Z);
  - comandos que cambian o dañan la configuración del firmware (M500, SAVE_CONFIG, etc.);
  - variables del slicer sin reemplazar y unidades en pulgadas;
  - que apague los calentadores al terminar;
  - tiempo, filamento y costo estimados.

Uso:
  python3 revisar_gcode.py ARCHIVO.gcode [--impresora taller-3d/impresoras/<id>.json | --buscar <carpeta>]
         [--material PETG] [--json informe.json]
         [--precio-kg 25000] [--precio-kwh 150] [--watts 180] [--moneda ARS]

Código de salida: 0 aprobado, 1 con advertencias, 2 rechazado (no entregar).
"""
from __future__ import annotations

import argparse
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402
from comun import ADVERTENCIA, APROBADO, RECHAZO  # noqa: E402

# Comandos que no deben estar en un archivo de impresión.
PELIGROSOS = {
    "M500": (RECHAZO, "guarda la configuración en la memoria de la impresora"),
    "M502": (RECHAZO, "restablece la configuración de fábrica"),
    "M997": (RECHAZO, "actualiza el firmware"),
    "M303": (RECHAZO, "hace un autoajuste PID (calienta sin imprimir)"),
    "M851": (RECHAZO, "cambia el offset de la sonda Z"),
    "M92": (RECHAZO, "cambia los pasos por mm de los motores"),
    "M906": (RECHAZO, "cambia la corriente de los motores"),
    "M206": (RECHAZO, "cambia el offset de inicio"),
    "M428": (RECHAZO, "fija el offset de inicio en la posición actual"),
    "M302": (RECHAZO, "permite extruir con la boquilla fría"),
    "M665": (RECHAZO, "cambia la geometría de una delta"),
    "M666": (RECHAZO, "cambia los finales de carrera de una delta"),
    "SAVE_CONFIG": (RECHAZO, "guarda la configuración de Klipper y lo reinicia"),
    "FIRMWARE_RESTART": (RECHAZO, "reinicia el firmware"),
    "RESTART": (RECHAZO, "reinicia Klipper"),
    "SET_KINEMATIC_POSITION": (RECHAZO, "hace creer a la impresora que está en otra posición"),
    "FORCE_MOVE": (RECHAZO, "mueve motores sin respetar los límites"),
    "SET_TMC_CURRENT": (RECHAZO, "cambia la corriente de los motores"),
    "PROBE_CALIBRATE": (RECHAZO, "inicia una calibración de sonda interactiva"),
    "Z_OFFSET_APPLY_PROBE": (RECHAZO, "guarda un nuevo offset Z"),
    "Z_OFFSET_APPLY_ENDSTOP": (RECHAZO, "guarda un nuevo offset Z"),
    "RUN_SHELL_COMMAND": (RECHAZO, "ejecuta comandos en la computadora de la impresora"),
    "M149": (RECHAZO, "cambia las unidades de temperatura (una S400 podría leerse en otra escala)"),
    "M301": (RECHAZO, "cambia el PID del hotend (puede pasarse de temperatura)"),
    "M304": (RECHAZO, "cambia el PID de la cama (puede pasarse de temperatura)"),
    "M81": (ADVERTENCIA, "apaga la fuente de la impresora"),
    "M999": (ADVERTENCIA, "reinicia la impresora después de un error"),
    "M112": (ADVERTENCIA, "parada de emergencia dentro del archivo"),
    "SET_GCODE_OFFSET": (ADVERTENCIA, "cambia el offset Z durante la impresión"),
    "SET_STEPPER_ENABLE": (ADVERTENCIA, "habilita o deshabilita motores"),
    "BED_MESH_CALIBRATE": (ADVERTENCIA, "vuelve a medir la cama"),
}

# Comandos habituales de Orca/Klipper/Marlin que no generan aviso.
SEGUROS = {
    "G0", "G1", "G2", "G3", "G4", "G10", "G11", "G17", "G21", "G28", "G29", "G90", "G91", "G92",
    "M17", "M18", "M25", "M73", "M82", "M83", "M84", "M104", "M105", "M106", "M107", "M109", "M117",
    "M125", "M420", "M593",
    "M118", "M140", "M141", "M190", "M191", "M201", "M203", "M204", "M205", "M211", "M220",
    "M221", "M400", "M486", "M600", "M601", "M900", "M1002",
    "START_PRINT", "PRINT_START", "END_PRINT", "PRINT_END", "PAUSE", "RESUME", "CANCEL_PRINT",
    "SET_PRESSURE_ADVANCE", "SET_VELOCITY_LIMIT", "SET_RETRACTION", "SET_FAN_SPEED",
    "SET_HEATER_TEMPERATURE", "TEMPERATURE_WAIT", "SET_PRINT_STATS_INFO", "BED_MESH_PROFILE",
    "EXCLUDE_OBJECT_DEFINE", "EXCLUDE_OBJECT_START", "EXCLUDE_OBJECT_END", "EXCLUDE_OBJECT",
    "TIMELAPSE_TAKE_FRAME", "M300", "M290",
}

CLAVES_BOQUILLA = ("EXTRUDER_TEMP", "EXTRUDER", "HOTEND_TEMP", "HOTEND", "NOZZLE_TEMP", "NOZZLE",
                   "EXTRUDER_TEMPERATURE")
CLAVES_CAMA = ("BED_TEMP", "BED", "BED_TEMPERATURE", "HEATBED")

RE_PARAM_GM = re.compile(r"([A-Z])\s*([-+]?(?:\d+\.?\d*|\.\d+))")
RE_PARAM_KV = re.compile(r"([A-Z_][A-Z0-9_]*)=(\S+)")
RE_VARIABLE = re.compile(r"\[[a-z_][a-z0-9_]*\]|\{[^}]*\}")
RE_CONFIG = re.compile(r"^;\s*([^=:;]+?)\s*[=:]\s*(.*)$")
RE_NUMERO_LINEA = re.compile(r"^N\d+\s*", re.I)
RE_SUMA = re.compile(r"\s*\*\d+\s*$")
RE_CMD_GM = re.compile(r"^([GMT]\d+(?:\.\d+)?)(?!_)\s*(.*)$", re.I)
MAX_EJEMPLOS = 5
# En un G-code de perfil, una temperatura escrita como fórmula de Orca que suma, multiplica o divide
# (o trae un número grande adentro) no se puede controlar hasta laminar.
RE_FORMULA_SUBE = re.compile(r"[+*/]|-\s*-|-\s*\(\s*-")
RE_NUMERO_SUELTO = re.compile(r"(?<![\w.])\d+(?:\.\d+)?")
# Instrucciones del lenguaje de plantillas de Orca ({if ...}, {else}, {endif}): en un bloque de
# perfil se sacan y se revisa el G-code que queda en la línea.
RE_PLANTILLA = re.compile(r"\{\s*(?:if|elsif|else|endif)\b[^{}]*\}", re.I)
RE_COMANDO_VALIDO = re.compile(r"[A-Z_][A-Z0-9_.]*")


IMPRESORA_GENERICA = {
    "id": "generica",
    "area": {"x_min": -10000, "x_max": 10000, "y_min": -10000, "y_max": 10000, "z_max": 10000},
    "margen_mm": 0,
    "limites": {"boquilla_max_c": 300, "cama_max_c": 120},
}


def _textos_de(datos: dict, *claves) -> list[str]:
    return [datos[k] for k in claves if isinstance(datos.get(k), str) and datos[k].strip()]


def elegir_impresora(modelo: str, perfil: str, candidatas) -> dict | None:
    """Entre los datos de impresora del usuario, la que corresponde a ese printer_model y ese nombre de perfil.

    1. El perfil de máquina exacto.
    2. Si se sabe el modelo (printer_model del G-code), solo los datos de ese modelo: nunca los de uno parecido
       (A1 y A1 mini, MK3 y MK3.5, Neptune 4 y Neptune 4 Pro).
    3. Sin modelo, el patrón tiene que estar al final del nombre del perfil (@Modelo, @Modelo-all,
       Modelo 0.4 nozzle); gana el más largo.
    Si dos datos empatan, ninguno: mejor límites genéricos (con aviso) que los de otra impresora."""
    candidatas = [c for c in candidatas or [] if isinstance(c, dict)]
    perfil_p, modelo_p = comun.plano(perfil), comun.plano(modelo)
    if perfil_p:
        exactas = [d for d in candidatas if perfil_p in {comun.plano(x) for x in d.get("perfiles_maquina") or []
                                                         if isinstance(x, str)}]
        if exactas:
            return exactas[0] if len(exactas) == 1 else None
    if modelo_p:
        iguales = [d for d in candidatas if modelo_p in {comun.plano(x) for x in _textos_de(d, "nombre")}]
        if not iguales:
            iguales = [d for d in candidatas
                       if any(modelo_p.endswith(" " + comun.plano(x)) for x in _textos_de(d, "nombre", "patron_perfiles"))]
        return iguales[0] if len(iguales) == 1 else None
    con_patron = [d for d in candidatas if _textos_de(d, "patron_perfiles") and termina_en(perfil, d["patron_perfiles"])]
    if not con_patron:
        return None
    largo = max(len(comun.plano(d["patron_perfiles"])) for d in con_patron)
    mejores = [d for d in con_patron if len(comun.plano(d["patron_perfiles"])) == largo]
    return mejores[0] if len(mejores) == 1 else None


def contiene_palabra(texto: str, patron: str) -> bool:
    """El patrón aparece entero, sin distinguir mayúsculas ("Hi" está en "@Creality Hi-all", no en "High Flow")."""
    patron = comun.plano(patron)
    return bool(patron) and bool(re.search(r"(?<!\w)" + re.escape(patron) + r"(?!\w)", comun.plano(texto)))


# Lo que puede seguir al modelo al final del nombre de un perfil: -all y la boquilla.
RE_FIN_PERFIL = r"(?:-all)?(?:\s*[(\[]?\s*(?:hf\s*)?\d+(?:[.,]\d+)?\s*(?:mm)?\s*(?:nozzle)?\s*(?:hf)?\s*[)\]]?)?\s*$"


def termina_en(nombre: str, patron: str) -> bool:
    """¿El nombre del perfil termina con el patrón de la impresora? Así 'A1' no toma 'A1 mini' ni 'MK3' toma
    'MK3.5'."""
    patron = comun.plano(patron)
    return bool(patron) and bool(re.search(r"(?<!\w)" + re.escape(patron) + RE_FIN_PERFIL, comun.plano(nombre)))


def detectar_impresora(ruta: Path | None, texto: str | None = None, candidatas=None) -> dict:
    """Elige, entre los datos de impresora del usuario (candidatas), la del G-code según su printer_model y
    printer_settings_id. El plugin no trae impresoras: si no se pasan datos o ninguno coincide, devuelve una
    genérica que solo controla temperaturas absolutas, comandos peligrosos y variables (no el área)."""
    modelo = perfil = ""
    fuente = io.StringIO(texto) if texto is not None else open(ruta, encoding="utf-8", errors="replace")
    with fuente as f:
        for linea in f:
            if linea.startswith("; printer_model ="):
                modelo = linea.split("=", 1)[1].strip().strip('"')
            elif linea.startswith("; printer_settings_id ="):
                perfil = linea.split("=", 1)[1].strip().strip('"')
    return elegir_impresora(modelo, perfil, candidatas) or IMPRESORA_GENERICA


class Revision:
    def __init__(self):
        self.hallazgos: list[dict] = []

    def agregar(self, gravedad: str, mensaje: str, linea: int | None = None):
        self.hallazgos.append({"gravedad": gravedad, "mensaje": mensaje, "linea": linea})

    @property
    def estado(self) -> str:
        return comun.peor(*(h["gravedad"] for h in self.hallazgos)) if self.hallazgos else APROBADO


def _formula(rev: "Revision", cmd: str, resto: str, tope: float, n: int) -> None:
    if "{" not in resto and "[" not in resto:
        return
    numeros = [float(x) for x in RE_NUMERO_SUELTO.findall(resto)]
    if RE_FORMULA_SUBE.search(resto) or any(x > tope for x in numeros):
        rev.agregar(ADVERTENCIA, f"{cmd} usa una temperatura calculada ({resto.strip()[:80]}): la controlo en el "
                    "G-code laminado.", n)


def partir(texto: str) -> tuple[str, str]:
    """Separa el comando de sus parámetros. Acepta número de línea (N123), suma de control (*45)
    y comandos pegados a sus parámetros (M104S220, G1X10Y10), como los acepta el firmware."""
    t = RE_SUMA.sub("", RE_NUMERO_LINEA.sub("", texto, count=1)).strip()
    m = RE_CMD_GM.match(t)
    if m:
        return m.group(1).upper(), m.group(2).strip()
    partes = t.split(None, 1)
    return (partes[0].upper() if partes else ""), (partes[1] if len(partes) > 1 else "")


def _num(texto):
    try:
        return float(texto)
    except (TypeError, ValueError):
        return None


def _area_desde_config(texto: str):
    try:
        puntos = [tuple(float(v) for v in p.split("x")) for p in texto.split(",")]
        xs, ys = [p[0] for p in puntos], [p[1] for p in puntos]
        return min(xs), max(xs), min(ys), max(ys)
    except (ValueError, IndexError):
        return None


def revisar(ruta: Path | None, impresora: dict, material: str | None = None, costos: dict | None = None,
            cama_esperada: float | None = None, texto: str | None = None, fragmento: bool = False) -> dict:
    """Revisa un G-code. Con texto= revisa ese texto en lugar del archivo; con fragmento=True (G-code
    de inicio o de fin de un perfil) no exige extrusión ni apagado y acepta variables de Orca."""
    rev = Revision()
    if impresora.get("id") == IMPRESORA_GENERICA["id"] and not fragmento:
        rev.agregar(ADVERTENCIA, "No reconocí la impresora del G-code entre tus datos (o coinciden varias): controlé "
                    "las temperaturas con límites genéricos y no revisé el área de impresión.")
    area = impresora["area"]
    margen = float(impresora.get("margen_mm", 5))
    lim = impresora["limites"]
    materiales = comun.cargar_materiales()

    cfg: dict[str, str] = {}
    pos = {"X": None, "Y": None, "Z": None}
    absoluto = True
    e_relativo = None
    e_abs_ultimo = 0.0
    fuera = {"rechazo": [], "advertencia": []}
    z_bajo: list[tuple[float, int]] = []  # Z apenas negativa dentro de un bloque de perfil
    rango_ext = {"X": [None, None], "Y": [None, None]}
    z_max = None
    extrusiones = 0
    temp_boquilla: list[tuple[float, int]] = []
    temp_cama: list[tuple[float, int]] = []
    apagado_boquilla = apagado_cama = 0  # línea del último apagado de cada calentador
    linea_ultima_extrusion = 0
    linea_macro_fin = 0
    linea_primer_calentado = None
    linea_primera_extrusion = None
    ventilador_max = 0.0
    desconocidos: Counter = Counter()
    timelapse_creality = 0
    peligrosos: dict[str, list[int]] = {}
    variables: list[int] = []
    capas = 0

    fuente = io.StringIO(texto) if texto is not None else open(ruta, encoding="utf-8", errors="replace")
    with fuente as f:
        for n, cruda in enumerate(f, 1):
            s = cruda.strip()
            if not s:
                continue
            if s.startswith(";"):
                if s.startswith(";LAYER_CHANGE"):
                    capas += 1
                m = RE_CONFIG.match(s)
                if m:
                    cfg[m.group(1).strip()] = m.group(2).strip()
                continue
            linea_cmd = s.split(";", 1)[0].strip()
            if fragmento:
                linea_cmd = RE_PLANTILLA.sub(" ", linea_cmd).strip()
            if not linea_cmd:
                continue
            cmd, resto = partir(linea_cmd)
            if not cmd:
                continue
            if cmd == "M5001":
                # Timelapse de Creality (Hi, SPARKX i7): va adelante de los movimientos y pausas para la foto
                # de cada capa ("M5001 G1 X267 Y110"). Se revisa el comando de atrás como cualquier otro.
                timelapse_creality += 1
                cmd, resto = partir(resto) if RE_CMD_GM.match(resto.strip()) else ("", "")
                if not cmd:
                    continue  # "M5001 P15": dispara la foto
            if fragmento and (re.fullmatch(r"T[\[{].*", cmd) or not RE_COMANDO_VALIDO.fullmatch(cmd)):
                continue  # cambio de herramienta con variable, o restos de la plantilla

            if RE_VARIABLE.search(linea_cmd) and not cmd.startswith("EXCLUDE_OBJECT"):
                variables.append(n)

            if cmd in PELIGROSOS:
                peligrosos.setdefault(cmd, []).append(n)
            elif cmd not in SEGUROS and not re.fullmatch(r"T\d+", cmd):
                desconocidos[cmd] += 1

            if cmd in ("G0", "G1", "G2", "G3"):
                p = {k: float(v) for k, v in RE_PARAM_GM.findall(resto.upper())}
                for eje in ("X", "Y", "Z"):
                    if eje not in p:
                        continue
                    if absoluto:
                        pos[eje] = p[eje]
                    elif pos[eje] is not None:
                        pos[eje] += p[eje]
                for eje in ("X", "Y"):
                    v = pos[eje]
                    if eje in p and v is not None:
                        lo, hi = area[f"{eje.lower()}_min"], area[f"{eje.lower()}_max"]
                        if v < lo - margen or v > hi + margen:
                            fuera["rechazo"].append((eje, v, n))
                        elif v < lo or v > hi:
                            fuera["advertencia"].append((eje, v, n))
                if "Z" in p and pos["Z"] is not None:
                    z = pos["Z"]
                    z_max = z if z_max is None else max(z_max, z)
                    if fragmento and -1.0 <= z < -0.05:
                        z_bajo.append((z, n))
                    elif z < -0.05 or z > area["z_max"]:
                        fuera["rechazo"].append(("Z", z, n))
                if "E" in p:
                    e = p["E"]
                    extruye = e > 0 if e_relativo in (True, None) else e > e_abs_ultimo
                    if e_relativo is False:
                        e_abs_ultimo = e
                    if extruye:
                        extrusiones += 1
                        linea_ultima_extrusion = n
                        if linea_primera_extrusion is None:
                            linea_primera_extrusion = n
                        for eje in ("X", "Y"):
                            v = pos[eje]
                            if v is not None:
                                r = rango_ext[eje]
                                r[0] = v if r[0] is None else min(r[0], v)
                                r[1] = v if r[1] is None else max(r[1], v)
            elif cmd == "G90":
                absoluto = True
            elif cmd == "G91":
                absoluto = False
            elif cmd == "M82":
                e_relativo = False
            elif cmd == "M83":
                e_relativo = True
            elif cmd == "G92":
                p = {k: float(v) for k, v in RE_PARAM_GM.findall(resto.upper())}
                if "E" in p:
                    e_abs_ultimo = p["E"]
                ejes = [e for e in ("X", "Y", "Z") if e in p]
                for eje in ejes:
                    pos[eje] = p[eje]
                if "Z" in ejes:
                    rev.agregar(RECHAZO, f"G92 Z{p['Z']:g} cambia dónde cree la impresora que está Z: un movimiento "
                                "después puede chocar la boquilla contra la cama.", n)
                elif ejes:
                    rev.agregar(ADVERTENCIA, f"G92 redefine la posición de {', '.join(ejes)}.", n)
            elif cmd == "G28":
                ejes = [e for e in ("X", "Y", "Z") if e in resto.upper()] or ["X", "Y", "Z"]
                for eje in ejes:
                    pos[eje] = None
            elif cmd == "G20":
                rev.agregar(RECHAZO, "Usa pulgadas (G20): todas las medidas saldrían mal.", n)
            elif cmd in ("M104", "M109", "M140", "M190"):
                # Toma el valor más alto de S y R (y B, la máxima de autotemp en Marlin): si una línea
                # repite la letra, ningún firmware la va a leer más baja que eso.
                letras = "SRB" if cmd in ("M104", "M109") else "SR"
                valores = [float(v) for k, v in RE_PARAM_GM.findall(resto.upper()) if k in letras]
                valor = max(valores) if valores else None
                if fragmento:
                    _formula(rev, cmd, resto, lim["boquilla_max_c" if cmd in ("M104", "M109") else "cama_max_c"], n)
                if valor is not None:
                    if cmd in ("M104", "M109"):
                        temp_boquilla.append((valor, n))
                        if valor == 0:
                            apagado_boquilla = n
                    else:
                        temp_cama.append((valor, n))
                        if valor == 0:
                            apagado_cama = n
                    if valor > 0 and linea_primer_calentado is None:
                        linea_primer_calentado = n
            elif cmd in ("SET_HEATER_TEMPERATURE", "START_PRINT", "PRINT_START"):
                kv = dict(RE_PARAM_KV.findall(resto.upper()))
                if cmd == "SET_HEATER_TEMPERATURE":
                    if fragmento:
                        _formula(rev, cmd, resto, lim["cama_max_c" if "BED" in kv.get("HEATER", "")
                                                      else "boquilla_max_c"], n)
                    valor = _num(kv.get("TARGET"))
                    calentador = kv.get("HEATER", "")
                    if valor is not None:
                        if "BED" in calentador:
                            temp_cama.append((valor, n))
                            if valor == 0:
                                apagado_cama = n
                        elif "EXTRUDER" in calentador:
                            temp_boquilla.append((valor, n))
                            if valor == 0:
                                apagado_boquilla = n
                else:
                    for clave in CLAVES_BOQUILLA:
                        v = _num(kv.get(clave))
                        if v is not None:
                            temp_boquilla.append((v, n))
                            break
                    for clave in CLAVES_CAMA:
                        v = _num(kv.get(clave))
                        if v is not None:
                            temp_cama.append((v, n))
                            break
                    if linea_primer_calentado is None:
                        linea_primer_calentado = n
            elif cmd in ("END_PRINT", "PRINT_END"):
                linea_macro_fin = n
            elif cmd == "M106":
                p = {k: float(v) for k, v in RE_PARAM_GM.findall(resto.upper())}
                s_val = p.get("S")
                if s_val is not None:
                    ventilador_max = max(ventilador_max, s_val)
                    if s_val > 255:
                        rev.agregar(ADVERTENCIA, f"M106 S{s_val:g}: valor de ventilador fuera de rango (0-255).", n)
            elif cmd == "M221":
                p = {k: float(v) for k, v in RE_PARAM_GM.findall(resto.upper())}
                caudal = p.get("S")
                if caudal is not None and caudal > 200:
                    rev.agregar(RECHAZO, f"M221 S{caudal:g}: caudal al {caudal:g} %, puede trabar el extrusor y "
                                "desbordar la boquilla.", n)
                elif caudal is not None and caudal > 120:
                    rev.agregar(ADVERTENCIA, f"M221 S{caudal:g}: caudal al {caudal:g} %.", n)
            elif cmd == "M211":
                p = {k: float(v) for k, v in RE_PARAM_GM.findall(resto.upper())}
                if p.get("S") == 0:
                    rev.agregar(RECHAZO, "M211 S0 desactiva los límites de software de los ejes.", n)

    # Material
    material_clave = comun.normalizar_material(material) or comun.normalizar_material(
        cfg.get("filament_type")) or comun.normalizar_material(cfg.get("filament_settings_id"))
    datos_mat = materiales.get(material_clave) if material_clave else None
    if not material_clave and not fragmento:
        rev.agregar(ADVERTENCIA, "No pude identificar el material: reviso solo los límites de la impresora.")

    # Temperaturas
    def revisar_temps(lista, tipo, maximo_impresora):
        nombre = "boquilla" if tipo == "boquilla" else "cama"
        for valor, n in lista:
            if valor <= 0:
                continue
            if valor > maximo_impresora:
                rev.agregar(RECHAZO, f"Temperatura de {nombre} {valor:g} °C: supera el máximo de la impresora "
                            f"({maximo_impresora:g} °C).", n)
            elif datos_mat and valor > datos_mat[f"{tipo}_tope"]:
                rev.agregar(RECHAZO, f"Temperatura de {nombre} {valor:g} °C: supera el tope para {material_clave} "
                            f"({datos_mat[f'{tipo}_tope']} °C).", n)
            elif datos_mat and valor > datos_mat[tipo][1]:
                rev.agregar(ADVERTENCIA, f"Temperatura de {nombre} {valor:g} °C: por encima del rango recomendado "
                            f"para {material_clave} ({datos_mat[tipo][0]}-{datos_mat[tipo][1]} °C).", n)
            elif datos_mat and valor < datos_mat[tipo][0]:
                rev.agregar(ADVERTENCIA, f"Temperatura de {nombre} {valor:g} °C: por debajo del rango recomendado "
                            f"para {material_clave} ({datos_mat[tipo][0]}-{datos_mat[tipo][1]} °C).", n)

    revisar_temps(temp_boquilla, "boquilla", float(lim["boquilla_max_c"]))
    revisar_temps(temp_cama, "cama", float(lim["cama_max_c"]))
    primera_cama = next((v for v, _ in temp_cama if v > 0), None)
    if cama_esperada is not None and primera_cama is not None and abs(primera_cama - cama_esperada) > 0.5:
        rev.agregar(ADVERTENCIA, f"La cama arranca a {primera_cama:g} °C y se esperaba {cama_esperada:g} °C: revisar el "
                    "tipo de cama (por línea de comandos Orca usa cool_plate_temp).")

    # Movimientos
    for gravedad in (RECHAZO, ADVERTENCIA):
        casos = fuera[gravedad]
        if casos:
            ejemplos = "; ".join(f"{eje}={v:.2f} (línea {n})" for eje, v, n in casos[:MAX_EJEMPLOS])
            extra = "" if gravedad == RECHAZO else f" (dentro del margen de {margen:g} mm)"
            rev.agregar(gravedad, f"{len(casos)} movimiento(s) fuera del área de impresión{extra}: {ejemplos}.",
                        casos[0][2])

    if z_bajo:
        z, n_z = min(z_bajo)
        rev.agregar(ADVERTENCIA, f"El bloque baja la boquilla hasta Z={z:.2f}: solo es seguro si la impresora tiene un "
                    "offset de Z que lo compense.", n_z)

    area_cfg = _area_desde_config(cfg.get("printable_area", "")) if cfg.get("printable_area") else None
    if area_cfg and (area_cfg[1] > area["x_max"] + 0.5 or area_cfg[3] > area["y_max"] + 0.5):
        rev.agregar(ADVERTENCIA, "El perfil de máquina declara un área más grande que la de esta impresora.")

    # Comandos
    for cmd, lineas in peligrosos.items():
        gravedad, explicacion = PELIGROSOS[cmd]
        rev.agregar(gravedad, f"{cmd} {explicacion} ({len(lineas)} vez/veces).", lineas[0])
    if timelapse_creality and not fragmento:
        rev.agregar(APROBADO, f"M5001 ×{timelapse_creality}: timelapse de Creality (Hi, SPARKX i7). Va adelante de "
                    "los movimientos y pausas para sacar la foto de cada capa; los revisé como al resto.")
    if desconocidos:
        lista = ", ".join(f"{c} ×{k}" for c, k in desconocidos.most_common(10))
        rev.agregar(ADVERTENCIA, f"Comandos que no conozco (revisalos): {lista}.")
    if variables and not fragmento:
        rev.agregar(RECHAZO, f"Hay variables del slicer sin reemplazar ({len(variables)} líneas).", variables[0])

    if not fragmento:
        # Extrusión y calentado
        if extrusiones == 0:
            rev.agregar(RECHAZO, "El archivo no extruye material: no es un G-code de impresión válido.")
        elif linea_primer_calentado is None or (linea_primera_extrusion
                                                 and linea_primer_calentado > linea_primera_extrusion):
            rev.agregar(ADVERTENCIA, "Extruye antes de fijar la temperatura de la boquilla.", linea_primera_extrusion)

        # Final
        apaga = bool(linea_macro_fin and linea_macro_fin >= linea_ultima_extrusion) or (
            apagado_boquilla > linea_ultima_extrusion and apagado_cama > linea_ultima_extrusion)
        if extrusiones and not apaga:
            rev.agregar(ADVERTENCIA, "No encontré que apague los calentadores al terminar (END_PRINT o M104 S0 + "
                        "M140 S0).")

    # Estimaciones
    segundos = comun.parse_duracion_orca(cfg.get("estimated printing time (normal mode)", ""))
    gramos = _num(cfg.get("total filament used [g]") or cfg.get("filament used [g]"))
    capas_cfg = _num(cfg.get("total layers count") or cfg.get("total layer number"))
    costo = None
    if costos and gramos is not None:
        moneda = costos.get("moneda") or ""
        costo = {"moneda": moneda}
        if costos.get("precio_kg"):
            costo["material"] = round(gramos / 1000 * float(costos["precio_kg"]), 2)
        if costos.get("precio_kwh") and costos.get("watts") and segundos:
            costo["energia"] = round(segundos / 3600 * float(costos["watts"]) / 1000 * float(costos["precio_kwh"]), 2)
        costo["total"] = round(costo.get("material", 0) + costo.get("energia", 0), 2)

    def maximo(lista):
        vals = [v for v, _ in lista]
        return max(vals) if vals else None

    return {
        "estado": rev.estado,
        "archivo": str(ruta) if ruta is not None else None,
        "impresora": impresora.get("id"),
        "material": material_clave,
        "perfiles": {
            "maquina": cfg.get("printer_settings_id", "").strip('"'),
            "proceso": cfg.get("print_settings_id", "").strip('"'),
            "filamento": cfg.get("filament_settings_id", "").strip('"'),
            "cama": cfg.get("curr_bed_type"),
            "altura_capa": _num(cfg.get("layer_height")),
        },
        "temperaturas": {
            "cama_primera_capa": primera_cama,
            "boquilla_max": maximo(temp_boquilla),
            "cama_max": maximo(temp_cama),
            "rango_recomendado": {
                "boquilla": datos_mat["boquilla"] if datos_mat else None,
                "cama": datos_mat["cama"] if datos_mat else None,
            },
        },
        "movimientos": {
            "x_extrusion": rango_ext["X"],
            "y_extrusion": rango_ext["Y"],
            "z_max": z_max,
            "fuera_de_area": len(fuera["rechazo"]),
            "en_margen": len(fuera["advertencia"]),
        },
        "ventilador_max_pct": round(ventilador_max / 255 * 100) if ventilador_max else 0,
        "estimaciones": {
            "segundos": segundos,
            "duracion": comun.formato_duracion(segundos),
            "gramos": gramos,
            "capas": int(capas_cfg) if capas_cfg else capas,
        },
        "costo": costo,
        "hallazgos": rev.hallazgos,
    }


def informe_texto(r: dict) -> str:
    est = r["estimaciones"]
    t = r["temperaturas"]
    mov = r["movimientos"]
    lineas = [
        f"RESULTADO: {comun.TITULO[r['estado']]}",
        f"Archivo: {Path(r['archivo']).name}",
        f"Impresora: {r['impresora']} | Material: {r['material'] or 'desconocido'}",
        f"Perfiles: {r['perfiles']['maquina']} / {r['perfiles']['proceso']} / {r['perfiles']['filamento']}"
        + (f" | Tipo de cama en Orca: {r['perfiles']['cama']}" if r["perfiles"].get("cama") else ""),
        f"Temperaturas máximas: boquilla {t['boquilla_max']} °C, cama {t['cama_max']} °C "
        f"(primera capa de cama: {t.get('cama_primera_capa')} °C)",
        f"Ventilador máximo: {r['ventilador_max_pct']} %",
    ]
    if mov["x_extrusion"][0] is not None:
        lineas.append(
            f"Zona impresa: X {mov['x_extrusion'][0]:.1f}-{mov['x_extrusion'][1]:.1f}, "
            f"Y {mov['y_extrusion'][0]:.1f}-{mov['y_extrusion'][1]:.1f}, Z máx {mov['z_max']:.2f} mm")
    lineas.append(f"Tiempo: {est['duracion']} | Filamento: {est['gramos']} g | Capas: {est['capas']}")
    if r.get("costo"):
        c = r["costo"]
        partes = [f"material {c['material']}" if "material" in c else None,
                  f"luz {c['energia']}" if "energia" in c else None]
        partes = [p for p in partes if p]
        lineas.append(f"Costo estimado: {c['total']} {c['moneda']} ({', '.join(partes)})")
    if r["hallazgos"]:
        lineas.append("Hallazgos:")
        etiqueta = {RECHAZO: "[RECHAZO]", ADVERTENCIA: "[ADVERTENCIA]", APROBADO: "[OK]"}
        for h in sorted(r["hallazgos"], key=lambda h: h["gravedad"] != RECHAZO):
            lin = f" (línea {h['linea']})" if h.get("linea") else ""
            lineas.append(f"  {etiqueta[h['gravedad']]} {h['mensaje']}{lin}")
    else:
        lineas.append("Sin hallazgos: temperaturas, movimientos y comandos dentro de lo esperado.")
    return "\n".join(lineas)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Revisión de seguridad de un G-code.")
    ap.add_argument("gcode", type=Path)
    ap.add_argument("--impresora", default="auto",
                    help="JSON con los datos de la impresora (taller-3d/impresoras/<id>.json); 'auto' la busca "
                         "en --buscar según el G-code o usa límites genéricos")
    ap.add_argument("--buscar", type=Path, action="append", default=[],
                    help="carpeta con datos de impresoras del usuario, para --impresora auto")
    ap.add_argument("--material", help="PLA, PETG, TPU, ABS, ASA... (si no, lo toma del G-code)")
    ap.add_argument("--json", type=Path, help="guardar el informe en JSON")
    ap.add_argument("--precio-kg", type=float)
    ap.add_argument("--precio-kwh", type=float)
    ap.add_argument("--watts", type=float, default=None)
    ap.add_argument("--moneda", default="ARS")
    ap.add_argument("--cama-primera-capa", type=float, help="temperatura de cama esperada en la primera capa")
    a = ap.parse_args(argv)
    if not a.gcode.exists():
        raise SystemExit(f"No existe {a.gcode}")
    costos = None
    if a.precio_kg or a.precio_kwh:
        costos = {"precio_kg": a.precio_kg, "precio_kwh": a.precio_kwh, "watts": a.watts, "moneda": a.moneda}
    if a.impresora == "auto":
        impresora = detectar_impresora(a.gcode, candidatas=comun.impresoras_en(a.buscar))
    else:
        impresora = comun.cargar_impresora(a.impresora)
    r = revisar(a.gcode, impresora, a.material, costos, a.cama_primera_capa)
    print(informe_texto(r))
    if a.json:
        a.json.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    comun.salir(r["estado"])


if __name__ == "__main__":
    main()
