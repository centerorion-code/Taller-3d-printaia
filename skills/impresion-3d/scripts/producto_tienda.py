#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
"""Arma la ficha de producto de una pieza impresa para una tienda WooCommerce.

Calcula el precio sugerido (material + luz + horas de máquina + embalaje, más el margen),
redacta la descripción con medidas, material y cuidados, y genera:
  - producto.json: datos para crear el producto por la API REST de WooCommerce (siempre como borrador);
  - producto_woocommerce.csv: para el importador de productos de WooCommerce (Publicado = -1, borrador);
  - ficha.md: el texto para revisar o copiar a mano.

Uso:
  python3 producto_tienda.py --nombre "Soporte en L reforzado" --material PETG --color Negro \\
      --informe-gcode informe_gcode.json --informe-stl informe_stl.json \\
      --config config.json --uso "Fijar estantes livianos a la pared" \\
      [--categoria "Soportes"] [--etiquetas "soporte,PETG"] [--precio 4500] [--salida carpeta]

Con --plantilla, además completa una fila en la plantilla CSV que exporta otra plataforma
(Tiendanube, Shopify, etc.), respetando sus encabezados exactos: plantilla_completa.csv.

config.json (carpeta taller-3d de la PC del usuario), secciones "costos" y "tienda":
  {"costos": {"moneda": "ARS", "precio_kwh": 150, "consumo_w": 180,
              "filamentos": {"PETG": {"precio_kg": 25000}}},
   "tienda": {"plataforma": "woocommerce", "url": "https://mitienda.com", "margen_pct": 60,
              "costo_hora_maquina": 300, "embalaje": 400, "redondeo": 100, "demora_dias": 3,
              "peso_embalaje_g": 50}}
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import math
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

CUIDADOS = {
    "PLA": ["No dejar al sol ni dentro de un auto: se deforma desde unos 50 °C.",
            "Limpiar con un paño húmedo; no usar lavavajillas."],
    "PETG": ["Resiste humedad y algo de calor (hasta unos 70 °C).",
             "Limpiar con un paño húmedo; no usar lavavajillas."],
    "TPU": ["Material flexible: se puede doblar sin romper.",
            "Limpiar con agua y jabón neutro."],
    "ASA": ["Apto para exterior: resiste sol y lluvia.",
            "Limpiar con un paño húmedo."],
    "ABS": ["Resiste calor moderado (hasta unos 85 °C).",
            "Limpiar con un paño húmedo."],
}
AVISO_3D = ("Pieza fabricada por impresión 3D: puede tener líneas de capa visibles y pequeñas "
            "variaciones de terminación, propias del proceso.")


def _slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:40]


def _redondear(valor: float, paso: float) -> float:
    return float(math.ceil(valor / paso) * paso) if paso else round(valor, 2)


def calcular_precio(gramos: float | None, segundos: float | None, material: str | None, config: dict,
                    filamento: str | None = None) -> dict:
    tienda = config.get("tienda", {})
    costos = config.get("costos", config)
    precios = costos.get("filamentos", {})
    mat = precios.get(filamento) or precios.get(material) or {}
    faltan = []
    precio_kg = mat.get("precio_kg")
    if precio_kg is None:
        faltan.append(f"precio por kg del filamento {material or ''}".strip())
    horas = (segundos or 0) / 3600
    material_ars = (gramos or 0) / 1000 * (precio_kg or 0)
    luz = horas * (costos.get("consumo_w") or 0) / 1000 * (costos.get("precio_kwh") or 0)
    if not costos.get("precio_kwh"):
        faltan.append("precio del kWh")
    maquina = horas * (tienda.get("costo_hora_maquina") or 0)
    embalaje = tienda.get("embalaje") or 0
    costo = material_ars + luz + maquina + embalaje
    margen = tienda.get("margen_pct")
    if margen is None:
        faltan.append("margen de ganancia")
    sugerido = _redondear(costo * (1 + (margen or 0) / 100), tienda.get("redondeo") or 0)
    return {
        "moneda": costos.get("moneda", "ARS"),
        "material": round(material_ars, 2),
        "luz": round(luz, 2),
        "horas_maquina": round(maquina, 2),
        "embalaje": round(embalaje, 2),
        "costo_total": round(costo, 2),
        "margen_pct": margen,
        "precio_sugerido": sugerido,
        "faltan_datos": faltan,
    }


def armar(args, config: dict) -> dict:
    gcode = comun.cargar_json(args.informe_gcode) if args.informe_gcode else {}
    stl = comun.cargar_json(args.informe_stl) if args.informe_stl else {}
    material = comun.normalizar_material(args.material) or gcode.get("material")
    est = gcode.get("estimaciones", {})
    gramos, segundos = est.get("gramos"), est.get("segundos")
    medidas = stl.get("medidas_mm") or ([float(v) for v in args.medidas.lower().split("x")] if args.medidas else None)
    filamento = (gcode.get("perfiles") or {}).get("filamento")
    precio = calcular_precio(gramos, segundos, material, config, filamento)
    precio_final = args.precio if args.precio is not None else precio["precio_sugerido"]
    tienda = config.get("tienda", {})

    puntos = []
    if medidas:
        puntos.append(f"Medidas: {medidas[0]:g} × {medidas[1]:g} × {medidas[2]:g} mm.")
    puntos.append(f"Material: {material or 'a confirmar'}" + (f", color {args.color}." if args.color else "."))
    if gramos:
        puntos.append(f"Peso aproximado: {gramos:.0f} g.")
    puntos += CUIDADOS.get(material, [])
    if tienda.get("demora_dias"):
        puntos.append(f"Se fabrica a pedido: demora aproximada de {tienda['demora_dias']} días hábiles.")
    puntos.append("Se puede hacer a medida o en otro color: consultanos.")

    corta = f"{args.nombre} impreso en 3D en {material or 'plástico'}" + (f" {args.color.lower()}" if args.color else "")
    corta += f". {args.uso.rstrip('.')}." if args.uso else "."
    descripcion_html = (
        (f"<p>{html.escape(args.uso.rstrip('.'))}.</p>\n" if args.uso else "")
        + "<ul>\n" + "".join(f"<li>{html.escape(p)}</li>\n" for p in puntos) + "</ul>\n"
        + f"<p><small>{html.escape(AVISO_3D)}</small></p>\n"
    )
    peso_kg = ((gramos or 0) + (tienda.get("peso_embalaje_g") or 0)) / 1000 if gramos else None
    sku = args.sku or f"P3D-{date.today():%Y%m%d}-{_slug(args.nombre)}"
    etiquetas = [e.strip() for e in (args.etiquetas or "").split(",") if e.strip()]
    if material and material not in etiquetas:
        etiquetas.append(material)

    producto = {
        "name": args.nombre,
        "type": "simple",
        "status": "draft",
        "sku": sku,
        "regular_price": f"{precio_final:.0f}" if precio_final else "",
        "short_description": corta,
        "description": descripcion_html,
        "categories": [{"name": args.categoria}] if args.categoria else [],
        "tags": [{"name": e} for e in etiquetas],
        "weight": f"{peso_kg:.3f}" if peso_kg else "",
        "dimensions": {"length": f"{medidas[0] / 10:.1f}", "width": f"{medidas[1] / 10:.1f}",
                       "height": f"{medidas[2] / 10:.1f}"} if medidas else {},
        "manage_stock": False,
        "images": [],
    }
    return {"producto": producto, "precio": precio, "puntos": puntos, "material": material, "sku": sku}


def escribir(resultado: dict, salida: Path) -> list[Path]:
    salida.mkdir(parents=True, exist_ok=True)
    p = resultado["producto"]
    archivos = []
    ruta = salida / "producto.json"
    ruta.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
    archivos.append(ruta)

    ruta = salida / "producto_woocommerce.csv"
    columnas = ["Type", "SKU", "Name", "Published", "Is featured?", "Visibility in catalog", "Short description",
                "Description", "Tax status", "In stock?", "Weight (kg)", "Length (cm)", "Width (cm)",
                "Height (cm)", "Regular price", "Categories", "Tags", "Images"]
    dim = p.get("dimensions") or {}
    fila = ["simple", p["sku"], p["name"], "-1", "0", "visible", p["short_description"], p["description"],
            "taxable", "1", p.get("weight", ""), dim.get("length", ""), dim.get("width", ""),
            dim.get("height", ""), p.get("regular_price", ""), ", ".join(c["name"] for c in p["categories"]),
            ", ".join(t["name"] for t in p["tags"]), ""]
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(columnas)
        escritor.writerow(fila)
    archivos.append(ruta)

    pr = resultado["precio"]
    lineas = [
        f"# {p['name']}",
        "",
        f"**Estado:** borrador (revisar antes de publicar) · **SKU:** {p['sku']}",
        f"**Precio:** {p.get('regular_price') or 'a definir'} {pr['moneda']}",
        "",
        f"**Descripción corta:** {p['short_description']}",
        "",
        "**Descripción:**",
        "",
        *[f"- {x}" for x in resultado["puntos"]],
        "",
        f"_{AVISO_3D}_",
        "",
        "## Cálculo del precio",
        "",
        f"- Material: {pr['material']} {pr['moneda']}",
        f"- Luz: {pr['luz']} {pr['moneda']}",
        f"- Horas de máquina: {pr['horas_maquina']} {pr['moneda']}",
        f"- Embalaje: {pr['embalaje']} {pr['moneda']}",
        f"- Costo total: {pr['costo_total']} {pr['moneda']}",
        f"- Margen: {pr['margen_pct'] if pr['margen_pct'] is not None else 'sin definir'} %",
        f"- Precio sugerido: {pr['precio_sugerido']} {pr['moneda']}",
    ]
    if pr["faltan_datos"]:
        lineas.append(f"- Faltan datos para un precio real: {', '.join(pr['faltan_datos'])}.")
    ruta = salida / "ficha.md"
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    archivos.append(ruta)
    return archivos


SINONIMOS = {
    "slug": ["identificador de url", "handle", "slug", "url"],
    "name": ["nombre", "name", "title", "titulo", "producto"],
    "price": ["precio", "regular price", "price", "variant price", "precio regular"],
    "sku": ["sku", "variant sku", "codigo", "código"],
    "description": ["descripcion", "descripción", "description", "body (html)", "body html", "body"],
    "categories": ["categorias", "categorías", "categories", "category", "product category", "type", "tipo"],
    "tags": ["tags", "etiquetas"],
    "weight": ["peso (kg)", "weight (kg)", "peso", "weight", "variant grams"],
    "height": ["alto (cm)", "height (cm)", "alto", "height"],
    "width": ["ancho (cm)", "width (cm)", "ancho", "width"],
    "length": ["profundidad (cm)", "length (cm)", "profundidad", "largo", "length", "depth"],
    "visible": ["mostrar en tienda", "published", "publicado", "status", "estado", "visible"],
    "physical": ["producto fisico", "producto físico", "requires shipping", "variant requires shipping"],
}


def _norm(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower().strip()
    return re.sub(r"\s+", " ", t)


def completar_plantilla(plantilla: Path, resultado: dict, salida: Path) -> Path:
    """Completa una fila de producto en la plantilla CSV de otra plataforma, sin tocar sus encabezados."""
    texto = plantilla.read_text(encoding="utf-8-sig")
    dialecto = csv.Sniffer().sniff(texto.splitlines()[0], delimiters=",;\t")
    encabezados = next(csv.reader([texto.splitlines()[0]], dialecto))
    p = resultado["producto"]
    dim = p.get("dimensions") or {}
    texto_plano = re.sub(r"<[^>]+>", " ", p["description"])
    valores = {
        "slug": _slug(p["name"]),
        "name": p["name"],
        "price": p.get("regular_price", ""),
        "sku": p["sku"],
        "description": p["description"],
        "categories": ", ".join(c["name"] for c in p["categories"]),
        "tags": ", ".join(t["name"] for t in p["tags"]),
        "weight": p.get("weight", ""),
        "height": f"{float(dim['height']):.0f}" if dim.get("height") else "",
        "width": f"{float(dim['width']):.0f}" if dim.get("width") else "",
        "length": f"{float(dim['length']):.0f}" if dim.get("length") else "",
        "visible": "NO",
        "physical": "SÍ",
    }
    fila = []
    usados = []
    for enc in encabezados:
        n = _norm(enc)
        clave = next((k for k, sin in SINONIMOS.items() if n in [_norm(s) for s in sin]), None)
        valor = valores.get(clave, "") if clave else ""
        if clave == "visible" and n in ("status", "estado"):
            valor = "draft"
        if clave == "visible" and n == "published":
            valor = "FALSE"
        if clave == "description" and "html" not in n and n not in ("description", "descripcion"):
            valor = texto_plano
        fila.append(valor)
        if valor:
            usados.append(enc)
    destino = salida / "plantilla_completa.csv"
    with open(destino, "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f, dialecto)
        escritor.writerow(encabezados)
        escritor.writerow(fila)
    print(f"Plantilla: completé {len(usados)} columnas ({', '.join(usados)}); el resto quedó vacío.")
    return destino


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Ficha de producto para WooCommerce.")
    ap.add_argument("--nombre", required=True)
    ap.add_argument("--material")
    ap.add_argument("--color")
    ap.add_argument("--uso", help="para qué sirve, en una frase")
    ap.add_argument("--categoria")
    ap.add_argument("--etiquetas", help="separadas por coma")
    ap.add_argument("--medidas", help="si no hay informe de STL, por ejemplo 60x30x40")
    ap.add_argument("--informe-gcode", type=Path, help="JSON de revisar_gcode.py --json")
    ap.add_argument("--informe-stl", type=Path, help="JSON de revisar_stl.py --json")
    ap.add_argument("--config", type=Path, help="config.json con precios y datos de la tienda")
    ap.add_argument("--precio", type=float, help="precio final elegido (si no, el sugerido)")
    ap.add_argument("--sku")
    ap.add_argument("--plantilla", type=Path, help="CSV exportado de otra plataforma para completar")
    ap.add_argument("--salida", type=Path, default=Path("."))
    a = ap.parse_args(argv)
    config = comun.cargar_json(a.config) if a.config and a.config.exists() else {}
    r = armar(a, config)
    for ruta in escribir(r, a.salida):
        print(f"Escrito: {ruta}")
    if a.plantilla:
        print(f"Escrito: {completar_plantilla(a.plantilla, r, a.salida)}")
    pr = r["precio"]
    print(f"Costo: {pr['costo_total']} {pr['moneda']} | Precio sugerido: {pr['precio_sugerido']} {pr['moneda']}")
    if pr["faltan_datos"]:
        print(f"Faltan datos: {', '.join(pr['faltan_datos'])}")


if __name__ == "__main__":
    main()
