#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
"""Arma la ficha de producto de una pieza impresa para una tienda WooCommerce.

Calcula el precio sugerido con costos.py (material, luz, desgaste de la impresora, fallas, tu tiempo y
embalaje, más el margen sobre el precio y las comisiones del canal),
redacta la descripción con medidas, material y cuidados, y genera:
  - producto.json: datos para crear el producto por la API REST de WooCommerce (siempre como borrador);
  - producto_woocommerce.csv: para el importador de productos de WooCommerce (Publicado = -1, borrador);
  - ficha.md: el texto para revisar o copiar a mano;
  - publicacion.json y vista-previa.html: la vista previa de cómo se vería en la tienda (vista_publicacion.py).

Con --textos (textos_ia.py revisar), el título para Mercado Libre, la descripción corta y los párrafos de venta los
escribió Gemini o Claude; los datos de la lista (medidas, material, cuidados) salen siempre de los informes.
Con --fotos-reales, las fotos de la pieza impresa van primero; si solo hay renderizadas, la descripción lo aclara.

Uso:
  python3 producto_tienda.py --nombre "Soporte en L reforzado" --material PETG --color Negro \\
      --informe-gcode informe_gcode.json --informe-stl informe_stl.json \\
      --config config.json --uso "Fijar estantes livianos a la pared" \\
      [--categoria "Soportes"] [--etiquetas "soporte,PETG"] [--precio 4500] [--salida carpeta]

Con --plantilla, además completa una fila en la plantilla CSV que exporta otra plataforma
(Tiendanube, Shopify, etc.), respetando sus encabezados exactos: plantilla_completa.csv.

config.json (carpeta taller-3d de la PC del usuario): secciones "costos", "tienda" e "impresoras"
(formato en references/configuracion.md; cómo se calcula, en references/costos.md).
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
import costos  # noqa: E402

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


def canal_de_plataforma(config: dict) -> str:
    tienda = config.get("tienda") or {}
    canales = costos.canales_de_config(tienda)
    if tienda.get("plataforma") == "mercadolibre" and "mercadolibre" in canales:
        return "mercadolibre"
    return "tienda" if "tienda" in canales else next(iter(canales))


def calcular_precio(gramos: float | None, segundos: float | None, material: str | None, config: dict,
                    filamento: str | None = None, impresora: str | None = None, canal: str | None = None,
                    margen_pct: float | None = None, precio: float | None = None) -> dict:
    """Costo real (costos.py) y precio por canal; el sugerido es el del canal de la tienda del usuario.

    margen_pct: el margen que el usuario eligió para este producto (si no, el habitual de la tienda).
    precio: un precio fijo que eligió; entonces cada canal muestra el margen real que le deja.
    """
    imp = costos.impresora_de_config(config, impresora)
    c = costos.costo_pieza(gramos, segundos, material, config, imp, filamento)
    p = costos.precios(c["total"], config, margen_pct=margen_pct, precio=precio)
    canal = canal if canal in p["canales"] else canal_de_plataforma(config)
    elegido = p["canales"].get(canal) or {}
    partes = c["partes"]
    return {
        "moneda": c["moneda"],
        "material": partes["material"],
        "luz": partes["luz"],
        "horas_maquina": partes["maquina"],
        "fallas": partes["fallas"],
        "mano_de_obra": partes["mano_de_obra"],
        "embalaje": partes["embalaje"],
        "costo_total": c["total"],
        "margen_pct": p["margen_pct"],
        "margen_habitual_pct": p["margen_habitual_pct"],
        "margen_elegido": margen_pct is not None or precio is not None,
        "precio_sugerido": elegido.get("precio"),
        "impuestos": p.get("impuestos"),
        "con_iva": p.get("con_iva", False),
        "margen_origen": p.get("margen_origen"),
        "canal": canal,
        "canales": p["canales"],
        "faltan_datos": c["faltan"] + p["faltan"],
        "supuestos": c["supuestos"] + ([p["aviso_margen"]] if p["aviso_margen"] else []),
    }


def _extra_precio(canal: dict) -> str:
    """Lo que acompaña al precio de un canal: el IVA (responsable inscripto) y si es el mínimo por pieza."""
    extra = f" con IVA ({canal['precio_sin_iva']} + IVA {canal['iva_venta']})" if canal.get("iva_venta") else ""
    return extra + (" (el mínimo por pieza)" if canal.get("por_precio_minimo") else "")


IMAGENES = (".jpg", ".jpeg", ".png", ".webp")
AVISO_ILUSTRATIVAS = ("Las imágenes son ilustrativas: la pieza real puede variar levemente en color y terminación.")


def fotos_de(salida: Path, reales: list[str] | None = None) -> tuple[list[str], int]:
    """Las fotos de la publicación, relativas a la carpeta producto/: primero las reales de la pieza impresa (las
    pasa el usuario, por ejemplo ../foto.jpg) y después las de producto renderizadas que hay en la carpeta."""
    reales = [r for r in reales or [] if isinstance(r, str) and r.lower().endswith(IMAGENES)]
    renders = sorted(p.name for p in Path(salida).glob("producto-*") if p.suffix.lower() in IMAGENES)
    if (Path(salida) / "foto_producto.png").exists():
        renders.append("foto_producto.png")
    return reales + [r for r in renders if r not in reales], len(reales)


def leer_textos(ruta: Path | None) -> dict | None:
    """textos.json de textos_ia.py revisar: título, descripción corta, descripción y palabras clave."""
    if not ruta:
        return None
    textos = comun.cargar_json(ruta)
    if not isinstance(textos, dict) or not textos.get("revisado") or not textos.get("descripcion_corta"):
        raise SystemExit(f"{ruta} no es un textos.json revisado: pasalo antes por textos_ia.py revisar.")
    return textos


def armar(args, config: dict) -> dict:
    gcode = comun.cargar_json(args.informe_gcode) if args.informe_gcode else {}
    stl = comun.cargar_json(args.informe_stl) if args.informe_stl else {}
    textos = leer_textos(getattr(args, "textos", None))
    fotos, reales = fotos_de(args.salida, getattr(args, "fotos_reales", None))
    material = comun.normalizar_material(args.material) or gcode.get("material")
    est = gcode.get("estimaciones", {})
    gramos, segundos = est.get("gramos"), est.get("segundos")
    medidas = stl.get("medidas_mm") or ([float(v) for v in args.medidas.lower().split("x")] if args.medidas else None)
    filamento = (gcode.get("perfiles") or {}).get("filamento")
    precio = calcular_precio(gramos, segundos, material, config, filamento, gcode.get("impresora"),
                             getattr(args, "canal", None), getattr(args, "margen", None), args.precio)
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
    if fotos and not reales:
        puntos.append(AVISO_ILUSTRATIVAS)

    # El texto de venta (si lo escribió Gemini o Claude y pasó textos_ia.py revisar) va antes de los datos, que
    # salen siempre de los informes.
    if textos:
        corta = textos["descripcion_corta"]
        parrafos = [p.strip() for p in str(textos.get("descripcion") or "").split("\n\n") if p.strip()]
    else:
        corta = f"{args.nombre} impreso en 3D en {material or 'plástico'}" + (f" {args.color.lower()}" if args.color else "")
        corta += f". {args.uso.rstrip('.')}." if args.uso else "."
        parrafos = [f"{args.uso.rstrip('.')}."] if args.uso else []
    descripcion_html = (
        "".join(f"<p>{html.escape(p)}</p>\n" for p in parrafos)
        + "<ul>\n" + "".join(f"<li>{html.escape(p)}</li>\n" for p in puntos) + "</ul>\n"
        + f"<p><small>{html.escape(AVISO_3D)}</small></p>\n"
    )
    titulo_ml = (textos or {}).get("titulo") or comun.una_linea(
        f"{args.nombre} impreso en 3D" + (f" {material}" if material else ""), 60)
    peso_kg = ((gramos or 0) + (tienda.get("peso_embalaje_g") or 0)) / 1000 if gramos else None
    sku = args.sku or f"P3D-{date.today():%Y%m%d}-{_slug(args.nombre)}"
    etiquetas = [e.strip() for e in (args.etiquetas or "").split(",") if e.strip()]
    if material and material not in etiquetas:
        etiquetas.append(material)
    for clave in (textos or {}).get("palabras_clave") or []:
        if len(etiquetas) < 10 and comun.plano(clave) not in {comun.plano(x) for x in etiquetas}:
            etiquetas.append(clave)

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
    return {"producto": producto, "precio": precio, "puntos": puntos, "material": material, "sku": sku,
            "precio_fijo": args.precio is not None, "parrafos": parrafos, "titulo_ml": titulo_ml,
            "textos": textos, "fotos": fotos, "fotos_reales": reales, "medidas_mm": medidas, "gramos": gramos,
            "color": args.color, "categoria": args.categoria, "carpeta": getattr(args, "carpeta", None),
            "tienda": {"url": tienda.get("url"), "plataforma": tienda.get("plataforma"),
                       "demora_dias": tienda.get("demora_dias")}}


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
    titulo_ml = resultado.get("titulo_ml") or p["name"]
    lineas = [
        f"# {p['name']}",
        "",
        f"**Estado:** borrador (revisar antes de publicar) · **SKU:** {p['sku']}",
        f"**Precio:** {p.get('regular_price') or 'a definir'} {pr['moneda']}",
        f"**Título para Mercado Libre:** {titulo_ml} ({len(titulo_ml)}/60 caracteres)",
        f"**Texto:** {autor_del_texto(resultado.get('textos'))}",
        "",
        f"**Descripción corta:** {p['short_description']}",
        "",
        "**Descripción:**",
        "",
        *[x for par in resultado.get("parrafos") or [] for x in (par, "")],
        *[f"- {x}" for x in resultado["puntos"]],
        "",
        f"_{AVISO_3D}_",
        "",
        "## Cálculo del precio",
        "",
        f"- Material: {pr['material']} {pr['moneda']}",
        f"- Luz: {pr['luz']} {pr['moneda']}",
        f"- Desgaste de la impresora: {pr['horas_maquina']} {pr['moneda']}",
        f"- Fallas: {pr['fallas']} {pr['moneda']}",
        f"- Tu tiempo: {pr['mano_de_obra']} {pr['moneda']}",
        f"- Embalaje: {pr['embalaje']} {pr['moneda']}",
        f"- Costo total: {pr['costo_total']} {pr['moneda']}",
        (f"- Precio elegido: {p.get('regular_price')} {pr['moneda']} (abajo, el margen real que deja en cada canal)"
         if resultado.get("precio_fijo") else
         f"- Margen sobre el precio{' sin IVA' if pr.get('con_iva') else ''}: "
         f"{pr['margen_pct'] if pr['margen_pct'] is not None else 'sin definir'} %"
         + (" (elegido para este producto)" if pr.get("margen_elegido") else
            f" (tu margen habitual{', ' + pr['margen_origen'] if pr.get('margen_origen') else ''})"
            if pr['margen_pct'] is not None else "")),
        *([f"- Impuestos de la venta: {pr['impuestos']}"] if pr.get("impuestos") else []),
        f"- Precio sugerido ({pr['canal']}): {pr['precio_sugerido']} {pr['moneda']}"
        + (" con IVA incluido" if pr.get("con_iva") else ""),
    ]
    for clave, canal in pr["canales"].items():
        if "error" in canal:
            lineas.append(f"- {canal.get('nombre') or clave}: {canal['error']}")
        else:
            lineas.append(f"- {canal.get('nombre') or clave}: precio {canal['precio']}{_extra_precio(canal)}, "
                          f"comisiones {canal['comisiones']}"
                          + (f", impuestos {canal['impuestos']}" if canal.get("impuestos") else "")
                          + f", te queda {canal['te_queda']}, ganancia {canal['ganancia']} ({canal['margen_real_pct']} %)")
    lineas += [f"- Supuesto: {s}" for s in pr["supuestos"]]
    if pr["faltan_datos"]:
        lineas.append(f"- Faltan datos para un precio real: {', '.join(pr['faltan_datos'])}.")
    ruta = salida / "ficha.md"
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    archivos.append(ruta)

    # Lo que necesita la vista previa (vista_publicacion.py): la página como en la tienda y lo que hay que revisar.
    publicacion = {"version": 1, "producto": p, "precio": pr, "puntos": resultado["puntos"],
                   "aviso_3d": AVISO_3D, **{k: resultado.get(k) for k in (
                       "parrafos", "titulo_ml", "textos", "fotos", "fotos_reales", "medidas_mm", "gramos", "color",
                       "categoria", "carpeta", "tienda", "material")}}
    ruta = salida / "publicacion.json"
    ruta.write_text(json.dumps(publicacion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    archivos.append(ruta)
    import vista_publicacion
    ruta = salida / "vista-previa.html"
    ruta.write_text(vista_publicacion.generar(publicacion), encoding="utf-8")
    archivos.append(ruta)
    return archivos


def autor_del_texto(textos: dict | None) -> str:
    if not textos:
        return "armado con la plantilla (uso, medidas, material y cuidados)"
    quien = {"gemini": "Gemini (gratis), revisado por Claude contra los datos de la pieza",
             "claude": "Claude, revisado contra los datos de la pieza"}.get(textos.get("autor"), "revisado por Claude")
    cambios = [c for c in textos.get("cambios") or [] if isinstance(c, str) and c.strip()]
    return f"escrito por {quien}" + (f"; Claude corrigió: {'; '.join(cambios)}" if cambios else "")


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
    elegir = ap.add_mutually_exclusive_group()
    elegir.add_argument("--precio", type=float, help="precio final elegido (si no, el sugerido)")
    elegir.add_argument("--margen", type=float, help="margen sobre el precio elegido para este producto, en %%")
    ap.add_argument("--canal", help="canal del precio sugerido (tienda, mercadolibre…); si no, el de la plataforma")
    ap.add_argument("--sku")
    ap.add_argument("--plantilla", type=Path, help="CSV exportado de otra plataforma para completar")
    ap.add_argument("--textos", type=Path, help="textos.json revisado (textos_ia.py revisar): título y descripción")
    ap.add_argument("--fotos-reales", nargs="*", default=[],
                    help="fotos de la pieza impresa, relativas a --salida (por ejemplo ../foto.jpg): van primero")
    ap.add_argument("--carpeta", help="carpeta de la pieza, relativa a la carpeta de trabajo (para los pedidos)")
    ap.add_argument("--salida", type=Path, default=Path("."))
    a = ap.parse_args(argv)
    config = comun.cargar_json(a.config) if a.config and a.config.exists() else {}
    r = armar(a, config)
    for ruta in escribir(r, a.salida):
        print(f"Escrito: {ruta}")
    if a.plantilla:
        print(f"Escrito: {completar_plantilla(a.plantilla, r, a.salida)}")
    pr = r["precio"]
    print(f"Costo: {pr['costo_total']} {pr['moneda']} | Precio sugerido ({pr['canal']}): {pr['precio_sugerido']} "
          f"{pr['moneda']}")
    for clave, canal in pr["canales"].items():
        if "error" not in canal:
            print(f"  {canal.get('nombre') or clave}: {canal['precio']}{_extra_precio(canal)} → te queda "
                  f"{canal['te_queda']}, ganancia {canal['ganancia']} ({canal['margen_real_pct']} % del precio"
                  f"{' sin IVA' if canal.get('iva_venta') else ''})")
    if pr["faltan_datos"]:
        print(f"Faltan datos: {', '.join(pr['faltan_datos'])}")


if __name__ == "__main__":
    main()
