#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
"""Crear, validar y comparar perfiles de usuario de OrcaSlicer 2.5.1.

Cada clave se valida contra el catálogo de parámetros de Orca (nombre, tipo de perfil,
valores posibles y rangos) y las temperaturas contra la impresora y el material.
Si hay un rechazo, no se escribe nada.

Uso:
  # Crear (o rehacer) un perfil de proceso a partir de uno de usuario + cambios
  python3 perfil_orca.py crear --tipo proceso --nombre "AUTO proceso @Ender-3 V3 Plus" \\
      --hereda "0.20mm Standard @Creality Ender-3 V3 Plus" \\
      --base "PETG Eficiente 0.20 @Ender-3 V3 Plus.json" \\
      --set wall_loops=5 --set sparse_infill_density=40% \\
      --anterior "AUTO proceso @Ender-3 V3 Plus.json" --salida /mnt/user-data/outputs/taller-3d/perfiles

  # Filamento de trabajo con las temperaturas de la cama real (Orca por línea de comandos usa Cool Plate)
  python3 perfil_orca.py crear --tipo filamento --nombre "AUTO filamento @Ender-3 V3 Plus" \\
      --hereda "Generic PETG @Ender-3 V3 Plus-all" --base "GST3D PETG @Ender-3 V3 Plus.json" \\
      --cama "Textured PEI Plate" --salida /mnt/user-data/outputs/taller-3d/perfiles

  # Validar un perfil existente
  python3 perfil_orca.py validar archivo.json [--tipo filamento] [--material PETG]

  # Ver diferencias entre dos perfiles
  python3 perfil_orca.py diff viejo.json nuevo.json

Código de salida: 0 aprobado, 1 con advertencias, 2 rechazado.
"""
from __future__ import annotations

import argparse
import difflib
import json
import math
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402
import revisar_gcode  # noqa: E402
from comun import ADVERTENCIA, APROBADO, RECHAZO  # noqa: E402

TIPOS = {
    "proceso": {"carpeta": "process", "id": "print_settings_id", "lista": False, "catalogo": "proceso"},
    "filamento": {"carpeta": "filament", "id": "filament_settings_id", "lista": True, "catalogo": "filamento"},
    "maquina": {"carpeta": "machine", "id": "printer_settings_id", "lista": False, "catalogo": "impresora"},
}
META = {"from", "inherits", "is_custom_defined", "name", "version", "print_settings_id",
        "filament_settings_id", "printer_settings_id", "setting_id", "base_id", "instantiation",
        "compatible_printers", "compatible_printers_condition", "compatible_prints",
        "compatible_prints_condition", "filament_id", "user_id", "updated_time", "type"}
CLAVES_TEMP_BOQUILLA = {"nozzle_temperature", "nozzle_temperature_initial_layer"}
# Otras temperaturas que Orca le manda a la boquilla (espera, purga, torre): se controlan contra
# el máximo de la impresora y el tope del material, sin el aviso de rango recomendado.
CLAVES_TEMP_BOQUILLA_OTRAS = {"idle_temperature", "filament_flush_temp", "filament_flush_temp_fast",
                              "filament_tower_interface_print_temp"}
# Claves que hacen que Orca ejecute código al laminar. Claude no escribe perfiles con ellas:
# al copiar un perfil base se quitan, y pedirlas con --set es un rechazo.
CLAVES_QUE_EJECUTAN = {
    "post_process": "corre programas de la PC al laminar",
    "plugins": "usa plugins de Orca",
    "slicing_pipeline_plugin": "corre plugins de Orca durante el laminado",
}


def _tiene_valor(valor) -> bool:
    valores = valor if isinstance(valor, list) else [valor]
    return any(str(v).strip() for v in valores if v is not None)
RE_TEMP_CAMA = re.compile(r"^(cool|eng|hot|textured|textured_cool|supertack)_plate_temp(_initial_layer)?$")
RE_NUM = re.compile(r"^-?\d+(\.\d+)?$")


def _numero_catalogo(valor):
    if valor is None:
        return None
    try:
        return float(str(valor).rstrip("f").rstrip("."))
    except ValueError:
        return None


def _normalizar(valor, info: dict):
    """Convierte un valor al formato de texto que guarda Orca."""
    tipo = info.get("type", "")
    v = str(valor).strip()
    if tipo.startswith("coBool"):
        if v.lower() in ("true", "si", "sí", "yes", "on"):
            return "1"
        if v.lower() in ("false", "no", "off"):
            return "0"
    if tipo.startswith("coPercent") and RE_NUM.match(v):
        return v + "%"
    return v


