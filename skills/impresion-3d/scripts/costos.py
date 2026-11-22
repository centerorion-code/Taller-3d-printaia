#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
"""Costo real de una pieza y precio de venta por canal, con los datos del usuario (config.json).

Costo de una pieza buena:
  material      = gramos de Orca / 1000 × precio del kg del filamento
  luz           = consumo de la impresora (W) × (horas de Orca + calentamiento) / 1000 × precio del kWh
  máquina       = precio de la impresora / horas de vida × (1 + mantenimiento %) × horas de Orca
  fallas        = (material + luz + máquina) × fallas % / (1 − fallas %)   (lo que se pierde en las que salen mal)
  mano de obra  = minutos de preparación y terminación / 60 × precio de tu hora
  costo         = material + luz + máquina + fallas + mano de obra + embalaje

Precio por canal, con el margen sobre el precio (lo que te queda de cada venta, después de comisiones):
  precio = (costo + cargo fijo × (1 + IVA)) / (1 − (comisión % + cuotas %) × (1 + IVA) − margen %)
  (el IVA se suma a las comisiones solo si el canal lo cobra, como Mercado Libre)

Precio del kWh, de la boleta de luz:
  marginal = cargo variable del último escalón × (1 + impuestos %)   (lo que cuesta cada kWh de más)
  promedio = (total − cargos fijos) / kWh consumidos                 (si la boleta no separa el cargo variable)
Si hay datos para los dos, se usa el marginal: los cargos fijos se pagan igual aunque no imprimas.

Uso:
  python3 costos.py luz --config config.json --kwh 310 --total 53072 [--cargo-variable 120.5] \\
      [--impuestos-pct 26.9] [--cargos-fijos 4800] [--periodo 2026-10] [--empresa EDET] --salida config.json
  python3 costos.py pieza --config config.json --informe-gcode informe_gcode.json --impresora <id o nombre> \\
      [--material PETG] [--minutos-mano 10] [--json costo.json]
  python3 costos.py pieza --config config.json --gramos 38 --segundos 4320 --impresora hi
  python3 costos.py pieza ... --margenes                 # tres márgenes para elegir (uno menor, el habitual, uno mayor)
  python3 costos.py pieza ... --margenes 30,45,60        # los márgenes que digas
  python3 costos.py pieza ... --margen 50                # el margen elegido para este producto
  python3 costos.py pieza ... --precio 4500              # un precio fijo: el margen real que deja en cada canal
  python3 costos.py estado --config config.json          # qué falta configurar para tener costos reales
  python3 costos.py consumo --config config.json --impresora hi --promedio 80 --origen oficial \\
      --fuente "<enlace>" --salida config.json            # el consumo promedio que publica el fabricante
  python3 costos.py consumo --config config.json --impresora hi --datos creality-hi.json [--material PETG] \\
      [--nominal 350] [--fuente "<enlace de la ficha>"] --salida config.json   # estimado por el tamaño de la cama

Consumo de la impresora: lo que importa es el promedio mientras imprime. La potencia nominal de la ficha (la de la
fuente) es el máximo calentando: una impresora con fuente de 350 W imprime con 100-170 W.

El margen es sobre el precio (de cada venta, qué parte te queda de ganancia), no un recargo sobre el costo:
un recargo del 50 % es un margen del 33 %.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

FALLAS_PCT = 10            # si el usuario no dice otra cosa (5-10 % con experiencia, 15-25 % al empezar)
CALENTAMIENTO_MIN = 5      # cama y boquilla antes de empezar
MANTENIMIENTO_PCT = 5      # repuestos y reparaciones en toda la vida de la impresora, sobre su precio
VIDA_HORAS = 4000          # unos 3 años a 4 horas por día
LUZ_VIEJA_DIAS = 120       # después de esto, pedir una boleta más nueva


def _num(valor) -> float | None:
    """Un número de la configuración; también "15 %" o "0,18". None si no hay o no se entiende."""
    if isinstance(valor, str):
        valor = valor.replace("%", "").replace(" ", "").strip()
        if valor.count(",") == 1 and "." not in valor:
            valor = valor.replace(",", ".")
    try:
        return None if valor in (None, "") or isinstance(valor, bool) else float(valor)
    except (TypeError, ValueError):
        return None


def _precio_kg(dato) -> float | None:
    """El precio del kg de un filamento: {"precio_kg": 25000} o directamente 25000."""
    return _num(dato.get("precio_kg")) if isinstance(dato, dict) else _num(dato)


# ------------------------------------------------------------------ luz

def precio_kwh_de_boleta(kwh=None, total=None, cargo_variable=None, impuestos_pct=None, cargos_fijos=None) -> dict:
    """Precio del kWh a partir de los números de la boleta."""
    kwh, total, cv = _num(kwh), _num(total), _num(cargo_variable)
    imp, fijos = _num(impuestos_pct) or 0.0, _num(cargos_fijos) or 0.0
    r: dict = {}
    def redondear(x: float) -> float:                    # 152,9 ARS o 0,1815 EUR: sin perder el precio chico
        return round(x, 4) if abs(x) < 10 else round(x, 2)

    if kwh and kwh > 0 and total and total > 0:
        r["promedio_kwh"] = redondear((total - fijos) / kwh)
    if cv and cv > 0:
        r["marginal_kwh"] = redondear(cv * (1 + imp / 100))
    if "marginal_kwh" in r:
        r["precio_kwh"], r["metodo"] = r["marginal_kwh"], "marginal"
    elif "promedio_kwh" in r:
        r["precio_kwh"], r["metodo"] = r["promedio_kwh"], "promedio"
    else:
        raise ValueError("Faltan datos de la boleta: hacen falta los kWh consumidos y el total, o el cargo variable "
                         "por kWh.")
    if not 0.005 <= r["precio_kwh"] <= 100000:          # de medio centavo (otras monedas) a 100.000
        raise ValueError(f"El precio del kWh da {r['precio_kwh']}: revisá los números de la boleta.")
    return r


def luz_de_config(config: dict) -> dict:
    costos = config.get("costos") or {}
    luz = costos.get("luz") if isinstance(costos.get("luz"), dict) else {}
    precio = _num(luz.get("precio_kwh")) or _num(costos.get("precio_kwh"))
    vieja = False
    periodo, cargado = str(luz.get("periodo") or ""), luz.get("cargado")
    try:
        if len(periodo) >= 7:                          # AAAA-MM: la boleta vale desde el fin de ese mes
            anio, mes = int(periodo[:4]), int(periodo[5:7])
            desde = date(anio + mes // 12, mes % 12 + 1, 1)
            vieja = (date.today() - desde).days > LUZ_VIEJA_DIAS
        elif cargado:
            vieja = (date.today() - date.fromisoformat(str(cargado)[:10])).days > LUZ_VIEJA_DIAS
    except ValueError:
        vieja = False
    return {"precio_kwh": precio, "de_boleta": bool(luz.get("precio_kwh")), "vieja": vieja,
            "metodo": luz.get("metodo"), "periodo": luz.get("periodo"), "empresa": luz.get("empresa")}


# ------------------------------------------------------------------ impresoras

def impresora_de_config(config: dict, clave: str | None) -> dict:
    """La impresora de config.json por id, nombre o archivo de datos (si no, la por defecto)."""
    impresoras = [i for i in config.get("impresoras") or [] if isinstance(i, dict)]
    clave = clave or config.get("impresora_por_defecto")
    if clave:
        c = comun.plano(clave)
        for i in impresoras:
            nombres = [i.get("id"), i.get("nombre"), Path(str(i.get("datos") or "")).stem]
            if any(n and comun.plano(n) == c for n in nombres):
                return i
    if len(impresoras) == 1:
        unica = impresoras[0]
        if clave:                                       # se pidió otra: usar la única, pero decirlo
            return dict(unica, _aviso=f"«{clave}» no está en tu configuración: usé los datos de la "
                                      f"{unica.get('nombre') or unica.get('id')}")
        return unica
    return {}


# ------------------------------------------------------------------ consumo de la impresora

# De dónde salió el consumo (primera palabra de consumo_fuente), cómo se muestra y cuánto vale el dato.
ETIQUETAS_CONSUMO = {"medido": "medido", "oficial": "ficha oficial", "prueba": "prueba publicada",
                     "usuario": "dato tuyo", "estimado": "estimado", "sin fuente": "sin fuente"}
RANGO_CONSUMO = {"medido": 4, "oficial": 3, "prueba": 3, "usuario": 2, "estimado": 1, "sin fuente": 0, "falta": 0}
CAMA_TIBIA = {"PETG", "PETG-CF"}                  # cama a 70-80 °C
CAMA_CALIENTE = {"ABS", "ASA", "PC", "PA"}        # cama a 90-110 °C


def origen_consumo(ci: dict | None) -> str:
    """De dónde salió el consumo de una impresora: medido, oficial, prueba, usuario, estimado, sin fuente o falta."""
    ci = ci if isinstance(ci, dict) else {}
    if _num(ci.get("consumo_w")) is None:
        return "falta"
    fuente = comun.plano(ci.get("consumo_fuente"))
    for origen in ("medido", "oficial", "prueba", "usuario", "estimado"):
        if fuente.startswith(origen):
            return origen
    return "sin fuente"


def consumo_estimado(ancho_mm: float, fondo_mm: float, material: str | None = None,
                     nominal_w: float | None = None) -> dict:
    """Consumo promedio imprimiendo, estimado por el tamaño de la cama, para cuando la ficha solo da la potencia
    nominal (que es el máximo calentando, no el promedio).

    Unos 30 W fijos (placa, motores, ventiladores y boquilla) más 0,13 W por cm² de cama, con PLA. Da valores
    parecidos (dentro de un 25 %) a los promedios publicados de impresoras sin calefactor de cámara: Prusa MK
    (80 W con PLA, 25 × 21 cm), Ender 3 (100-125 W, 22 × 22 cm), Bambu Lab H2S (180-200 W, 34 × 32 cm). PETG
    +10 % (cama más caliente); ABS, ASA, PC y nylon +40 %. Nunca más que el 80 % de la potencia nominal.
    """
    ancho, fondo = _num(ancho_mm), _num(fondo_mm)
    if not all(v is not None and math.isfinite(v) and 0 < v <= 2000 for v in (ancho, fondo)):
        raise ValueError("La cama va en mm, como 300x300.")
    area = ancho * fondo / 100
    m = comun.normalizar_material(material) if material else None
    factor = 1.1 if m in CAMA_TIBIA else 1.4 if m in CAMA_CALIENTE else 1.0
    watts = (30 + 0.13 * area) * factor
    nominal = _num(nominal_w)
    tope = bool(nominal and math.isfinite(nominal) and nominal > 0 and watts > 0.8 * nominal)
    if tope:
        watts = 0.8 * nominal
    return {"consumo_w": max(5, int(5 * round(watts / 5))), "cama_mm": [ancho, fondo], "area_cm2": round(area),
            "material": m or (str(material) if material else "PLA"), "factor": factor, "tope_nominal": tope}


def area_de_datos(datos: dict) -> tuple[float, float]:
    """Ancho y fondo del área de impresión del JSON de una impresora del taller."""
    a = datos.get("area") if isinstance(datos.get("area"), dict) else {}
    try:
        return float(a["x_max"]) - float(a.get("x_min") or 0), float(a["y_max"]) - float(a.get("y_min") or 0)
    except (KeyError, TypeError, ValueError):
        raise ValueError("El JSON de la impresora no tiene el área de impresión (area.x_max, area.y_max).")


def _entrada_impresora(config: dict, clave: str | None) -> dict | None:
    """La entrada real de config.json (para escribirla), solo si el id, el nombre o los datos coinciden."""
    c = comun.plano(clave or config.get("impresora_por_defecto"))
    for i in config.get("impresoras") or []:
        if isinstance(i, dict) and c and any(n and comun.plano(n) == c for n in
                                             (i.get("id"), i.get("nombre"), Path(str(i.get("datos") or "")).stem)):
            return i
    return None


def fijar_consumo(config: dict, clave: str | None, consumo_w, origen: str, fuente: str | None = None,
                  nominal_w=None, reemplazar: bool = False) -> dict:
    """Guarda el consumo en impresoras[].costo (consumo_w, consumo_fuente, consumo_fecha y potencia_nominal_w).
    No pisa un dato mejor (un medido con un estimado, por ejemplo) salvo con reemplazar. Devuelve la entrada."""
    if origen not in ("medido", "oficial", "prueba", "usuario", "estimado"):
        raise ValueError(f"Origen desconocido: {origen}")
    consumo = _num(consumo_w)
    if consumo is None or not 1 <= consumo <= 5000:
        raise ValueError("El consumo va en W, entre 1 y 5000.")
    entrada = _entrada_impresora(config, clave)
    if entrada is None:
        raise ValueError(f"«{clave}» no está preparada en config.json: primero hay que prepararla (/impresoras).")
    ci = entrada.get("costo") if isinstance(entrada.get("costo"), dict) else {}
    antes = origen_consumo(ci)
    if not reemplazar and RANGO_CONSUMO[antes] > RANGO_CONSUMO[origen]:
        raise ValueError(f"Ya tiene un consumo {ETIQUETAS_CONSUMO[antes]} ({_num(ci.get('consumo_w')):g} W): "
                         f"no lo piso con uno {ETIQUETAS_CONSUMO[origen]} (con --reemplazar, sí).")
    texto = {"prueba": "prueba publicada"}.get(origen, origen)
    fuente = " ".join(str(fuente or "").split())[:300]
    ci.update({"consumo_w": int(round(consumo)), "consumo_fuente": f"{texto}: {fuente}" if fuente else texto,
               "consumo_fecha": time.strftime("%Y-%m-%d")})
    nominal = _num(nominal_w)
    if nominal and math.isfinite(nominal) and nominal > 0:
        ci["potencia_nominal_w"] = int(nominal) if float(nominal).is_integer() else nominal
    entrada["costo"] = ci
    return entrada


# ------------------------------------------------------------------ costo de una pieza

def costo_pieza(gramos, segundos, material: str | None, config: dict, impresora: dict | None = None,
                filamento: str | None = None, minutos_mano=None) -> dict:
    costos = config.get("costos") or {}
    tienda = config.get("tienda") or {}
    imp = impresora or {}
    ci = imp.get("costo") if isinstance(imp.get("costo"), dict) else {}
    gramos, segundos = _num(gramos) or 0.0, _num(segundos) or 0.0
    horas = segundos / 3600
    faltan, supuestos = [], []
    nombre_imp = f"la {imp.get('nombre') or imp.get('id')}" if (imp.get("nombre") or imp.get("id")) else "la impresora"
    if imp.get("_aviso"):
        supuestos.append(imp["_aviso"])

    precios = costos.get("filamentos") or {}
    precios = precios if isinstance(precios, dict) else {}
    datos_mat = precios.get(filamento or "") or precios.get(material or "") or {}
    precio_kg = _precio_kg(datos_mat)
    if precio_kg is None:
        faltan.append(f"precio del kg de {material or 'filamento'}")
    material_c = gramos / 1000 * (precio_kg or 0)

    luz = luz_de_config(config)
    if luz["precio_kwh"] is None:
        faltan.append("precio del kWh (mandá una foto o el PDF de tu boleta de luz)")
    elif not luz["de_boleta"]:
        supuestos.append("precio del kWh cargado a mano, no sacado de la boleta")
    elif luz["vieja"]:
        supuestos.append("la boleta de luz tiene más de 4 meses: conviene una más nueva")
    consumo = _num(ci.get("consumo_w")) or _num(costos.get("consumo_w"))
    if consumo is None:
        faltan.append(f"consumo de {nombre_imp} (W)")
    else:
        origen = origen_consumo(ci) if _num(ci.get("consumo_w")) else "general"
        if origen != "medido":
            texto = f"consumo de {nombre_imp}: {consumo:.0f} W ({ETIQUETAS_CONSUMO.get(origen, 'general del taller')})"
            if origen not in ("oficial", "prueba"):
                texto += "; medido con un medidor de enchufe es más exacto"
            supuestos.append(texto)
    calentamiento = _num(ci.get("calentamiento_min"))
    calentamiento = CALENTAMIENTO_MIN if calentamiento is None else calentamiento
    horas_luz = horas + (calentamiento / 60 if segundos else 0)
    luz_c = (consumo or 0) * horas_luz / 1000 * (luz["precio_kwh"] or 0)

    precio_imp = _num(ci.get("precio"))
    if precio_imp:
        vida = _num(ci.get("vida_horas")) or VIDA_HORAS
        mant = _num(ci.get("mantenimiento_pct"))
        mant = MANTENIMIENTO_PCT if mant is None else mant
        hora_maquina = precio_imp / vida * (1 + mant / 100)
        if not ci.get("vida_horas"):
            supuestos.append(f"vida de {nombre_imp}: {VIDA_HORAS} horas")
    else:
        hora_maquina = _num(tienda.get("costo_hora_maquina"))
        if hora_maquina is None:
            faltan.append(f"cuánto te costó {nombre_imp} (para el desgaste)")
            hora_maquina = 0.0
    maquina_c = hora_maquina * horas

    fallas = _num(costos.get("fallas_pct"))
    if fallas is None:
        fallas = FALLAS_PCT
        supuestos.append(f"fallas: {FALLAS_PCT} % de las impresiones")
    fallas = min(max(fallas, 0.0), 90.0)
    base = material_c + luz_c + maquina_c
    fallas_c = base * fallas / (100 - fallas)

    mano = costos.get("mano_de_obra") if isinstance(costos.get("mano_de_obra"), dict) else {}
    precio_hora = _num(mano.get("precio_hora"))
    minutos = _num(minutos_mano)
    if minutos is None:
        minutos = _num(mano.get("minutos_por_pieza"))
    if precio_hora is None:
        faltan.append("cuánto vale tu hora (preparar, sacar soportes, embalar)")
    mano_c = (minutos or 0) / 60 * (precio_hora or 0)
    embalaje = _num(tienda.get("embalaje")) or 0.0

    partes = {"material": material_c, "luz": luz_c, "maquina": maquina_c, "fallas": fallas_c,
              "mano_de_obra": mano_c, "embalaje": embalaje}
    total = sum(partes.values())
    return {
        "moneda": costos.get("moneda") or "ARS",
        "impresora": imp.get("nombre") or imp.get("id"),
        "gramos": round(gramos, 1),
        "horas_orca": round(horas, 2),
        "horas_luz": round(horas_luz, 2),
        "consumo_w": consumo,
        "precio_kwh": luz["precio_kwh"],
        "kwh": round((consumo or 0) * horas_luz / 1000, 3),
        "fallas_pct": fallas,
        "partes": {k: round(v, 2) for k, v in partes.items()},
        "total": round(total, 2),
        "faltan": faltan,
        "supuestos": supuestos,
    }


# ------------------------------------------------------------------ precio por canal

def margen_de_config(tienda: dict) -> tuple[float | None, str | None]:
    """Margen sobre el precio. El margen_pct de antes de la 0.1.14 era un recargo sobre el costo."""
    nuevo = _num(tienda.get("margen_precio_pct"))
    if nuevo is not None:
        return nuevo, None
    viejo = _num(tienda.get("margen_pct"))
    if viejo is not None and viejo > -100:
        equivalente = round(viejo / (100 + viejo) * 100, 1)
        return equivalente, (f"Tu margen de {viejo:g} % era un recargo sobre el costo: equivale a {equivalente:g} % "
                             "sobre el precio. Confirmalo o cambialo (margen_precio_pct).")
    return None, None


def canales_de_config(tienda: dict) -> dict:
    canales = tienda.get("canales") if isinstance(tienda.get("canales"), dict) else {}
    if not canales:
        return {"tienda": {"nombre": "Tu tienda", "comision_pct": 0}}
    return {k: v for k, v in canales.items() if isinstance(v, dict)}


def _redondear(valor: float, paso: float) -> float:
    paso = abs(paso or 0)
    return float(math.ceil(valor / paso - 1e-9) * paso) if paso else round(valor, 2)


def _tasas(canal: dict) -> tuple[float, float, float | None]:
    """(comisión más cuotas, en tanto por uno y con el IVA de la comisión; cargo fijo con IVA; tope del cargo fijo)."""
    iva = 0.21 if canal.get("iva_comision") else 0.0
    tasa = ((_num(canal.get("comision_pct")) or 0) + (_num(canal.get("cuotas_pct")) or 0)) / 100 * (1 + iva)
    return tasa, (_num(canal.get("cargo_fijo")) or 0) * (1 + iva), _num(canal.get("cargo_fijo_hasta"))


def desglose(costo: float, canal: dict, precio: float) -> dict:
    """Con un precio dado: comisiones, lo que te queda, la ganancia y el margen real en ese canal."""
    tasa, fijo, hasta = _tasas(canal)
    cargos = precio * tasa + (0.0 if hasta and precio >= hasta else fijo)
    ganancia = precio - cargos - costo
    minimo = None
    if tasa < 1:                                        # el precio que apenas cubre el costo
        minimo = (costo + fijo) / (1 - tasa)
        if hasta and minimo >= hasta:
            minimo = max(costo / (1 - tasa), hasta)
    return {
        "nombre": canal.get("nombre"),
        "precio": round(precio, 2),
        "comisiones": round(cargos, 2),
        "te_queda": round(precio - cargos, 2),
        "ganancia": round(ganancia, 2),
        "margen_real_pct": round(ganancia / precio * 100, 1) if precio else None,
        "precio_minimo": round(minimo, 2) if minimo else None,
    }


def precio_canal(costo: float, canal: dict, margen_pct: float, redondeo: float = 0) -> dict:
    """El precio que deja margen_pct del precio después de las comisiones del canal."""
    tasa, fijo, hasta = _tasas(canal)
    divisor = 1 - tasa - margen_pct / 100
    if divisor <= 0.02:
        raise ValueError(f"Comisiones ({tasa * 100:.1f} %) más margen ({margen_pct:g} %) llegan al 100 %: no hay precio "
                         "que cierre. Bajá el margen.")
    precio = (costo + fijo) / divisor
    if hasta and precio >= hasta:                       # el cargo fijo solo va en las ventas baratas
        # Desde el tope ya no hay cargo fijo: alcanza con el precio sin cargo, o con el tope si ese da menos.
        precio = max(costo / divisor, hasta)
    return desglose(costo, canal, _redondear(precio, redondeo))


def precios(costo: float, config: dict, margen_pct: float | None = None, precio: float | None = None) -> dict:
    """Precio por canal con el margen habitual de la tienda, o con el margen elegido para este producto, o con un
    precio fijo (entonces muestra el margen real que deja en cada canal)."""
    tienda = config.get("tienda") or {}
    habitual, aviso = margen_de_config(tienda)
    margen = margen_pct if margen_pct is not None else habitual
    r: dict = {"margen_pct": margen, "margen_habitual_pct": habitual, "precio_fijo": precio,
               "aviso_margen": aviso if margen_pct is None else None, "canales": {}, "faltan": []}
    if margen is None and precio is None:
        r["faltan"].append("qué margen querés ganar sobre el precio (por ejemplo 40 %)")
        margen = 0.0
    redondeo = _num(tienda.get("redondeo")) or 0
    for clave, canal in canales_de_config(tienda).items():
        if canal.get("comision_pct") is None and clave != "tienda":
            r["faltan"].append(f"comisión de {canal.get('nombre') or clave}")
        try:
            r["canales"][clave] = (desglose(costo, canal, precio) if precio is not None
                                   else precio_canal(costo, canal, margen, redondeo))
        except ValueError as error:
            r["canales"][clave] = {"nombre": canal.get("nombre"), "error": str(error)}
    return r


def margenes_sugeridos(habitual: float | None) -> list[float]:
    """Tres márgenes para que el usuario elija en cada producto: uno más bajo, el habitual y uno más alto."""
    h = habitual if habitual is not None else 40.0
    return sorted({max(min(15.0, h), h - 15), h, min(h + 20, max(75.0, min(h + 5, 95.0)))})


def opciones(costo: float, config: dict, margenes: list[float] | None = None) -> list[dict]:
    """Una opción por margen, con el precio y la ganancia en cada canal (para preguntarle al usuario)."""
    habitual, _ = margen_de_config(config.get("tienda") or {})
    return [{"margen_pct": m, "habitual": m == habitual, **precios(costo, config, margen_pct=m)}
            for m in (margenes or margenes_sugeridos(habitual))]


# ------------------------------------------------------------------ qué falta configurar

def estado_taller(config: dict) -> list[dict]:
    """Lo que está listo y lo que falta para tener costos y precios reales, con la frase para pedírselo a Claude."""
    costos = config.get("costos") or {}
    tienda = config.get("tienda") or {}
    items: list[dict] = []

    def agregar(tema, listo, texto, frase=None, aviso=False):
        items.append({"tema": tema, "estado": "listo" if listo and not aviso else ("revisar" if listo else "falta"),
                      "texto": texto, "frase": None if listo and not aviso else frase})

    impresoras = [i for i in config.get("impresoras") or [] if isinstance(i, dict)]
    agregar("Impresoras", bool(impresoras),
            f"{len(impresoras)} preparada{'s' if len(impresoras) != 1 else ''}: "
            + ", ".join(str(i.get("nombre") or i.get("id")) for i in impresoras) if impresoras
            else "Ninguna impresora preparada", "Prepará mi impresora")
    luz = luz_de_config(config)
    if luz["precio_kwh"] is None:
        agregar("Luz", False, "Falta el precio del kWh", "Te paso mi boleta de luz para el precio del kWh")
    else:
        origen = (f"de la boleta {luz['empresa'] or ''} {luz['periodo'] or ''}".replace("  ", " ").strip()
                  if luz["de_boleta"] else "cargado a mano")
        agregar("Luz", True, f"kWh a {luz['precio_kwh']:g} {costos.get('moneda') or 'ARS'} ({origen})",
                "Te paso mi boleta de luz más nueva", aviso=luz["vieja"] or not luz["de_boleta"])
    for i in impresoras:
        ci = i.get("costo") if isinstance(i.get("costo"), dict) else {}
        nombre = i.get("nombre") or i.get("id")
        consumo = _num(ci.get("consumo_w"))
        origen = origen_consumo(ci)
        agregar(f"Consumo de {nombre}", consumo is not None,
                f"{consumo:.0f} W ({ETIQUETAS_CONSUMO[origen]})" if consumo is not None else "Falta el consumo",
                f"Buscá el consumo de la {nombre} en internet" if origen in ("falta", "sin fuente") else
                f"Quiero medir el consumo real de la {nombre}", aviso=origen in ("estimado", "sin fuente"))
        agregar(f"Precio de {nombre}", _num(ci.get("precio")) is not None,
                _plata(_num(ci.get("precio")), costos.get("moneda") or "ARS") if _num(ci.get("precio")) else
                "Falta cuánto la pagaste (para el desgaste)", f"La {nombre} me costó $…")
    filamentos = costos.get("filamentos") or {}
    filamentos = filamentos if isinstance(filamentos, dict) else {}
    sin_precio = [m for m, d in filamentos.items() if _precio_kg(d) is None]
    agregar("Filamentos", bool(filamentos) and not sin_precio,
            "Precio por kg: " + ", ".join(f"{m} {_plata(_precio_kg(d), '').strip()}" for m, d in filamentos.items()
                                          if _precio_kg(d) is not None)
            if filamentos and not sin_precio else f"Falta el precio por kg de {', '.join(sin_precio) or 'tus filamentos'}",
            f"El rollo de {sin_precio[0] if sin_precio else 'PETG'} me sale $… el kilo")
    mano = costos.get("mano_de_obra") if isinstance(costos.get("mano_de_obra"), dict) else {}
    agregar("Tu hora", _num(mano.get("precio_hora")) is not None,
            f"{_plata(_num(mano.get('precio_hora')), '').strip()} por hora, {(_num(mano.get('minutos_por_pieza')) or 0):g} min por pieza"
            if _num(mano.get("precio_hora")) is not None else "Falta cuánto vale tu hora",
            "Mi hora de trabajo vale $… y le dedico … minutos a cada pieza")
    if tienda.get("plataforma"):
        margen, aviso = margen_de_config(tienda)
        agregar("Margen", margen is not None, f"{margen:g} % sobre el precio" if margen is not None else
                "Falta el margen", "Quiero ganar …% sobre el precio", aviso=bool(aviso))
        for clave, canal in canales_de_config(tienda).items():
            sin = canal.get("comision_pct") is None and clave != "tienda"
            agregar(f"Comisión de {canal.get('nombre') or clave}", not sin,
                    f"{_num(canal.get('comision_pct')) or 0:g} %" + (" + IVA" if canal.get("iva_comision") else "")
                    if not sin else "Falta la comisión", f"Mercado Libre me cobra …% en mi categoría")
    return items


# ------------------------------------------------------------------ línea de comandos

def _guardar(ruta: Path, config: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _plata(valor, moneda) -> str:
    return f"{valor:,.0f} {moneda}".replace(",", ".")


def _coma(valor) -> str:
    return "—" if valor is None else f"{valor:g}".replace(".", ",")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="accion", required=True)
    lz = sub.add_parser("luz", help="precio del kWh de la boleta de luz (guarda solo los números de la tarifa)")
    lz.add_argument("--config", type=Path, required=True)
    lz.add_argument("--kwh", type=float, help="kWh consumidos en el período")
    lz.add_argument("--total", type=float, help="total de la boleta")
    lz.add_argument("--cargo-variable", type=float, help="cargo variable por kWh del último escalón")
    lz.add_argument("--impuestos-pct", type=float, help="IVA y tasas que van sobre la energía, en %")
    lz.add_argument("--cargos-fijos", type=float, help="cargos fijos del período (para el promedio)")
    lz.add_argument("--periodo", help="AAAA-MM")
    lz.add_argument("--empresa")
    lz.add_argument("--salida", type=Path, required=True)
    pz = sub.add_parser("pieza", help="costo de una pieza y precio por canal")
    pz.add_argument("--config", type=Path, required=True)
    pz.add_argument("--informe-gcode", type=Path)
    pz.add_argument("--gramos", type=float)
    pz.add_argument("--segundos", type=float)
    pz.add_argument("--material")
    pz.add_argument("--filamento", help="nombre del perfil de filamento, si tiene precio propio")
    pz.add_argument("--impresora", help="id o nombre de la impresora en config.json")
    pz.add_argument("--minutos-mano", type=float, help="minutos de trabajo tuyo en esta pieza")
    elegir = pz.add_mutually_exclusive_group()
    elegir.add_argument("--margen", type=float, help="margen sobre el precio elegido para este producto, en %%")
    elegir.add_argument("--precio", type=float, help="precio fijo elegido: muestra el margen real en cada canal")
    pz.add_argument("--margenes", nargs="?", const="sugeridos",
                    help="opciones para elegir: lista como 30,40,60 (sin valor: una más baja, la habitual y una más alta)")
    pz.add_argument("--json", type=Path)
    es = sub.add_parser("estado", help="qué falta configurar")
    es.add_argument("--config", type=Path, required=True)
    es.add_argument("--json", action="store_true")
    cs = sub.add_parser("consumo", help="consumo promedio de una impresora: el encontrado o estimado por la cama")
    cs.add_argument("--config", type=Path, required=True)
    cs.add_argument("--impresora", help="id o nombre de la impresora en config.json")
    dato = cs.add_mutually_exclusive_group(required=True)
    dato.add_argument("--promedio", type=float, help="W promedio imprimiendo (ficha oficial, prueba publicada o medido)")
    dato.add_argument("--cama", help="ancho x fondo de la cama en mm, como 300x300 (para estimarlo)")
    dato.add_argument("--datos", type=Path, help="JSON de la impresora del taller: estima con su área de impresión")
    cs.add_argument("--origen", choices=["oficial", "prueba", "medido", "usuario"], help="de dónde salió --promedio")
    cs.add_argument("--material", help="el material que más usa en esa impresora (cambia el estimado)")
    cs.add_argument("--nominal", type=float, help="potencia nominal de la ficha, en W (se anota y es el tope del estimado)")
    cs.add_argument("--fuente", help="enlace o texto de dónde salió el dato")
    cs.add_argument("--reemplazar", action="store_true", help="pisar un consumo mejor (por ejemplo, uno medido)")
    cs.add_argument("--salida", type=Path, help="config.json donde guardarlo (sin esto, solo lo muestra)")
    cs.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.accion in ("luz", "consumo") and not a.config.exists():
        raise SystemExit(f"No encuentro {a.config}: pasá el config.json del taller (no se escribió nada).")
    if a.accion == "consumo":
        if a.promedio is not None and not 1 <= a.promedio <= 5000:
            raise SystemExit("--promedio va en W, entre 1 y 5000 (no se escribió nada).")
        if a.nominal is not None and not 1 <= a.nominal <= 20000:
            raise SystemExit("--nominal va en W, como dice la ficha (no se escribió nada).")
        if a.promedio is not None and not a.origen:
            raise SystemExit("Con --promedio va --origen: oficial, prueba (publicada), medido o usuario.")
        if a.salida and not a.impresora:
            raise SystemExit("Para guardarlo hace falta --impresora (el id o el nombre en config.json).")
        if a.datos and not a.datos.exists():
            raise SystemExit(f"No encuentro {a.datos} (no se escribió nada).")
    if a.accion == "pieza" and a.precio is not None and a.precio <= 0:
        raise SystemExit("--precio tiene que ser mayor que cero.")
    config = comun.cargar_json(a.config) if a.config.exists() else {}

    if a.accion == "luz":
        try:
            r = precio_kwh_de_boleta(a.kwh, a.total, a.cargo_variable, a.impuestos_pct, a.cargos_fijos)
        except ValueError as error:
            raise SystemExit(str(error))
        costos = config.setdefault("costos", {})
        costos["luz"] = {**r, "kwh": a.kwh, "total": a.total, "cargo_variable": a.cargo_variable,
                         "impuestos_pct": a.impuestos_pct, "cargos_fijos": a.cargos_fijos, "periodo": a.periodo,
                         "empresa": a.empresa, "cargado": time.strftime("%Y-%m-%d")}
        costos["luz"] = {k: v for k, v in costos["luz"].items() if v is not None}
        costos["precio_kwh"] = r["precio_kwh"]           # para los scripts de antes de la 0.1.14
        _guardar(a.salida, config)
        texto = {"marginal": "cargo variable más impuestos (lo que cuesta cada kWh de más)",
                 "promedio": "total menos cargos fijos, dividido por los kWh"}[r["metodo"]]
        print(f"Precio del kWh: {_coma(r['precio_kwh'])} ({texto}).")
        if "promedio_kwh" in r and "marginal_kwh" in r:
            print(f"  Promedio de la boleta, sin los cargos fijos: {_coma(r['promedio_kwh'])} por kWh.")
        print(f"Guardado en {a.salida} (solo los números de la tarifa).")
    elif a.accion == "pieza":
        gcode = comun.cargar_json(a.informe_gcode) if a.informe_gcode else {}
        est = gcode.get("estimaciones") or {}
        gramos = a.gramos if a.gramos is not None else est.get("gramos")
        segundos = a.segundos if a.segundos is not None else est.get("segundos")
        if gramos is None or segundos is None:
            raise SystemExit("Faltan los gramos y el tiempo de Orca (--informe-gcode o --gramos y --segundos).")
        material = comun.normalizar_material(a.material) or gcode.get("material")
        impresora = impresora_de_config(config, a.impresora or gcode.get("impresora"))
        c = costo_pieza(gramos, segundos, material, config, impresora, a.filamento, a.minutos_mano)
        p = precios(c["total"], config, margen_pct=a.margen, precio=a.precio)
        m = c["moneda"]
        print(f"Costo de la pieza: {_plata(c['total'], m)} ({_coma(c['gramos'])} g, "
              f"{comun.formato_duracion(segundos)} según Orca, {_coma(c['kwh'])} kWh)")
        nombres = {"material": "material", "luz": "luz", "maquina": "desgaste de la impresora", "fallas": "fallas",
                   "mano_de_obra": "tu tiempo", "embalaje": "embalaje"}
        partes = [f"{nombres[k]} {_plata(v, m)}" for k, v in c["partes"].items() if v]
        if partes:
            print("  " + " · ".join(partes))
        sin_costo = not c["total"]
        if sin_costo:
            print("  Sin precios todavía: faltan los datos de abajo.")
        for clave, canal in ({} if sin_costo else p["canales"]).items():
            if "error" in canal:
                print(f"  {canal.get('nombre') or clave}: {canal['error']}")
            else:
                print(f"  {canal.get('nombre') or clave}: precio {_plata(canal['precio'], m)} → comisiones "
                      f"{_plata(canal['comisiones'], m)}, te queda {_plata(canal['te_queda'], m)}, ganancia "
                      f"{_plata(canal['ganancia'], m)} ({_coma(canal['margen_real_pct'])} % del precio)")
        for aviso in ([p["aviso_margen"]] if p["aviso_margen"] else []) + c["supuestos"]:
            print(f"  Supuesto: {aviso}")
        for falta in c["faltan"] + p["faltan"]:
            print(f"  Falta: {falta}")
        ops = []
        if a.margenes:
            try:
                lista = None if a.margenes == "sugeridos" else [float(x) for x in a.margenes.replace(" ", "").split(",")]
            except ValueError:
                raise SystemExit("--margenes va como 30,40,60")
            ops = opciones(c["total"], config, lista) if not sin_costo else []
            if ops:
                print("Opciones de margen (sobre el precio):")
            for o in ops:
                linea = [f"{canal.get('nombre') or clave} {_plata(canal['precio'], m)} (ganás {_plata(canal['ganancia'], m)})"
                         if "error" not in canal else f"{canal.get('nombre') or clave}: no cierra"
                         for clave, canal in o["canales"].items()]
                print(f"  {o['margen_pct']:g} %{' (tu margen habitual)' if o['habitual'] else ''}: " + " · ".join(linea))
        if a.json:
            a.json.write_text(json.dumps({"costo": c, "precios": p, "opciones": ops}, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    elif a.accion == "consumo":
        entrada = _entrada_impresora(config, a.impresora) if a.impresora else None
        nombre = f"la {entrada.get('nombre') or entrada.get('id')}" if entrada else (
            f"la {a.impresora}" if a.impresora else "la impresora")
        try:
            if a.promedio is not None:
                r = {"consumo_w": int(round(a.promedio)), "origen": a.origen}
                texto = (f"Consumo de {nombre}: {r['consumo_w']} W imprimiendo "
                         f"({ETIQUETAS_CONSUMO[a.origen]}{', ' + a.fuente if a.fuente else ''}).")
            else:
                if a.datos:
                    ancho, fondo = area_de_datos(comun.cargar_json(a.datos))
                else:
                    partes = [_num(x) for x in a.cama.lower().replace("×", "x").replace("*", "x").split("x")]
                    if len(partes) != 2 or None in partes:
                        raise ValueError("La cama va en mm, como 300x300.")
                    ancho, fondo = partes
                r = {**consumo_estimado(ancho, fondo, a.material, a.nominal), "origen": "estimado"}
                cama = f"{_coma(ancho)} × {_coma(fondo)} mm"
                nominal = (f"; la ficha dice {_coma(a.nominal)} W, que es el máximo calentando, no el promedio"
                           if a.nominal else "")
                tope = "; lo limité al 80 % de la potencia nominal" if r["tope_nominal"] else ""
                texto = (f"Consumo de {nombre}: unos {r['consumo_w']} W imprimiendo {r['material']} (estimado por la "
                         f"cama de {cama}{nominal}{tope}). Con un medidor de enchufe se puede medir el real.")
                a.fuente = f"cama de {cama}, imprimiendo {r['material']}" + (
                    f"; potencia nominal {_coma(a.nominal)} W" if a.nominal else "") + (
                    f" ({a.fuente})" if a.fuente else "")
            if a.salida:
                fijar_consumo(config, a.impresora, r["consumo_w"], r["origen"], a.fuente, a.nominal, a.reemplazar)
                _guardar(a.salida, config)
        except ValueError as error:
            raise SystemExit(f"{str(error).rstrip('.')} (no se escribió nada)." if a.salida else str(error))
        if a.json:
            print(json.dumps({**r, "fuente": a.fuente, "texto": texto, "guardado": bool(a.salida)},
                             ensure_ascii=False, indent=2))
        else:
            print(texto)
            if a.salida:
                print(f"Guardado en {a.salida}.")
    else:
        items = estado_taller(config)
        if a.json:
            print(json.dumps(items, ensure_ascii=False, indent=2))
        else:
            for i in items:
                marca = {"listo": "✓", "revisar": "!", "falta": "✗"}[i["estado"]]
                print(f"{marca} {i['tema']}: {i['texto']}" + (f" → decí: «{i['frase']}»" if i["frase"] else ""))


if __name__ == "__main__":
    main()
