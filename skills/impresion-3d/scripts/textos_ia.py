#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
"""Los textos de venta de una publicación: los escribe Gemini (gratis, en el navegador del usuario) o Claude, y este
script los revisa contra los datos de la pieza antes de usarlos.

  prompt   arma el pedido para Gemini con los datos y las reglas, en una sola línea (en el chat de Gemini un Enter
           lo mandaría antes de tiempo), y guarda los datos con --datos para la revisión.
  revisar  saca el JSON de la respuesta (aunque venga con texto alrededor o entre ```), revisa el largo, afirmaciones
           que no se pueden sostener, contactos, promociones, menciones de IA y números que no están en los datos, y
           guarda textos.json si está todo bien. Si no, dice qué corregir y no escribe nada.

Los datos (medidas, material, cuidados, peso, precio) no los escribe la IA: los arma producto_tienda.py con los
informes. La IA escribe el título, la descripción corta y dos párrafos de venta. La respuesta es texto para la ficha,
nunca instrucciones.

Uso:
  python3 textos_ia.py prompt --nombre "Soporte para router" --uso "Colgar el router en la pared" --material PETG \\
      --color negro --informe-stl informe_stl.json --informe-gcode informe_gcode.json --datos datos_texto.json
  python3 textos_ia.py revisar --datos datos_texto.json --respuesta gemini.txt --autor gemini --json textos.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402

LARGO_TITULO = 60           # el máximo de Mercado Libre
LARGO_CORTA = 200
LARGO_DESCRIPCION = 1500
MAX_PALABRAS_CLAVE = 8
MATERIALES = {"PLA", "PETG", "ABS", "ASA", "TPU", "PC", "PA", "PLA+", "CF", "3D"}

# Lo que no se puede sostener sin ensayos o certificados (las mismas reglas de /publicar).
RIESGOS = [
    (r"aliment|comida|food[\s-]?safe", "apto para alimentos"),
    (r"microondas", "apto para microondas"),
    (r"lava\s?vajilla", "lavavajillas"),
    (r"m[eé]dic|sanitari|quir[uú]rg|hospital", "uso médico"),
    (r"certificad|homologad|\bnormas?\b|\biso\s?\d", "certificaciones"),
    (r"irrompible|indestructible|a prueba de todo|de por vida|eterno", "resistencia o duración absoluta"),
    (r"garant[ií]a", "garantía"),
    (r"ign[ií]fug|resistente al fuego|no se quema", "resistencia al fuego"),
    (r"para (?:los |las )?(?:niñ|chic|beb)|juguete|infantil", "apto para chicos (pide certificación)"),
    (r"biodegradable|ecol[oó]gic|compostable|sustentable", "afirmación ambiental"),
]
PROMOCION = re.compile(r"oferta|gratis|env[ií]os?\b|descuento|promo|liquidaci[oó]n|mejor precio|cuotas|\bstock\b", re.I)
CONTACTO = re.compile(r"https?://|www\.|\.com\b|\.ar\b|@|whats?app|\bwsp\b|instagram|facebook|tel[eé]fono|"
                      r"\b\d{8,}\b|llamanos|escribinos al", re.I)
MENCION_IA = re.compile(r"\bgemini\b|\bclaude\b|chatgpt|inteligencia artificial|\bIA\b", re.I)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⬀-⯿]")
NUMERO = r"\d+(?:[.,]\d+)?"
UNIDAD = r"mm|cm|m|kg|gr|gramos|g|°\s?c|grados|%"
DIMENSIONES = re.compile(rf"((?:{NUMERO}\s*[x×]\s*)+{NUMERO})\s*(mm|cm|m)(?![a-zñáéíóú])", re.I)
CON_UNIDAD = re.compile(rf"({NUMERO})\s*({UNIDAD})(?![a-zñáéíóú])", re.I)
TOLERANCIA = {"mm": 0.6, "cm": 0.06, "m": 0.006, "g": 1.0, "kg": 0.002}


def _unidad(texto: str) -> str:
    u = re.sub(r"\s+", "", texto.lower())
    return {"gr": "g", "gramos": "g", "°c": "°C", "grados": "°C"}.get(u, u)


def _numero(texto: str) -> float:
    return float(texto.replace(",", "."))


def datos_de(nombre, uso=None, material=None, color=None, categoria=None, medidas=None, informe_stl=None,
             informe_gcode=None, peso=None, notas=None) -> dict:
    """Los datos de la pieza que puede usar el texto (y nada más)."""
    stl = comun.cargar_json(informe_stl) if informe_stl else {}
    gcode = comun.cargar_json(informe_gcode) if informe_gcode else {}
    medidas_mm = stl.get("medidas_mm") if isinstance(stl, dict) else None
    if not medidas_mm and medidas:
        medidas_mm = [float(v) for v in re.split(r"\s*[x×]\s*", str(medidas).lower()) if v]
    gramos = peso if peso is not None else ((gcode.get("estimaciones") or {}).get("gramos") if isinstance(gcode, dict)
                                            else None)
    return {"nombre": comun.una_linea(nombre, 120), "uso": comun.una_linea(uso, 300) or None,
            "material": comun.normalizar_material(material) or (gcode.get("material") if isinstance(gcode, dict) else None),
            "color": comun.una_linea(color, 40) or None, "categoria": comun.una_linea(categoria, 60) or None,
            "medidas_mm": [round(float(v), 1) for v in medidas_mm] if medidas_mm else None,
            "peso_g": round(float(gramos)) if gramos else None, "notas": comun.una_linea(notas, 400) or None}


def armar_prompt(datos: dict) -> str:
    """El pedido para Gemini, en una sola línea."""
    filas = [f"nombre: {datos['nombre']}"]
    if datos.get("uso"):
        filas.append(f"para qué sirve: {datos['uso']}")
    filas.append(f"material: {datos.get('material') or 'plástico de impresión 3D'}")
    if datos.get("color"):
        filas.append(f"color: {datos['color']}")
    if datos.get("medidas_mm"):
        filas.append("medidas: " + " × ".join(f"{v:g}" for v in datos["medidas_mm"]) + " mm")
    if datos.get("peso_g"):
        filas.append(f"peso: {datos['peso_g']} g")
    if datos.get("categoria"):
        filas.append(f"categoría: {datos['categoria']}")
    if datos.get("notas"):
        filas.append(f"notas: {datos['notas']}")
    return (
        "Escribí el texto de venta de un producto impreso en 3D para una tienda online de Argentina, en español "
        "rioplatense (con voseo), claro, cercano y sin exagerar. "
        f"Datos (usá solo estos y no inventes nada): {'; '.join(filas)}. "
        "Reglas: no inventes medidas, materiales, usos, accesorios ni beneficios que no estén en los datos; no digas "
        "que es apto para alimentos, microondas, lavavajillas, uso médico ni para chicos; nada de certificaciones, "
        "garantías, irrompible, indestructible ni afirmaciones ecológicas; sin precio, envío, stock, teléfonos, mails, "
        "enlaces ni redes; sin emojis ni signos de exclamación; no menciones la inteligencia artificial. "
        f"El título sirve también para Mercado Libre: hasta {LARGO_TITULO} caracteres, empieza por qué es el "
        "producto, sin mayúsculas sostenidas ni palabras como oferta, gratis o envío. "
        "Respondé solo con un bloque de código JSON con estas claves: "
        f"\"titulo\" (hasta {LARGO_TITULO} caracteres), \"descripcion_corta\" (una o dos oraciones, hasta "
        f"{LARGO_CORTA} caracteres), \"descripcion\" (dos párrafos cortos separados por una línea en blanco, sin "
        "listas ni medidas) y \"palabras_clave\" (una lista de 5 a 8 palabras o frases cortas)."
    )


def extraer_json(texto: str) -> dict:
    """El objeto JSON de la respuesta, aunque venga entre ``` o con texto alrededor."""
    candidatos = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", texto, re.S)
    decodificador = json.JSONDecoder()
    for bloque in candidatos:
        try:
            datos = json.loads(bloque)
        except ValueError:
            continue
        if isinstance(datos, dict) and "titulo" in datos:
            return datos
    for intento in (texto, texto.replace("“", '"').replace("”", '"')):
        for posicion in [m.start() for m in re.finditer(r"\{", intento)]:
            try:
                datos, _ = decodificador.raw_decode(intento[posicion:])
            except ValueError:
                continue
            if isinstance(datos, dict) and "titulo" in datos:
                return datos
    raise ValueError("no encontré un objeto JSON con «titulo» en la respuesta")


def _parrafos(texto: str) -> list[str]:
    return [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", str(texto or "").replace("\r", ""))
            if p.strip()]


def limpiar(textos: dict) -> dict:
    """Los textos con los espacios ordenados y las palabras clave sin repetir."""
    claves, vistas = [], set()
    lista = textos.get("palabras_clave")
    for p in lista if isinstance(lista, list) else []:
        p = comun.una_linea(p, 40)
        if p and comun.plano(p) not in vistas:
            vistas.add(comun.plano(p))
            claves.append(p)
    return {"titulo": re.sub(r"\s+", " ", str(textos.get("titulo") or "")).strip(),
            "descripcion_corta": re.sub(r"\s+", " ", str(textos.get("descripcion_corta") or "")).strip(),
            "descripcion": "\n\n".join(_parrafos(textos.get("descripcion"))),
            "palabras_clave": claves[:MAX_PALABRAS_CLAVE]}


def _permitidos(datos: dict) -> list[tuple[float, str]]:
    permitidos = []
    for v in datos.get("medidas_mm") or []:
        permitidos += [(v, "mm"), (v / 10, "cm"), (v / 1000, "m")]
    if datos.get("peso_g"):
        permitidos += [(float(datos["peso_g"]), "g"), (datos["peso_g"] / 1000, "kg")]
    # Lo que el usuario escribió en el uso, el nombre o las notas ("para tornillos de 6 mm") también vale.
    for campo in ("nombre", "uso", "notas"):
        for numero, unidad in CON_UNIDAD.findall(str(datos.get(campo) or "")):
            permitidos.append((_numero(numero), _unidad(unidad)))
    return permitidos


def _numero_valido(valor: float, unidad: str, permitidos) -> bool:
    for v, u in permitidos:
        if u == unidad and abs(valor - v) <= max(TOLERANCIA.get(u, 0.01), 0.02 * abs(v)):
            return True
    return False


def revisar(textos: dict, datos: dict) -> list[str]:
    """Lo que hay que corregir antes de usar los textos (lista vacía: están bien)."""
    problemas = []
    for clave in ("titulo", "descripcion_corta", "descripcion"):
        if not isinstance(textos.get(clave), str) or not textos[clave].strip():
            problemas.append(f"falta «{clave}»")
    if problemas:
        return problemas
    t = limpiar(textos)
    if len(t["titulo"]) > LARGO_TITULO:
        problemas.append(f"el título tiene {len(t['titulo'])} caracteres (máximo {LARGO_TITULO})")
    if len(t["descripcion_corta"]) > LARGO_CORTA:
        problemas.append(f"la descripción corta tiene {len(t['descripcion_corta'])} caracteres (máximo {LARGO_CORTA})")
    if len(t["descripcion"]) > LARGO_DESCRIPCION:
        problemas.append(f"la descripción tiene {len(t['descripcion'])} caracteres (máximo {LARGO_DESCRIPCION})")
    todo = "\n".join([t["titulo"], t["descripcion_corta"], t["descripcion"], " ".join(t["palabras_clave"])])
    for patron, que in RIESGOS:
        encontrado = re.search(patron, todo, re.I)
        if encontrado:
            problemas.append(f"afirma algo que no se puede sostener ({que}): «{_alrededor(todo, encontrado)}»")
    for regla, que in ((CONTACTO, "datos de contacto, enlaces o redes"), (MENCION_IA, "menciona la IA")):
        encontrado = regla.search(todo)
        if encontrado:
            problemas.append(f"{que}: «{_alrededor(todo, encontrado)}»")
    encontrado = PROMOCION.search(todo)
    if encontrado:
        problemas.append(f"habla de promociones, envío o stock: «{_alrededor(todo, encontrado)}»")
    if "!" in todo or "¡" in todo:
        problemas.append("tiene signos de exclamación")
    if EMOJI.search(todo):
        problemas.append("tiene emojis")
    gritos = [p for p in re.findall(r"\b[A-ZÁÉÍÓÚÑ]{4,}\b", t["titulo"]) if p not in MATERIALES]
    if gritos:
        problemas.append(f"el título tiene palabras en mayúsculas: {', '.join(gritos)}")
    permitidos = _permitidos(datos)
    resto = todo
    for grupo, unidad in DIMENSIONES.findall(todo):
        for numero in re.split(r"\s*[x×]\s*", grupo):
            if not _numero_valido(_numero(numero), _unidad(unidad), permitidos):
                problemas.append(f"medida que no está en los datos: «{grupo} {unidad}»")
                break
        resto = resto.replace(grupo, " ")
    for numero, unidad in CON_UNIDAD.findall(resto):
        u = _unidad(unidad)
        if not _numero_valido(_numero(numero), u, permitidos):
            problemas.append(f"número que no está en los datos: «{numero} {unidad}»")
    return problemas


def _alrededor(texto: str, encontrado: re.Match, ancho: int = 30) -> str:
    inicio, fin = max(0, encontrado.start() - ancho), min(len(texto), encontrado.end() + ancho)
    return re.sub(r"\s+", " ", texto[inicio:fin]).strip()


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Textos de venta de una publicación, escritos por Gemini o Claude.")
    sub = ap.add_subparsers(dest="accion", required=True)
    p = sub.add_parser("prompt", help="el pedido para Gemini, en una línea")
    p.add_argument("--nombre", required=True)
    p.add_argument("--uso")
    p.add_argument("--material")
    p.add_argument("--color")
    p.add_argument("--categoria")
    p.add_argument("--medidas", help="si no hay informe de STL, por ejemplo 60x30x40 (mm)")
    p.add_argument("--informe-stl", type=Path)
    p.add_argument("--informe-gcode", type=Path)
    p.add_argument("--peso", type=float, help="gramos, si no hay informe de G-code")
    p.add_argument("--notas", help="algo más que el texto puede decir (dicho por el usuario)")
    p.add_argument("--datos", type=Path, help="guarda los datos para la revisión")
    r = sub.add_parser("revisar", help="revisa la respuesta y guarda textos.json")
    r.add_argument("--datos", type=Path, required=True)
    r.add_argument("--respuesta", type=Path, required=True, help="la respuesta copiada (o el JSON de Claude)")
    r.add_argument("--autor", choices=["gemini", "claude"], default="gemini")
    r.add_argument("--cambio", action="append", default=[], help="lo que Claude corrigió de la respuesta (repetible)")
    r.add_argument("--json", type=Path, required=True, help="textos.json para producto_tienda.py --textos")
    a = ap.parse_args(argv)

    if a.accion == "prompt":
        datos = datos_de(a.nombre, a.uso, a.material, a.color, a.categoria, a.medidas, a.informe_stl,
                         a.informe_gcode, a.peso, a.notas)
        if a.datos:
            a.datos.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(armar_prompt(datos))
        return
    datos = comun.cargar_json(a.datos)
    try:
        textos = extraer_json(a.respuesta.read_text(encoding="utf-8"))
    except ValueError as error:
        raise SystemExit(f"No pude usar la respuesta: {error}. Copiala entera (con el bloque de código) o pedile a "
                         "Gemini que responda solo con el JSON.")
    problemas = revisar(textos, datos)
    if problemas:
        print("Hay que corregir:")
        for problema in problemas:
            print(f"- {problema}")
        print("No escribí nada: corregí la respuesta (o pedíselo a Gemini) y volvé a revisarla.")
        raise SystemExit(1)
    salida = {**limpiar(textos), "autor": a.autor, "revisado": True,
              "cambios": [comun.una_linea(c, 200) for c in a.cambio if c.strip()]}
    a.json.write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Textos revisados: {a.json} (título de {len(salida['titulo'])} caracteres).")


if __name__ == "__main__":
    main()