def _validar_valor(clave: str, valor: str, info: dict) -> list[tuple[str, str]]:
    problemas = []
    tipo = info.get("type", "")
    enum = info.get("enum_values") or []
    v = valor.strip()
    if v.lower() == "nil" and tipo.endswith("s"):
        return problemas  # en las listas de Orca, "nil" es "sin sobreescribir" (usa el valor de la impresora)
    if tipo.startswith("coEnum") and enum and v not in enum:
        cercanos = difflib.get_close_matches(v, enum, n=3)
        problemas.append((RECHAZO, f"{clave}={v}: valor no válido. Posibles: {', '.join(cercanos or enum[:8])}"))
        return problemas
    numero = None
    if tipo.startswith(("coInt", "coFloat", "coPercent")):
        base = v[:-1] if v.endswith("%") else v
        if not RE_NUM.match(base):
            problemas.append((RECHAZO, f"{clave}={v}: se esperaba un número."))
            return problemas
        if tipo.startswith("coInt") and "." in base:
            problemas.append((RECHAZO, f"{clave}={v}: se esperaba un número entero."))
            return problemas
        if tipo.startswith(("coInt", "coFloat")) and not tipo.startswith("coFloatOrPercent") and v.endswith("%"):
            problemas.append((RECHAZO, f"{clave}={v}: este parámetro no acepta porcentaje."))
            return problemas
        numero = float(base)
    if tipo.startswith("coBool") and v not in ("0", "1"):
        problemas.append((RECHAZO, f"{clave}={v}: se esperaba 0 o 1."))
    if numero is not None and not v.endswith("%"):
        minimo, maximo = _numero_catalogo(info.get("min")), _numero_catalogo(info.get("max"))
        if minimo is not None and numero < minimo:
            problemas.append((RECHAZO, f"{clave}={v}: por debajo del mínimo de Orca ({minimo:g})."))
        if maximo is not None and numero > maximo:
            problemas.append((RECHAZO, f"{clave}={v}: por encima del máximo de Orca ({maximo:g})."))
    return problemas


def _seguridad(clave: str, valor: str, impresora: dict | None, material: str | None) -> list[tuple[str, str]]:
    problemas = []
    principal = clave in CLAVES_TEMP_BOQUILLA
    es_boquilla = principal or clave in CLAVES_TEMP_BOQUILLA_OTRAS
    es_cama = bool(RE_TEMP_CAMA.match(clave))
    v = str(valor).strip()
    if clave == "standby_temperature_delta":
        try:
            if float(v) > 0:
                problemas.append((ADVERTENCIA, f"{clave}={v}: las boquillas en espera quedarían más calientes "
                                  "que al imprimir."))
        except ValueError:
            pass
        return problemas
    if not (es_boquilla or es_cama) or v.lower() in ("", "nil"):
        return problemas
    try:
        numero = float(v)
    except ValueError:
        return [(RECHAZO, f"{clave}={v}: la temperatura tiene que ser un número.")]
    if not math.isfinite(numero):
        return [(RECHAZO, f"{clave}={v}: la temperatura tiene que ser un número.")]
    valor = v
    materiales = comun.cargar_materiales()
    datos = materiales.get(material) if material else None
    if numero <= 0:
        return problemas
    tipo = "boquilla" if es_boquilla else "cama"
    if impresora:
        maximo = impresora["limites"]["boquilla_max_c" if es_boquilla else "cama_max_c"]
        if numero > maximo:
            problemas.append((RECHAZO, f"{clave}={valor} °C supera el máximo de la impresora ({maximo} °C)."))
            return problemas
    if datos:
        if numero > datos[f"{tipo}_tope"]:
            problemas.append((RECHAZO, f"{clave}={valor} °C supera el tope para {material} ({datos[f'{tipo}_tope']} °C)."))
        elif (es_cama or principal) and not (datos[tipo][0] <= numero <= datos[tipo][1]):
            problemas.append((ADVERTENCIA, f"{clave}={valor} °C fuera del rango recomendado para {material} "
                              f"({datos[tipo][0]}-{datos[tipo][1]} °C)."))
    return problemas


def es_clave_gcode(clave: str, info: dict | None) -> bool:
    """Claves de texto con G-code (inicio, fin, cambio de capa, de filamento...)."""
    return bool(info) and clave.endswith(("_gcode", "_gcodes")) and info.get("type") in ("coString", "coStrings")


