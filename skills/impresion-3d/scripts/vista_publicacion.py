#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
"""Vista previa de la publicación: la página del producto como se vería en la tienda del usuario (galería, título,
precio, descripción y ficha técnica) y, aparte, lo que conviene revisar antes de publicar (fotos, título para
Mercado Libre, precio por canal, quién escribió el texto). Sale de publicacion.json (producto_tienda.py).

  modo archivo  vista-previa.html en la carpeta producto/ de la pieza (fotos por ruta relativa); los botones copian
                el pedido.
  modo claude   la página que Claude publica en claude.ai, al costado del chat (fotos en fotos/); los botones le
                mandan el pedido a Claude.

Uso:
  python3 vista_publicacion.py --publicacion producto/publicacion.json --salida producto/vista-previa.html
  python3 vista_publicacion.py --publicacion publicacion.json --modo claude --prefijo-fotos fotos/ \\
      --salida vista-claude/index.html
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

LARGO_TITULO_ML = 60

ESTILO = """
:root{--tinta:#1d1d1f;--suave:#5f5f66;--borde:#e3e3e8;--acento:#0b6e4f;--nota:#fff7e6;--nota-borde:#e0b44c}
*{box-sizing:border-box}
body{margin:0;background:#f4f4f6;color:var(--tinta);font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.banda{background:var(--tinta);color:#fff;font-size:13px;padding:8px 16px;text-align:center}
.tienda{max-width:1080px;margin:16px auto;background:#fff;border:1px solid var(--borde);border-radius:12px;padding:20px}
.producto{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:28px}
@media (max-width:720px){.producto{grid-template-columns:1fr}.tienda{margin:8px;padding:14px}}
.principal{aspect-ratio:1;border:1px solid var(--borde);border-radius:10px;overflow:hidden;background:#fff;display:flex;align-items:center;justify-content:center}
.principal img{width:100%;height:100%;object-fit:contain}
.sin-foto{color:var(--suave);font-size:14px}
.miniaturas{display:flex;gap:8px;margin-top:8px;flex-wrap:wrap}
.miniaturas button{width:64px;height:64px;padding:0;border:1px solid var(--borde);border-radius:8px;background:#fff;cursor:pointer;overflow:hidden}
.miniaturas button[aria-pressed="true"]{border:2px solid var(--tinta)}
.miniaturas img{width:100%;height:100%;object-fit:contain}
.ilustrativa{font-size:12px;color:var(--suave);margin:6px 0 0}
.categoria{font-size:13px;color:var(--suave);margin:0}
h1{font-size:26px;line-height:1.2;margin:4px 0 8px}
.precio{font-size:30px;font-weight:700;margin:8px 0}
.precio.sin{font-size:18px;color:#b3261e;font-weight:600}
.corta{margin:0 0 14px}
.comprar{width:100%;min-height:48px;border:0;border-radius:10px;background:var(--acento);color:#fff;font:inherit;font-weight:600;cursor:not-allowed}
.descripcion,.ficha{margin-top:24px;border-top:1px solid var(--borde);padding-top:16px}
h2{font-size:19px;margin:0 0 10px}
h3{font-size:16px;margin:14px 0 6px}
.descripcion ul{padding-left:20px;margin:0}
.descripcion li{margin:2px 0}
.aviso3d{font-size:13px;color:var(--suave)}
table{border-collapse:collapse;width:100%;font-size:15px}
th,td{text-align:left;padding:8px;border-bottom:1px solid var(--borde);vertical-align:top}
th{color:var(--suave);font-weight:500;width:40%}
aside{max-width:1080px;margin:0 auto 32px;background:var(--nota);border:1.5px solid var(--nota-borde);border-radius:12px;padding:16px 20px}
@media (max-width:720px){aside{margin:0 8px 24px}}
aside h2{font-size:18px}
aside ul{list-style:none;padding:0;margin:0;display:grid;gap:8px}
aside li{display:grid;grid-template-columns:22px 1fr;gap:6px;font-size:15px}
.marca{font-weight:700;text-align:center}
.ok{color:#0b6e4f}.mal{color:#b3261e}.ojo{color:#b45309}
.botones{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
.botones button{min-height:44px;padding:8px 16px;border:1.5px solid var(--tinta);border-radius:999px;background:#fff;color:var(--tinta);font:inherit;cursor:pointer}
.botones button.aprobar{background:var(--tinta);color:#fff}
.botones button:disabled{opacity:.55;cursor:progress}
#aviso{font-size:14px;color:var(--suave);margin:10px 0 0}
#aviso:empty{display:none}
.solo-claude{display:none}
body.con-claude .solo-claude{display:inline-block}
"""

GUION = """
(function(){
  // Galería: tocar una miniatura la muestra grande.
  var principal=document.getElementById('principal'),mini=document.querySelectorAll('.miniaturas button');
  mini.forEach(function(b){b.addEventListener('click',function(){
    if(principal){principal.src=b.getAttribute('data-src');principal.alt=b.getAttribute('data-alt')||principal.alt;}
    mini.forEach(function(o){o.setAttribute('aria-pressed',o===b?'true':'false');});
  });});
  document.querySelectorAll('img').forEach(function(i){i.addEventListener('error',function(){
    var s=document.createElement('span');s.className='sin-foto';s.textContent='Sin foto';i.replaceWith(s);
  });});
  // Botones: en claude.ai le mandan el pedido a Claude (despierta al chat); si no, lo copian para pegarlo.
  var aviso=document.getElementById('aviso'),com=null;
  function decir(t){aviso.textContent=t;}
  function copiar(texto){
    function mostrar(){decir('Copiá este pedido y pegalo en el chat con Claude: '+texto);}
    try{navigator.clipboard.writeText(texto).then(function(){decir('Pedido copiado: pegalo en el chat con Claude.');},mostrar);}
    catch(e){mostrar();}
  }
  function pedir(el,texto){
    if(!com){copiar(texto);return;}
    el.disabled=true;decir('Enviando a Claude…');
    com.canSendToClaude().then(function(estado){
      if(estado!=='available'){copiar(texto);return;}
      return com.anchorFor(el.closest('aside')).then(function(a){return com.sendToClaude({anchor:a,text:texto});})
        .then(function(){decir('Enviado. Claude lo hace y te contesta en el chat.');},
              function(err){decir('No se envió ('+((err&&err.code)||'error')+'). Si querés, pegalo en el chat: '+texto);});
    }).catch(function(){copiar(texto);}).then(function(){el.disabled=false;});
  }
  document.querySelectorAll('[data-pedido]').forEach(function(b){
    b.addEventListener('click',function(){pedir(b,b.getAttribute('data-pedido'));});
  });
  document.querySelectorAll('[data-comentar]').forEach(function(b){b.addEventListener('click',function(){
    if(com){com.openComposer({element:b.closest('aside')}).catch(function(){});}
  });});
  if(window.claude&&typeof window.claude.use==='function'){
    window.claude.use('comments').then(function(c){
      if(!c){return;}
      return c.canSendToClaude().then(function(estado){
        com=c;document.body.classList.toggle('con-claude',estado==='available');
      });
    }).catch(function(){});
  }
})();
"""


def plata(valor, moneda: str | None = "ARS") -> str | None:
    """12300 → "$ 12.300" (US$ si la moneda es USD)."""
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return None
    entero = abs(v - round(v)) < 1e-9
    texto = (f"{v:,.0f}" if entero else f"{v:,.2f}").replace(",", "X").replace(".", ",").replace("X", ".")
    return ("US$ " if (moneda or "ARS").upper() == "USD" else "$ ") + texto


def _numero(v) -> str:
    return f"{float(v):g}".replace(".", ",")


def _foto(ruta: str, modo: str, prefijo: str) -> str | None:
    """La ruta de la foto en la página: tal cual en el archivo (relativa a producto/), y en claude.ai el nombre del
    archivo dentro de la carpeta de fotos publicada. Nada de rutas absolutas, esquemas ni comillas."""
    ruta = str(ruta or "").replace("\\", "/")
    if not ruta or re.search(r"[\x00-\x1f\"'<>]|^[a-z][a-z0-9+.-]*:|^/", ruta, re.I):
        return None
    return prefijo + ruta.rsplit("/", 1)[-1] if modo == "claude" else ruta


def revisar(pub: dict) -> list[tuple[str, str]]:
    """Lo que conviene revisar antes de publicar: (estado ok | ojo | mal, texto)."""
    items = []
    fotos, reales = pub.get("fotos") or [], int(pub.get("fotos_reales") or 0)
    if not fotos:
        items.append(("mal", "No hay fotos: sacá fotos de la pieza o pedile a Claude las fotos de producto con Blender."))
    elif not reales:
        items.append(("ojo", "Las fotos son ilustrativas (renderizadas). Antes de publicar, sumá fotos reales de la "
                             "pieza impresa como imagen principal."))
    else:
        items.append(("ok", f"{reales} foto{'s' if reales != 1 else ''} real{'es' if reales != 1 else ''} de la pieza."))
    titulo = str(pub.get("titulo_ml") or (pub.get("producto") or {}).get("name") or "")
    items.append(("ok" if len(titulo) <= LARGO_TITULO_ML else "mal",
                  f"Título si la publicás en Mercado Libre: «{titulo}» ({len(titulo)}/{LARGO_TITULO_ML} caracteres)."))
    if fotos:
        primera = str(fotos[0]).rsplit("/", 1)[-1]
        if primera.startswith("producto-1-principal"):
            items.append(("ok", "La primera foto tiene fondo blanco, como pide Mercado Libre."))
        else:
            items.append(("ojo", "En Mercado Libre la primera foto tiene que tener fondo blanco puro, sin textos: "
                                 "usá producto-1-principal.jpg o una foto real con fondo blanco."))
    precio = pub.get("precio") or {}
    moneda = precio.get("moneda") or "ARS"
    if not (pub.get("producto") or {}).get("regular_price"):
        faltan = ", ".join(precio.get("faltan_datos") or []) or "datos de costos"
        items.append(("mal", f"Precio a definir: faltan {faltan}."))
    else:
        if precio.get("faltan_datos"):
            items.append(("ojo", "El precio sale sin " + ", ".join(precio["faltan_datos"])
                                 + ": cargalos para que sea el real."))
        for clave, canal in (precio.get("canales") or {}).items():
            nombre = canal.get("nombre") or clave
            if "error" in canal:
                items.append(("mal", f"{nombre}: {canal['error']}"))
                continue
            negativa = (canal.get("ganancia") or 0) < 0
            items.append(("mal" if negativa else "ok",
                          f"{nombre}: {plata(canal.get('precio'), moneda)}, comisiones {plata(canal.get('comisiones'), moneda)}, "
                          f"te queda {plata(canal.get('te_queda'), moneda)}, ganancia {plata(canal.get('ganancia'), moneda)} "
                          f"({_numero(canal.get('margen_real_pct') or 0)} %)" + (": pierde plata" if negativa else "") + "."))
    textos = pub.get("textos") or {}
    if textos.get("autor") == "gemini":
        texto = "El texto lo escribió Gemini (gratis) y Claude lo revisó contra los datos de la pieza."
    elif textos.get("autor") == "claude":
        texto = "El texto lo escribió Claude, revisado contra los datos de la pieza."
    else:
        texto = "El texto sale de la plantilla: para qué sirve, medidas, material y cuidados."
    cambios = [c for c in textos.get("cambios") or [] if isinstance(c, str) and c.strip()]
    items.append(("ok", texto + (f" Corrigió: {'; '.join(cambios)}." if cambios else "")))
    items.append(("ok", "Se carga como borrador: no se ve en la tienda hasta que lo publiques vos."))
    return items


def generar(pub: dict, modo: str = "archivo", prefijo_fotos: str = "fotos/") -> str:
    if modo not in ("archivo", "claude"):
        raise ValueError(f"Modo desconocido: {modo}")
    e = html.escape
    p = pub.get("producto") or {}
    nombre = str(p.get("name") or "Producto")
    precio = pub.get("precio") or {}
    moneda = precio.get("moneda") or "ARS"
    tienda = pub.get("tienda") or {}
    sitio = urlparse(str(tienda.get("url") or "")).hostname if tienda.get("url") else None
    fotos = [f for f in (_foto(x, modo, prefijo_fotos) for x in pub.get("fotos") or []) if f]
    ilustrativas = bool(fotos) and not int(pub.get("fotos_reales") or 0)

    if fotos:
        principal = f'<img id="principal" src="{e(fotos[0])}" alt="{e(nombre)}">'
        miniaturas = "".join(
            f'<button type="button" data-src="{e(f)}" data-alt="{e(nombre)} (foto {i + 1})" '
            f'aria-pressed="{"true" if i == 0 else "false"}" aria-label="Ver la foto {i + 1}">'
            f'<img src="{e(f)}" alt="" loading="lazy"></button>' for i, f in enumerate(fotos)) if len(fotos) > 1 else ""
    else:
        principal, miniaturas = '<span class="sin-foto">Sin fotos todavía</span>', ""
    precio_html = (f'<p class="precio">{e(plata(p["regular_price"], moneda) or "")}</p>' if p.get("regular_price")
                   else '<p class="precio sin">Precio a definir</p>')
    medidas = pub.get("medidas_mm")
    filas = []
    if medidas:
        filas.append(("Medidas", " × ".join(_numero(v) for v in medidas) + " mm"))
    if pub.get("material"):
        filas.append(("Material", pub["material"]))
    if pub.get("color"):
        filas.append(("Color", pub["color"]))
    if pub.get("gramos"):
        filas.append(("Peso aproximado", f"{float(pub['gramos']):.0f} g"))
    if p.get("sku"):
        filas.append(("SKU", p["sku"]))
    if pub.get("categoria"):
        filas.append(("Categoría", pub["categoria"]))
    ficha = "".join(f"<tr><th>{e(str(k))}</th><td>{e(str(v))}</td></tr>" for k, v in filas)
    parrafos = "".join(f"<p>{e(str(x))}</p>" for x in pub.get("parrafos") or [])
    puntos = "".join(f"<li>{e(str(x))}</li>" for x in pub.get("puntos") or [])
    marcas = {"ok": "✓", "ojo": "!", "mal": "✗"}
    revision = "".join(f'<li><span class="marca {e(estado)}" aria-hidden="true">{marcas[estado]}</span>'
                       f'<span>{e(texto)}</span></li>' for estado, texto in revisar(pub))
    cual = comun.una_linea(nombre, 80)
    carpeta = comun.una_linea(pub.get("carpeta"), 160)
    pedido = (f"Desde la vista previa: aprobé la publicación de «{cual}»" + (f" ({carpeta})" if carpeta else "")
              + ". Cargala como borrador en la tienda.")
    politica = "" if modo == "claude" else (
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src * data: file:; '
        'style-src \'unsafe-inline\'; script-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">\n')
    nota_modo = ("Para cambiar algo, tocá «Cambiar algo…» o decíselo a Claude en el chat." if modo == "claude" else
                 "El botón copia el pedido para que lo pegues en el chat con Claude; para cambiar algo, decíselo ahí.")
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{politica}<title>{e("Vista previa: " + nombre)}</title>
<style>{ESTILO}</style>
</head>
<body>
<div class="banda">Vista previa · borrador sin publicar{(" · así se vería en <strong>" + e(sitio) + "</strong>") if sitio else ""}</div>
<main class="tienda">
<section class="producto">
<div class="galeria">
<div class="principal">{principal}</div>
{f'<div class="miniaturas">{miniaturas}</div>' if miniaturas else ''}
{'<p class="ilustrativa">Imágenes ilustrativas</p>' if ilustrativas else ''}
</div>
<div class="compra">
{f'<p class="categoria">{e(str(pub["categoria"]))}</p>' if pub.get("categoria") else ''}
<h1>{e(nombre)}</h1>
{precio_html}
<p class="corta">{e(str(p.get("short_description") or ""))}</p>
<button type="button" class="comprar" disabled>Agregar al carrito</button>
</div>
</section>
<section class="descripcion">
<h2>Descripción</h2>
{parrafos}
<h3>Características</h3>
<ul>{puntos}</ul>
<p class="aviso3d">{e(str(pub.get("aviso_3d") or ""))}</p>
</section>
{f'<section class="ficha"><h2>Ficha técnica</h2><table>{ficha}</table></section>' if ficha else ''}
</main>
<aside aria-label="Antes de publicar">
<h2>Antes de publicar</h2>
<ul>{revision}</ul>
<div class="botones">
<button type="button" class="aprobar" data-pedido="{e(pedido)}">Aprobar y cargar como borrador</button>
<button type="button" class="solo-claude" data-comentar>Cambiar algo…</button>
</div>
<p id="aviso" role="status" aria-live="polite"></p>
<p class="aviso3d">{e(nota_modo)}</p>
</aside>
<script>{GUION}</script>
</body>
</html>
"""


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Vista previa de la publicación de una pieza.")
    ap.add_argument("--publicacion", type=Path, required=True, help="publicacion.json de producto_tienda.py")
    ap.add_argument("--salida", type=Path, required=True)
    ap.add_argument("--modo", choices=["archivo", "claude"], default="archivo")
    ap.add_argument("--prefijo-fotos", default="fotos/", help="(modo claude) carpeta de las fotos en la página")
    a = ap.parse_args(argv)
    pub = comun.cargar_json(a.publicacion)
    if not isinstance(pub, dict) or not isinstance(pub.get("producto"), dict):
        raise SystemExit(f"{a.publicacion} no es un publicacion.json de producto_tienda.py.")
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    a.salida.write_text(generar(pub, a.modo, a.prefijo_fotos), encoding="utf-8")
    fotos = [f for f in (_foto(x, a.modo, a.prefijo_fotos) for x in pub.get("fotos") or []) if f]
    print(f"Vista previa: {a.salida} ({len(fotos)} fotos" + (f", en {a.prefijo_fotos}" if a.modo == "claude" else "")
          + ").")


if __name__ == "__main__":
    main()
