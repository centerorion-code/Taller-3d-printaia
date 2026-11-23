#!/usr/bin/env python3
"""Une un taller que quedó en otra carpeta con el de `Documentos/Taller 3D` (desde la 0.1.34, la única carpeta de trabajo).

No mueve archivos: arma la configuración, el catálogo y el historial unidos, y dice qué carpetas hay que mover.

    python3 -I mudar_taller.py --origen <taller-3d de la otra carpeta> --destino <taller-3d de Taller 3D> \\
        --carpeta "<ruta de Taller 3D en la PC>" --salida <dónde dejar los tres archivos> [--base origen|destino]

`--origen` y `--destino` son las carpetas (traídas de la PC) donde están `config.json`, `catalogo.json` e
`historial.csv` de cada taller; puede faltar cualquiera. De la configuración manda la más completa (o la de `--base`)
y la otra completa lo que falte; las impresoras de las dos quedan; las piezas se suman por carpeta.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalogo  # noqa: E402

ENCABEZADO = ["fecha", "acción", "pieza o perfil", "archivo", "resultado"]
# Lo que conviene mover además de las piezas, si existe en la otra carpeta (relativo a la carpeta de trabajo).
TAMBIEN = ["respaldos/ (las carpetas de adentro)", "calibraciones/ (lo de adentro)", "taller-3d/impresoras/ (los .json que falten)",
           "taller-3d/blender/", "taller-3d/aprendizajes.md", "taller-3d/novedades-orca.json (si en Taller 3D no hay)"]


def _leer(ruta: Path):
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.is_file() and ruta.read_text(encoding="utf-8").strip() else None


def hojas(valor) -> int:
    """Cuántos datos cargados tiene una configuración (para saber cuál es la más completa)."""
    if isinstance(valor, dict):
        return sum(hojas(v) for v in valor.values())
    if isinstance(valor, list):
        return sum(hojas(v) for v in valor)
    return 0 if valor is None or valor == "" else 1


def completar(base, otro):
    """Lo de `base` queda; lo que le falta (o está vacío) se toma de `otro`. Las listas se suman sin repetir."""
    if isinstance(base, dict) and isinstance(otro, dict):
        salida = dict(base)
        for clave, valor in otro.items():
            if clave not in salida or salida[clave] is None:
                if valor is not None:
                    salida[clave] = valor
            elif isinstance(salida[clave], (dict, list)):
                salida[clave] = completar(salida[clave], valor)
        return salida
    if isinstance(base, list) and isinstance(otro, list):
        return base + [v for v in otro if v not in base]
    return base


def unir_config(origen: dict | None, destino: dict | None, carpeta: str, base: str | None = None) -> tuple[dict, str]:
    origen, destino = origen or {}, destino or {}
    if base not in ("origen", "destino"):
        base = "origen" if hojas(origen) > hojas(destino) else "destino"
    manda, otra = (origen, destino) if base == "origen" else (destino, origen)
    impresoras = [dict(i) for i in manda.get("impresoras") or []]
    for imp in otra.get("impresoras") or []:
        igual = next((i for i in impresoras if i.get("id") == imp.get("id")), None)
        if igual is None:
            impresoras.append(dict(imp))
        else:
            igual.update(completar(igual, imp))
    config = completar({k: v for k, v in manda.items() if k != "impresoras"}, {k: v for k, v in otra.items() if k != "impresoras"})
    config["impresoras"] = impresoras
    config["carpeta_trabajo"] = carpeta
    return config, base


def unir_catalogo(origen: dict | None, destino: dict | None) -> tuple[dict, list[str]]:
    """Las piezas de los dos; si una carpeta está en los dos, queda la de Taller 3D y se avisa."""
    piezas = [dict(p) for p in (destino or {}).get("piezas") or []]
    carpetas = {p.get("carpeta") for p in piezas}
    repetidas = []
    for p in (origen or {}).get("piezas") or []:
        if p.get("carpeta") in carpetas:
            repetidas.append(p.get("carpeta"))
        else:
            piezas.append(dict(p))
    return {"version": 1, "piezas": piezas}, repetidas


def _filas(texto: str | None) -> list[list[str]]:
    if not texto:
        return []
    filas = [f for f in csv.reader(io.StringIO(texto), delimiter=";") if f]
    return [f for f in filas if f[0].strip().lower() != "fecha"]


def unir_historial(origen: str | None, destino: str | None) -> str:
    filas = _filas(destino) + _filas(origen)
    filas.sort(key=lambda f: f[0].replace("T", " ")[:16])        # estable: en el mismo minuto queda el orden de cada uno
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";", lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    escritor.writerow(ENCABEZADO)
    escritor.writerows(filas)
    return salida.getvalue()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--origen", type=Path, required=True, help="taller-3d de la otra carpeta")
    ap.add_argument("--destino", type=Path, required=True, help="taller-3d de Taller 3D (puede estar vacía)")
    ap.add_argument("--carpeta", required=True, help="ruta de Taller 3D en la PC del usuario")
    ap.add_argument("--salida", type=Path, required=True)
    ap.add_argument("--base", choices=("origen", "destino"), help="de cuál manda la configuración (por defecto, la más completa)")
    a = ap.parse_args(argv)

    cat_origen = _leer(a.origen / "catalogo.json")
    config, base = unir_config(_leer(a.origen / "config.json"), _leer(a.destino / "config.json"), a.carpeta, a.base)
    cat, repetidas = unir_catalogo(cat_origen, _leer(a.destino / "catalogo.json"))
    historial = unir_historial(*[(d / "historial.csv").read_text(encoding="utf-8") if (d / "historial.csv").is_file() else None
                                 for d in (a.origen, a.destino)])
    a.salida.mkdir(parents=True, exist_ok=True)
    (a.salida / "config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    catalogo.guardar(a.salida / "catalogo.json", cat)
    (a.salida / "historial.csv").write_text(historial, encoding="utf-8")

    print(f"Configuración: manda la de {'la otra carpeta' if base == 'origen' else 'Taller 3D'}; "
          f"{len(config['impresoras'])} impresora(s): {', '.join(str(i.get('nombre') or i.get('id')) for i in config['impresoras']) or 'ninguna'}.")
    print(f"Catálogo: {len(cat['piezas'])} entre ideas y piezas.")
    mover = [p["carpeta"] for p in (cat_origen or {}).get("piezas") or []
             if p.get("tipo") != "idea" and p.get("carpeta") not in repetidas]
    if mover:
        print("Carpetas de piezas para mover a Taller 3D (con el mismo nombre):")
        for c in mover:
            print(f"  - {c}")
    print("También, si existen: " + "; ".join(TAMBIEN) + ".")
    if repetidas:
        print("ATENCIÓN: estas carpetas están en los dos talleres; quedó la de Taller 3D y la otra no se mueve sin cambiarle el nombre:")
        for c in repetidas:
            print(f"  - {c}")
    print(f"Archivos unidos en {a.salida}: config.json, catalogo.json e historial.csv.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