def revisar_fragmento(clave: str, texto: str, impresora: dict | None) -> list[tuple[str, str]]:
    """Pasa el G-code de una clave del perfil por el mismo control que el G-code laminado."""
    if not str(texto).strip():
        return []
    datos = dict(revisar_gcode.IMPRESORA_GENERICA)
    if impresora and impresora.get("limites"):
        datos["limites"] = impresora["limites"]
    r = revisar_gcode.revisar(None, datos, None, texto=str(texto), fragmento=True)
    return [(h["gravedad"], f"{clave}: {h['mensaje']}" + (f" (línea {h['linea']} del bloque)" if h.get("linea") else ""))
            for h in r["hallazgos"]]


def perfiles_de_usuario(config: dict | None) -> set[str]:
    """Nombres de perfiles de usuario conocidos, desde config.json de la carpeta taller-3d."""
    nombres: set[str] = set()
    for imp in (config or {}).get("impresoras", []):
        for clave, valor in imp.items():
            if isinstance(valor, str) and (clave.startswith("perfil") or clave.endswith("_auto")):
                nombres.add(valor)
            elif isinstance(valor, dict) and clave in ("procesos", "filamentos"):
                nombres.update(v for v in valor.values() if isinstance(v, str))
    return nombres


def validar(perfil: dict, tipo: str, impresora: dict | None = None, material: str | None = None,
            catalogo: dict | None = None, usuarios: set[str] | None = None) -> list[dict]:
    catalogo = catalogo or comun.cargar_catalogo()
    conf = TIPOS[tipo]
    hallazgos: list[dict] = []

    def agregar(g, m):
        hallazgos.append({"gravedad": g, "mensaje": m})

    for obligatoria in ("name", "inherits", "from"):
        if not perfil.get(obligatoria):
            agregar(RECHAZO, f"Falta '{obligatoria}'.")
    if perfil.get("from") not in (None, "User"):
        agregar(ADVERTENCIA, f"from={perfil.get('from')}: los perfiles de usuario llevan from=User.")
    nombre = str(perfil.get("name", ""))
    if any(c in nombre for c in "/\\"):
        agregar(RECHAZO, "El nombre no puede tener barras.")
    hereda = str(perfil.get("inherits", ""))
    if hereda in (usuarios or set()) or hereda.startswith(("AUTO ", "TEST ")):
        agregar(RECHAZO, f"inherits='{hereda}' es un perfil de usuario; tiene que ser uno de sistema.")
    if material is None:
        material = comun.normalizar_material(perfil.get("filament_type")) or comun.normalizar_material(hereda) \
            or comun.normalizar_material(nombre)

    for clave, valor in perfil.items():
        if clave in META:
            continue
        if clave in CLAVES_QUE_EJECUTAN and _tiene_valor(valor):
            agregar(RECHAZO, f"'{clave}' {CLAVES_QUE_EJECUTAN[clave]}: Claude no escribe perfiles con scripts "
                    "ni plugins. Si querés usarlos, elegilos vos en Orca.")
            continue
        info = catalogo.get(clave)
        if info is None:
            cercanas = difflib.get_close_matches(clave, list(catalogo), n=3)
            agregar(RECHAZO, f"'{clave}' no existe en Orca {comun.VERSION_ORCA}."
                    + (f" ¿Quisiste decir: {', '.join(cercanas)}?" if cercanas else ""))
            continue
        if info.get("preset") != conf["catalogo"]:
            agregar(RECHAZO, f"'{clave}' es un parámetro de {info.get('preset')}, no de {tipo}.")
            continue
        valores = valor if isinstance(valor, list) else [valor]
        if conf["lista"] and not isinstance(valor, list):
            agregar(ADVERTENCIA, f"'{clave}': en filamentos los valores van como lista; lo corrijo al crear.")
        for v in valores:
            for g, m in _validar_valor(clave, str(v), info) + _seguridad(clave, str(v), impresora, material):
                agregar(g, m)
            if es_clave_gcode(clave, info):
                for g, m in revisar_fragmento(clave, v, impresora):
                    agregar(g, m)
    return hallazgos


def construir(tipo: str, nombre: str, hereda: str, base: dict | None, cambios: dict, quitar: list[str],
              catalogo: dict) -> dict:
    conf = TIPOS[tipo]
    anulaciones = {k: v for k, v in (base or {}).items() if k not in META}
    for clave in quitar:
        anulaciones.pop(clave, None)
    for clave, valor in cambios.items():
        info = catalogo.get(clave, {})
        if isinstance(valor, list):
            anulaciones[clave] = [_normalizar(v, info) for v in valor]
        else:
            anulaciones[clave] = _normalizar(valor, info)
    perfil = {"from": "User", "inherits": hereda, "is_custom_defined": "0", "name": nombre,
              "version": f"{comun.VERSION_ORCA}.0"}
    perfil[conf["id"]] = [nombre] if conf["lista"] else nombre
    for clave, valor in anulaciones.items():
        if conf["lista"]:
            perfil[clave] = valor if isinstance(valor, list) else [str(valor)]
        else:
            perfil[clave] = valor[0] if isinstance(valor, list) and len(valor) == 1 else valor
    return perfil


