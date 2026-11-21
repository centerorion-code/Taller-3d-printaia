#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
"""Catálogo de los diseños e impresiones del taller.

Lleva un índice (`taller-3d/catalogo.json` en la carpeta de trabajo) con una entrada por pieza y
arma `catalogo.html`, una página que se abre con el navegador desde la carpeta de trabajo: muestra
la vista de cada pieza, sus datos y enlaces a sus archivos, ordenadas por mes, con buscador y
filtros. Las imágenes se cargan desde la carpeta de cada pieza: no hace falta traerlas.

Uso:
  # Agregar o actualizar una pieza (cada vez que se guarda, se lamina, se imprime o se publica)
  python3 catalogo.py agregar --catalogo catalogo.json --carpeta impresiones/2026-11-21_soporte-router \\
      --nombre "Soporte para router" [--tipo impresion|diseno] [--material PETG] [--color negro] \\
      [--informe-gcode informe_gcode.json] [--informe-stl informe_stl.json] [--producto producto.json] \\
      [--archivos pieza.stl pieza.py vista.png informe.md] [--imagen vista.png] \\
      [--estado disenada|laminada|impresa|en_tienda] [--nota "..."] [--url-tienda https://...] [--moneda ARS]

  # Sumar las piezas que ya estaban: listado de device_list_dir (recursive=true) de la carpeta de trabajo
  python3 catalogo.py desde-listado --catalogo catalogo.json --listado listado.json

  # Armar la página
  python3 catalogo.py html --catalogo catalogo.json --salida catalogo.html [--titulo "Taller 3D"]

  # Resumen en texto (para contestar "¿qué piezas hice?")
  python3 catalogo.py resumen --catalogo catalogo.json [--buscar texto]
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

TIPOS = {"impresion": "Impresión", "diseno": "Diseño"}
ESTADOS = {
    "disenada": "Diseñada",
    "laminada": "Lista para imprimir",
    "impresa": "Impresa",
    "en_tienda": "En la tienda (borrador)",
}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]
RE_CARPETA = re.compile(r"^(impresiones|disenos)/(\d{4}-\d{2}-\d{2})_([^/]+)$")
IMAGENES = (".png", ".jpg", ".jpeg", ".webp", ".gif")


def _ahora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def cargar(ruta: Path) -> dict:
    if ruta.exists() and ruta.read_text(encoding="utf-8").strip():
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        if not isinstance(datos, dict) or not isinstance(datos.get("piezas"), list):
            raise SystemExit(f"{ruta} no tiene el formato del catálogo.")
        return datos
    return {"version": 1, "piezas": []}


def guardar(ruta: Path, catalogo: dict) -> None:
    catalogo["actualizado"] = _ahora()
    catalogo["piezas"].sort(key=lambda p: (p.get("fecha") or "", p.get("carpeta") or ""), reverse=True)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(catalogo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalizar_carpeta(carpeta: str) -> str:
    c = str(carpeta).replace("\\", "/").strip().strip("/")
    partes = [p for p in c.split("/") if p not in ("", ".")]
    if not partes or any(p == ".." for p in partes):
        raise SystemExit(f"Carpeta inválida: {carpeta!r} (tiene que ser relativa a la carpeta de trabajo).")
    return "/".join(partes)


def nombre_desde_carpeta(carpeta: str) -> str:
    m = RE_CARPETA.match(carpeta)
    base = m.group(3) if m else carpeta.rsplit("/", 1)[-1]
    texto = re.sub(r"[-_]+", " ", base).strip()
    return texto[:1].upper() + texto[1:] if texto else carpeta


def url_segura(url: str | None) -> str | None:
    if not url:
        return None
    u = urlparse(str(url).strip())
    return u.geturl() if u.scheme in ("http", "https") and u.netloc else None


def _leer_json(ruta: str | None) -> dict:
    if not ruta:
        return {}
    datos = comun.cargar_json(ruta)
    return datos if isinstance(datos, dict) else {}


def datos_de_informes(gcode: dict, stl: dict, producto: dict) -> dict:
    """Lo que interesa del catálogo, sacado de los informes de los otros scripts."""
    d: dict = {}
    if stl.get("medidas_mm"):
        d["medidas_mm"] = [round(float(x), 1) for x in stl["medidas_mm"]][:3]
    if gcode:
        est = gcode.get("estimaciones") or {}
        if est.get("segundos"):
            d["segundos"] = int(est["segundos"])
            d["tiempo"] = comun.formato_duracion(est["segundos"])
        if est.get("gramos"):
            d["gramos"] = round(float(est["gramos"]), 1)
        costo = gcode.get("costo") or {}
        if costo.get("total"):
            d["costo"] = {"total": costo["total"], "moneda": costo.get("moneda")}
        if gcode.get("material"):
            d["material"] = gcode["material"]
        if gcode.get("estado"):
            d["revision"] = gcode["estado"]
        d["estado"] = "laminada"
    if producto:
        if producto.get("regular_price"):
            d["precio"] = {"valor": producto["regular_price"]}
        d["estado"] = "en_tienda"
    return d


def agregar(catalogo: dict, carpeta: str, **campos) -> dict:
    carpeta = normalizar_carpeta(carpeta)
    pieza = next((p for p in catalogo["piezas"] if p.get("carpeta") == carpeta), None)
    if pieza is None:
        m = RE_CARPETA.match(carpeta)
        pieza = {
            "carpeta": carpeta,
            "tipo": "diseno" if carpeta.startswith("disenos/") else "impresion",
            "nombre": nombre_desde_carpeta(carpeta),
            "fecha": m.group(2) if m else time.strftime("%Y-%m-%d"),
            "estado": "disenada",
            "archivos": [],
        }
        catalogo["piezas"].append(pieza)
    for clave, valor in campos.items():
        if valor in (None, "", [], {}):
            continue
        if clave == "archivos":
            nuevos = [normalizar_carpeta(a) for a in valor]
            pieza["archivos"] = sorted(set(pieza.get("archivos", [])) | set(nuevos))
        elif clave == "url_tienda":
            segura = url_segura(valor)
            if segura:
                pieza["url_tienda"] = segura
        elif clave == "tipo" and valor not in TIPOS:
            raise SystemExit(f"Tipo desconocido: {valor} (impresion o diseno).")
        elif clave == "estado" and valor not in ESTADOS:
            raise SystemExit(f"Estado desconocido: {valor} ({', '.join(ESTADOS)}).")
        else:
            pieza[clave] = valor
    if pieza.get("precio") and "moneda" not in pieza["precio"]:
        moneda = (pieza.get("costo") or {}).get("moneda")
        if moneda:
            pieza["precio"]["moneda"] = moneda
    pieza["actualizado"] = _ahora()
    return pieza


def _rutas_del_listado(listado) -> list[str]:
    if isinstance(listado, dict):
        entradas = listado.get("entries") or []
        return [str(e.get("name", "")) for e in entradas if isinstance(e, dict) and e.get("type") == "file"]
    if isinstance(listado, list):
        return [str(x.get("name", "")) if isinstance(x, dict) else str(x) for x in listado]
    return []


def desde_listado(catalogo: dict, listado) -> list[str]:
    """Suma las carpetas de piezas que hay en el listado y todavía no están. Devuelve las nuevas."""
    por_carpeta: dict[str, list[str]] = {}
    for ruta in _rutas_del_listado(listado):
        r = ruta.replace("\\", "/").strip("/")
        m = re.match(r"^((?:impresiones|disenos)/\d{4}-\d{2}-\d{2}_[^/]+)/(.+)$", r)
        if m:
            por_carpeta.setdefault(m.group(1), []).append(m.group(2))
    existentes = {p.get("carpeta") for p in catalogo["piezas"]}
    nuevas = []
    for carpeta, archivos in sorted(por_carpeta.items()):
        estado = "disenada"
        if any(a.lower().endswith((".gcode", ".gco", ".gcode.3mf")) for a in archivos):
            estado = "laminada"
        if any(a.lower().startswith("producto/") for a in archivos):
            estado = "en_tienda"
        if carpeta in existentes:
            agregar(catalogo, carpeta, archivos=archivos)
        else:
            agregar(catalogo, carpeta, archivos=archivos, estado=estado)
            nuevas.append(carpeta)
    return nuevas


def imagen_de(pieza: dict) -> str | None:
    """Una foto real si la hay; si no, la vista renderizada; si no, la imagen ilustrativa."""
    if pieza.get("imagen"):
        return pieza["imagen"]
    archivos = pieza.get("archivos") or []
    imagenes = [a for a in archivos if a.lower().endswith(IMAGENES)]
    for criterio in (lambda a: a.rsplit("/", 1)[-1].lower().startswith("foto") and "producto" not in a.lower(),
                     lambda a: a.lower() == "vista.png",
                     lambda a: a.lower().endswith("foto_producto.png")):
        elegida = next((a for a in imagenes if criterio(a)), None)
        if elegida:
            return elegida
    return "vista.png" if not archivos else (imagenes[0] if imagenes else None)


def _href(carpeta: str, archivo: str) -> str:
    return "/".join(quote(p) for p in f"{carpeta}/{archivo}".split("/"))


def _numero(valor) -> str:
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return str(valor)
    texto = f"{v:,.0f}" if v >= 100 else f"{v:,.2f}".rstrip("0").rstrip(".")
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _plata(dato: dict | None) -> str | None:
    if not dato:
        return None
    valor = dato.get("total", dato.get("valor"))
    if valor in (None, ""):
        return None
    moneda = dato.get("moneda") or ""
    return f"{moneda} {_numero(valor)}".strip() if moneda not in ("ARS", "USD") else (
        f"$ {_numero(valor)}" if moneda == "ARS" else f"US$ {_numero(valor)}")


ESTILO = """
:root{--papel:#F5F1E8;--tinta:#1A1A1E;--suave:#4A4740;--borde:#D9D3C7;--acento:#E8590C}
*{box-sizing:border-box}
body{margin:0;background:var(--papel);color:var(--tinta);font:16px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{padding:32px 24px 8px;max-width:1200px;margin:0 auto}
h1{margin:0;font-size:34px;letter-spacing:-.02em}
.sub{margin:6px 0 0;color:var(--suave)}
.controles{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:18px 0 4px}
.controles input{flex:1 1 260px;min-height:44px;padding:8px 14px;border:1.5px solid var(--tinta);border-radius:10px;font:inherit;background:#fff}
.controles button{min-height:44px;padding:8px 14px;border:1.5px solid var(--tinta);border-radius:999px;background:#fff;font:inherit;cursor:pointer}
.controles button[aria-pressed="true"]{background:var(--tinta);color:#fff}
main{max-width:1200px;margin:0 auto;padding:8px 24px 48px}
h2{margin:28px 0 12px;font-size:20px;text-transform:capitalize}
.grilla{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}
article{background:#fff;border:1.5px solid var(--tinta);border-radius:14px;overflow:hidden;display:flex;flex-direction:column}
.imagen{aspect-ratio:4/3;background:#EFEAE0;display:flex;align-items:center;justify-content:center;border-bottom:1.5px solid var(--tinta)}
.imagen img{width:100%;height:100%;object-fit:contain}
.sin{color:var(--suave);font-size:14px}
.cuerpo{padding:12px 14px 14px;display:flex;flex-direction:column;gap:8px}
h3{margin:0;font-size:18px;line-height:1.25}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{font-size:13px;padding:2px 8px;border-radius:6px;border:1px solid var(--borde);background:var(--papel)}
.chip.estado{background:var(--acento);border-color:var(--tinta);color:var(--tinta)}
dl{display:grid;grid-template-columns:auto 1fr;gap:2px 10px;margin:0;font-size:14px}
dt{color:var(--suave)}dd{margin:0}
.archivos{display:flex;flex-wrap:wrap;gap:6px;font-size:13px}
.archivos a{color:var(--tinta);padding:2px 8px;border:1px solid var(--tinta);border-radius:6px;text-decoration:none;font-family:ui-monospace,Consolas,monospace}
.archivos a:hover{background:var(--papel)}
.nota{font-size:14px;color:var(--suave);margin:0}
.ubicacion{font-family:ui-monospace,Consolas,monospace;font-size:12px;color:var(--suave);word-break:break-all}
footer{max-width:1200px;margin:0 auto;padding:0 24px 32px;color:var(--suave);font-size:13px}
.vacio{padding:40px 0;color:var(--suave)}
[hidden]{display:none!important}
@media print{.controles{display:none}article{break-inside:avoid}}
"""

GUION = """
(function(){
  var buscar=document.getElementById('buscar'),filtro='todo';
  var botones=document.querySelectorAll('[data-filtro]');
  function aplicar(){
    var q=(buscar.value||'').toLowerCase().trim();
    document.querySelectorAll('section[data-mes]').forEach(function(s){
      var visibles=0;
      s.querySelectorAll('article').forEach(function(a){
        var ok=(filtro==='todo'||a.getAttribute('data-tipo')===filtro||a.getAttribute('data-estado')===filtro)
          &&(!q||a.getAttribute('data-texto').indexOf(q)>=0);
        a.hidden=!ok; if(ok){visibles++;}
      });
      s.hidden=visibles===0;
    });
  }
  buscar.addEventListener('input',aplicar);
  botones.forEach(function(b){b.addEventListener('click',function(){
    filtro=b.getAttribute('data-filtro');
    botones.forEach(function(o){o.setAttribute('aria-pressed',o===b?'true':'false');});
    aplicar();
  });});
  document.querySelectorAll('.imagen img').forEach(function(i){i.addEventListener('error',function(){
    var s=document.createElement('span');s.className='sin';s.textContent='Sin vista';i.replaceWith(s);
  });});
})();
"""


def _tarjeta(p: dict) -> str:
    e = html.escape
    carpeta = p["carpeta"]
    nombre = p.get("nombre") or carpeta
    imagen = imagen_de(p)
    if imagen:
        img = (f'<img src="{e(_href(carpeta, imagen))}" alt="{e("Vista de " + nombre)}" loading="lazy">')
    else:
        img = '<span class="sin">Sin vista</span>'
    chips = [f'<span class="chip">{e(TIPOS.get(p.get("tipo"), "Pieza"))}</span>']
    if p.get("material"):
        material = p["material"] + (f' {p["color"]}' if p.get("color") else "")
        chips.append(f'<span class="chip">{e(material)}</span>')
    chips.append(f'<span class="chip estado">{e(ESTADOS.get(p.get("estado"), p.get("estado") or ""))}</span>')
    filas = []
    if p.get("medidas_mm"):
        filas.append(("Medidas", " × ".join(_numero(x) for x in p["medidas_mm"]) + " mm"))
    if p.get("tiempo"):
        filas.append(("Tiempo", p["tiempo"]))
    if p.get("gramos"):
        filas.append(("Filamento", f'{_numero(p["gramos"])} g'))
    if _plata(p.get("costo")):
        filas.append(("Costo", _plata(p["costo"])))
    if _plata(p.get("precio")):
        filas.append(("Precio", _plata(p["precio"])))
    if p.get("revision"):
        filas.append(("Revisión", {"aprobado": "aprobada", "advertencia": "con avisos"}.get(p["revision"], p["revision"])))
    dl = "".join(f"<dt>{e(k)}</dt><dd>{e(str(v))}</dd>" for k, v in filas)
    archivos = [a for a in (p.get("archivos") or []) if not a.lower().endswith(IMAGENES) and "/" not in a
                or a.lower().endswith((".gcode", ".gco", ".gcode.3mf"))]
    enlaces = "".join(f'<a href="{e(_href(carpeta, a))}">{e(a.rsplit("/", 1)[-1])}</a>' for a in archivos[:8])
    if p.get("url_tienda"):
        enlaces += f'<a href="{e(p["url_tienda"])}" rel="noopener noreferrer">en la tienda</a>'
    fecha = p.get("fecha") or ""
    texto = " ".join(str(x) for x in (nombre, p.get("material"), p.get("color"), p.get("nota"), carpeta) if x).lower()
    return f"""<article data-tipo="{e(p.get('tipo') or '')}" data-estado="{e(p.get('estado') or '')}" data-texto="{e(texto)}">
<div class="imagen">{img}</div>
<div class="cuerpo">
<h3>{e(nombre)}</h3>
<div class="chips">{''.join(chips)}</div>
{f'<dl>{dl}</dl>' if dl else ''}
{f'<p class="nota">{e(p["nota"])}</p>' if p.get("nota") else ''}
{f'<div class="archivos">{enlaces}</div>' if enlaces else ''}
<div class="ubicacion">{e(carpeta)} · {e(fecha)}</div>
</div>
</article>"""


def generar_html(catalogo: dict, titulo: str = "Mis piezas 3D") -> str:
    e = html.escape
    piezas = sorted(catalogo["piezas"], key=lambda p: (p.get("fecha") or "", p.get("carpeta") or ""), reverse=True)
    secciones = []
    for pieza in piezas:
        fecha = pieza.get("fecha") or ""
        clave = fecha[:7]
        if not secciones or secciones[-1][0] != clave:
            try:
                etiqueta = f"{MESES[int(clave[5:7]) - 1]} {clave[:4]}"
            except (ValueError, IndexError):
                etiqueta = "Sin fecha"
            secciones.append((clave, etiqueta, []))
        secciones[-1][2].append(_tarjeta(pieza))
    cuerpo = "\n".join(
        f'<section data-mes="{e(clave)}"><h2>{e(etiqueta)}</h2><div class="grilla">\n' + "\n".join(tarjetas)
        + "\n</div></section>" for clave, etiqueta, tarjetas in secciones)
    if not piezas:
        cuerpo = '<p class="vacio">Todavía no hay piezas. Cada vez que Claude guarde una, aparece acá.</p>'
    impresiones = sum(1 for p in piezas if p.get("tipo") == "impresion")
    disenos = sum(1 for p in piezas if p.get("tipo") == "diseno")
    actualizado = (catalogo.get("actualizado") or _ahora())[:16].replace("T", " ")
    filtros = [("todo", "Todo"), ("impresion", "Impresiones"), ("diseno", "Diseños"), ("impresa", "Impresas"),
               ("en_tienda", "En la tienda")]
    botones = "".join(f'<button type="button" data-filtro="{f}" aria-pressed="{"true" if f == "todo" else "false"}">'
                      f'{e(t)}</button>' for f, t in filtros)
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src * data: file:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<title>{e(titulo)}</title>
<style>{ESTILO}</style>
</head>
<body>
<header>
<h1>{e(titulo)}</h1>
<p class="sub">{len(piezas)} piezas · {impresiones} impresiones y {disenos} diseños · actualizado el {e(actualizado)}</p>
<div class="controles">
<label for="buscar" hidden>Buscar</label>
<input id="buscar" type="search" placeholder="Buscar por nombre, material o nota" aria-label="Buscar por nombre, material o nota">
{botones}
</div>
</header>
<main>
{cuerpo}
</main>
<footer>Lo arma taller-3d cada vez que Claude guarda una pieza. Abrilo desde tu carpeta de trabajo: las vistas y los archivos se cargan de la carpeta de cada pieza.</footer>
<script>{GUION}</script>
</body>
</html>
"""


def resumen(catalogo: dict, buscar: str | None = None) -> str:
    piezas = catalogo["piezas"]
    if buscar:
        q = buscar.lower()
        piezas = [p for p in piezas if q in " ".join(str(p.get(k) or "") for k in
                                                   ("nombre", "material", "color", "nota", "carpeta")).lower()]
    if not piezas:
        return "No hay piezas" + (f" que coincidan con «{buscar}»." if buscar else " en el catálogo.")
    lineas = [f"{len(piezas)} piezas:"]
    for p in piezas:
        datos = [ESTADOS.get(p.get("estado"), p.get("estado") or "")]
        if p.get("material"):
            datos.append(p["material"])
        if p.get("tiempo"):
            datos.append(p["tiempo"])
        if _plata(p.get("precio")):
            datos.append("precio " + _plata(p["precio"]))
        lineas.append(f"- {p.get('fecha', '')} {p.get('nombre', '')} ({', '.join(d for d in datos if d)}) → {p['carpeta']}")
    return "\n".join(lineas)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="accion", required=True)

    a = sub.add_parser("agregar", help="agrega o actualiza una pieza")
    a.add_argument("--catalogo", required=True, type=Path)
    a.add_argument("--carpeta", required=True, help="carpeta de la pieza, relativa a la carpeta de trabajo")
    a.add_argument("--nombre")
    a.add_argument("--tipo", choices=sorted(TIPOS))
    a.add_argument("--fecha", help="AAAA-MM-DD (si no, la del nombre de la carpeta)")
    a.add_argument("--material")
    a.add_argument("--color")
    a.add_argument("--informe-gcode")
    a.add_argument("--informe-stl")
    a.add_argument("--producto", help="producto.json de /publicar")
    a.add_argument("--archivos", nargs="*", default=[], help="archivos de la carpeta de la pieza (relativos a ella)")
    a.add_argument("--imagen", help="imagen principal (relativa a la carpeta de la pieza)")
    a.add_argument("--estado", choices=sorted(ESTADOS))
    a.add_argument("--nota")
    a.add_argument("--url-tienda")
    a.add_argument("--moneda", help="moneda del precio, si no sale del costo")

    d = sub.add_parser("desde-listado", help="suma las piezas que ya estaban en la carpeta de trabajo")
    d.add_argument("--catalogo", required=True, type=Path)
    d.add_argument("--listado", required=True, type=Path, help="JSON de device_list_dir (recursive) o lista de rutas")

    h = sub.add_parser("html", help="arma catalogo.html")
    h.add_argument("--catalogo", required=True, type=Path)
    h.add_argument("--salida", required=True, type=Path)
    h.add_argument("--titulo", default="Mis piezas 3D")

    r = sub.add_parser("resumen", help="lista las piezas en texto")
    r.add_argument("--catalogo", required=True, type=Path)
    r.add_argument("--buscar")

    args = ap.parse_args(argv)
    catalogo = cargar(args.catalogo)
    if args.accion == "agregar":
        extra = datos_de_informes(_leer_json(args.informe_gcode), _leer_json(args.informe_stl),
                                  _leer_json(args.producto))
        if args.estado:
            extra["estado"] = args.estado
        if args.moneda and extra.get("precio"):
            extra["precio"]["moneda"] = args.moneda
        pieza = agregar(catalogo, args.carpeta, nombre=args.nombre, tipo=args.tipo, fecha=args.fecha,
                        material=args.material or extra.pop("material", None), color=args.color,
                        archivos=args.archivos, imagen=args.imagen, nota=args.nota, url_tienda=args.url_tienda,
                        **{k: v for k, v in extra.items() if k != "material"})
        guardar(args.catalogo, catalogo)
        print(f"Catálogo: {pieza['nombre']} ({ESTADOS.get(pieza['estado'], pieza['estado'])}) — "
              f"{len(catalogo['piezas'])} piezas en total.")
    elif args.accion == "desde-listado":
        listado = json.loads(args.listado.read_text(encoding="utf-8"))
        nuevas = desde_listado(catalogo, listado)
        guardar(args.catalogo, catalogo)
        print(f"Sumé {len(nuevas)} piezas que ya estaban: {', '.join(nuevas) if nuevas else 'ninguna'}.")
    elif args.accion == "html":
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        args.salida.write_text(generar_html(catalogo, args.titulo), encoding="utf-8")
        print(f"Página: {args.salida} ({len(catalogo['piezas'])} piezas).")
    else:
        print(resumen(catalogo, args.buscar))


if __name__ == "__main__":
    main()