CLAVE_CAMA = {
    "Cool Plate": "cool_plate_temp",
    "Textured Cool Plate": "textured_cool_plate_temp",
    "Engineering Plate": "eng_plate_temp",
    "High Temp Plate": "hot_plate_temp",
    "Textured PEI Plate": "textured_plate_temp",
    "Supertack Plate": "supertack_plate_temp",
}


def temperaturas_para_cama(perfil: dict, cama: str, impresora: dict | None, material: str | None):
    """Temperaturas de cama [otras capas, primera capa] para el tipo de cama del usuario.

    Por línea de comandos Orca usa siempre "Cool Plate", así que estas temperaturas se copian
    a cool_plate_temp y cool_plate_temp_initial_layer.
    """
    if cama not in CLAVE_CAMA:
        raise SystemExit(f"Tipo de cama desconocido: {cama}. Opciones: {', '.join(CLAVE_CAMA)}")
    clave = CLAVE_CAMA[cama]

    def leer(k):
        v = perfil.get(k)
        v = v[0] if isinstance(v, list) and v else v
        return str(v) if v not in (None, "") else None

    otras, primera = leer(clave), leer(f"{clave}_initial_layer")
    if otras is None or primera is None:
        tabla = (impresora or {}).get("cama_sistema", {}).get(material or "")
        if tabla:
            otras = otras or str(tabla[0])
            primera = primera or str(tabla[1])
    if otras is None or primera is None:
        raise SystemExit(f"No sé las temperaturas de cama para {cama} con este filamento: pasalas con "
                         "--set cool_plate_temp=N --set cool_plate_temp_initial_layer=N")
    return otras, primera


def diferencias(viejo: dict, nuevo: dict) -> list[str]:
    salida = []
    for clave in sorted(set(viejo) | set(nuevo)):
        if clave in ("updated_time",):
            continue
        a, b = viejo.get(clave), nuevo.get(clave)
        if a == b:
            continue
        if a is None:
            salida.append(f"+ {clave} = {b}")
        elif b is None:
            salida.append(f"- {clave} (era {a})")
        else:
            salida.append(f"~ {clave}: {a} → {b}")
    return salida


def _setting_id(impresora: dict | None, hereda: str) -> str | None:
    if not impresora:
        return None
    sistema = impresora.get("sistema", {})
    for grupo in ("procesos", "filamentos"):
        for datos in sistema.get(grupo, {}).values():
            if datos.get("nombre") == hereda:
                return datos.get("setting_id")
    maquina = sistema.get("maquina", {})
    return maquina.get("setting_id") if maquina.get("nombre") == hereda else None


def _imprimir(hallazgos: list[dict]) -> str:
    estado = comun.peor(*(h["gravedad"] for h in hallazgos)) if hallazgos else APROBADO
    print(f"RESULTADO: {comun.TITULO[estado]}")
    etiqueta = {RECHAZO: "[RECHAZO]", ADVERTENCIA: "[ADVERTENCIA]"}
    for h in sorted(hallazgos, key=lambda h: h["gravedad"] != RECHAZO):
        print(f"  {etiqueta[h['gravedad']]} {h['mensaje']}")
    return estado


def _parse_set(items: list[str]) -> dict:
    cambios = {}
    for item in items or []:
        if "=" not in item:
            raise SystemExit(f"--set necesita clave=valor (recibí '{item}')")
        clave, valor = item.split("=", 1)
        valor = valor.strip().strip('"')
        cambios[clave.strip()] = [v.strip() for v in valor.split("|")] if "|" in valor else valor
    return cambios


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Perfiles de usuario de OrcaSlicer.")
    sub = ap.add_subparsers(dest="accion", required=True)

    c = sub.add_parser("crear")
    c.add_argument("--tipo", choices=list(TIPOS), required=True)
    c.add_argument("--nombre", required=True)
    c.add_argument("--hereda", required=True, help="perfil de SISTEMA del que hereda")
    c.add_argument("--base", type=Path, help="perfil de usuario cuyas anulaciones se copian")
    c.add_argument("--set", action="append", default=[], help="clave=valor (listas con |)")
    c.add_argument("--set-json", type=Path, help="JSON con clave: valor")
    c.add_argument("--quitar", action="append", default=[])
    c.add_argument("--anterior", type=Path, help="versión actual del perfil, para mostrar los cambios")
    c.add_argument("--impresora", default="ender-3-v3-plus")
    c.add_argument("--material")
    c.add_argument("--config", type=Path, help="config.json del usuario (para conocer sus perfiles)")
    c.add_argument("--cama", help="tipo de cama del usuario (filamentos): copia sus temperaturas a cool_plate_temp*, "
                                  "que es la que usa Orca por línea de comandos")
    c.add_argument("--salida", type=Path, required=True, help="carpeta donde escribir el .json y el .info")

    v = sub.add_parser("validar")
    v.add_argument("archivo", type=Path)
    v.add_argument("--tipo", choices=list(TIPOS))
    v.add_argument("--impresora", default="ender-3-v3-plus")
    v.add_argument("--material")
    v.add_argument("--config", type=Path)

    d = sub.add_parser("diff")
    d.add_argument("viejo", type=Path)
    d.add_argument("nuevo", type=Path)

    a = ap.parse_args(argv)
    catalogo = comun.cargar_catalogo()

    if a.accion == "diff":
        for linea in diferencias(comun.cargar_json(a.viejo), comun.cargar_json(a.nuevo)) or ["(sin cambios)"]:
            print(linea)
        return

    impresora = comun.cargar_impresora(a.impresora) if a.impresora else None
    material = comun.normalizar_material(a.material) if a.material else None
    config = comun.cargar_json(a.config) if getattr(a, "config", None) and a.config.exists() else None
    usuarios = perfiles_de_usuario(config)

    if a.accion == "validar":
        perfil = comun.cargar_json(a.archivo)
        tipo = a.tipo or next((t for t, conf in TIPOS.items() if conf["id"] in perfil), None)
        if not tipo:
            raise SystemExit("No pude deducir el tipo de perfil: usá --tipo.")
        comun.salir(_imprimir(validar(perfil, tipo, impresora, material, catalogo, usuarios)))

    base = comun.cargar_json(a.base) if a.base else None
    cambios = _parse_set(a.set)
    if a.set_json:
        cambios.update(comun.cargar_json(a.set_json))
    if a.cama:
        if a.tipo != "filamento":
            raise SystemExit("--cama es para perfiles de filamento.")
        mat_cama = material or comun.normalizar_material(a.hereda) or comun.normalizar_material(a.nombre)
        origen = dict(base or {})
        origen.update(cambios)
        otras, primera = temperaturas_para_cama(origen, a.cama, impresora, mat_cama)
        cambios.setdefault("cool_plate_temp", otras)
        cambios.setdefault("cool_plate_temp_initial_layer", primera)
        print(f"Cama {a.cama}: la línea de comandos usa cool_plate_temp = {otras} °C "
              f"(primera capa {primera} °C).")
    quitados = [k for k in CLAVES_QUE_EJECUTAN if k not in cambios and _tiene_valor((base or {}).get(k))]
    if quitados:
        print("Quité por seguridad (Orca los ejecuta al laminar): "
              + ", ".join(f"{k} ({CLAVES_QUE_EJECUTAN[k]})" for k in quitados))
    perfil = construir(a.tipo, a.nombre, a.hereda, base, cambios, list(a.quitar) + quitados, catalogo)
    hallazgos = validar(perfil, a.tipo, impresora, material, catalogo, usuarios)
    estado = _imprimir(hallazgos)
    if a.anterior and a.anterior.exists():
        print("Cambios respecto del perfil actual:")
        for linea in diferencias(comun.cargar_json(a.anterior), perfil) or ["(sin cambios)"]:
            print(f"  {linea}")
    if estado == RECHAZO:
        print("No escribí el perfil: corregí los rechazos.")
        comun.salir(estado)
    a.salida.mkdir(parents=True, exist_ok=True)
    destino = a.salida / f"{a.nombre}.json"
    destino.write_text(json.dumps(perfil, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    print(f"Escrito: {destino}")
    sid = _setting_id(impresora, a.hereda)
    if sid:
        info = a.salida / f"{a.nombre}.info"
        info.write_text(f"sync_info = create\nuser_id = \nsetting_id = \nbase_id = {sid}\n"
                        f"updated_time = {int(time.time())}\n", encoding="utf-8")
        print(f"Escrito: {info}")
    print(f"Destino en la PC: ~/.config/OrcaSlicer/user/default/{TIPOS[a.tipo]['carpeta']}/")
    comun.salir(estado)


if __name__ == "__main__":
    main()
