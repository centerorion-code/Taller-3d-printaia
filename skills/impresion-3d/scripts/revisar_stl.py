#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
"""Revisión de una malla STL antes de laminar.

Revisa que la malla sea cerrada y válida, mide la pieza, verifica que entre en la cama,
estima la superficie de apoyo, marca voladizos que pueden necesitar soporte y compara
con las medidas esperadas. Opcionalmente rota, apoya y centra la pieza y la guarda.

Uso:
  python3 revisar_stl.py pieza.stl [--impresora taller-3d/impresoras/<id>.json] [--material PETG]
         [--esperado 40x20x10] [--tolerancia 0.2] [--umbral-voladizo 45]
         [--rotar 90,0,0] [--escala 1.5 | --alto 180] [--apoyar] [--centrar] [--salida pieza_orientada.stl]
         [--otras <carpeta con los datos de las otras impresoras>] [--json informe.json]

Si la pieza no entra en la impresora elegida y se pasa --otras, dice en cuáles de las otras
impresoras del usuario entra (tal cual o girándola).

--escala multiplica todas las medidas y --alto escala parejo hasta ese alto en Z (después de --rotar): sirve para
los modelos generados con IA, que vienen sin unidades. Avisa si la pieza es una cáscara fina (paredes de menos
de 1,6 mm en promedio en una pieza grande), lo típico de esos modelos: se engrosa con engrosar_stl.py.

Código de salida: 0 aprobado, 1 con advertencias, 2 rechazado.
"""
from __future__ import annotations

import argparse
import itertools
import json
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comun  # noqa: E402
from comun import ADVERTENCIA, APROBADO, RECHAZO  # noqa: E402


def leer_stl(ruta: Path) -> np.ndarray:
    """Devuelve un array (n, 3, 3) con los vértices de cada triángulo."""
    datos = ruta.read_bytes()
    if len(datos) >= 84:
        n = struct.unpack_from("<I", datos, 80)[0]
        if 84 + 50 * n == len(datos):
            reg = np.frombuffer(datos, dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]),
                                count=n, offset=84)
            return reg["v"].astype(np.float64)
    texto = datos.decode("utf-8", errors="replace")
    if "facet" not in texto or "vertex" not in texto:
        raise ValueError("No parece un STL válido (ni binario ni ASCII).")
    vals = [list(map(float, ln.split()[1:4])) for ln in texto.splitlines() if ln.strip().startswith("vertex")]
    v = np.array(vals, dtype=np.float64)
    if len(v) % 3:
        raise ValueError("STL ASCII con una cantidad de vértices que no es múltiplo de 3.")
    return v.reshape(-1, 3, 3)


def escribir_stl(ruta: Path, tri: np.ndarray, nombre: str = "taller-3d") -> None:
    normales = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    largo = np.linalg.norm(normales, axis=1, keepdims=True)
    normales = np.divide(normales, largo, out=np.zeros_like(normales), where=largo > 0)
    reg = np.zeros(len(tri), dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    reg["n"] = normales
    reg["v"] = tri
    cabecera = nombre.encode("ascii", "replace")[:80].ljust(80, b" ")
    with open(ruta, "wb") as f:
        f.write(cabecera)
        f.write(struct.pack("<I", len(tri)))
        f.write(reg.tobytes())


def rotar(tri: np.ndarray, grados_xyz) -> np.ndarray:
    ax, ay, az = np.radians(grados_xyz)
    rx = np.array([[1, 0, 0], [0, np.cos(ax), -np.sin(ax)], [0, np.sin(ax), np.cos(ax)]])
    ry = np.array([[np.cos(ay), 0, np.sin(ay)], [0, 1, 0], [-np.sin(ay), 0, np.cos(ay)]])
    rz = np.array([[np.cos(az), -np.sin(az), 0], [np.sin(az), np.cos(az), 0], [0, 0, 1]])
    return tri @ (rz @ ry @ rx).T


def componentes(caras: np.ndarray, n_vertices: int) -> np.ndarray:
    """Etiqueta de cada vértice según la parte de la malla a la que pertenece (partes que no se tocan)."""
    etiqueta = np.arange(n_vertices)
    a = np.concatenate([caras[:, 0], caras[:, 1], caras[:, 2]])
    b = np.concatenate([caras[:, 1], caras[:, 2], caras[:, 0]])
    while True:
        ea, eb = etiqueta[a], etiqueta[b]
        menor = np.minimum(ea, eb)
        nueva = etiqueta.copy()
        np.minimum.at(nueva, ea, menor)          # cada raíz se cuelga de la menor de su borde
        np.minimum.at(nueva, eb, menor)
        while True:                              # y se acortan los caminos hasta la raíz
            salto = nueva[nueva]
            if np.array_equal(salto, nueva):
                break
            nueva = salto
        if np.array_equal(nueva, etiqueta):
            return etiqueta
        etiqueta = nueva


def partes_sueltas(vert: np.ndarray, caras: np.ndarray, z_min: float, signo: float, distancia: float = 0.3) -> dict:
    """Partes de la malla que no apoyan en la cama: las que tocan otra parte sin estar unidas y las que quedan en
    el aire. Los huecos internos (cáscaras con volumen negativo) no cuentan. Para ver si se tocan usa manifold3d;
    sin él, las que no apoyan quedan como "sin_saber"."""
    etiqueta = componentes(caras, len(vert))
    _, parte = np.unique(etiqueta[caras[:, 0]], return_inverse=True)
    parte = parte.reshape(-1)
    k = int(parte.max()) + 1 if len(parte) else 0
    v0, v1, v2 = vert[caras[:, 0]], vert[caras[:, 1]], vert[caras[:, 2]]
    volumen = np.bincount(parte, weights=np.einsum("ij,ij->i", v0, np.cross(v1, v2)) / 6.0, minlength=k) * signo
    z_parte = np.full(k, np.inf)
    np.minimum.at(z_parte, parte, np.minimum(np.minimum(v0[:, 2], v1[:, 2]), v2[:, 2]))
    solidas = volumen > 1e-6
    arriba = [int(c) for c in np.where(solidas & (z_parte > z_min + distancia))[0]]
    r = {"partes": int(solidas.sum()), "sin_unir": [], "en_el_aire": [], "sin_saber": []}
    if not arriba:
        return r
    try:
        from manifold3d import Error, Manifold, Mesh
    except ImportError:
        r["sin_saber"] = [round(float(z_parte[c]), 1) for c in arriba]
        return r

    def solido(elegidos):
        c = caras[elegidos]
        usados, nuevos = np.unique(c, return_inverse=True)
        m = Manifold(Mesh(vert_properties=vert[usados].astype(np.float32),
                          tri_verts=nuevos.reshape(-1, 3).astype(np.uint32)))
        return m if m.status() == Error.NoError else None

    for c in arriba[:50]:
        propia, resto = solido(parte == c), solido(parte != c)
        z = round(float(z_parte[c]), 1)
        if propia is None or resto is None:
            r["sin_saber"].append(z)
            continue
        crecida = propia                         # la parte, agrandada unos décimos en las seis direcciones
        for d in ((distancia, 0, 0), (-distancia, 0, 0), (0, distancia, 0), (0, -distancia, 0),
                  (0, 0, distancia), (0, 0, -distancia)):
            crecida = crecida + propia.translate(d)
        (r["sin_unir"] if (crecida ^ resto).volume() > 1e-6 else r["en_el_aire"]).append(z)
    return r


def analizar(tri: np.ndarray, impresora: dict, material: str | None, esperado=None, tolerancia=0.2,
             umbral=45.0) -> dict:
    hallazgos: list[dict] = []

    def agregar(g, m):
        hallazgos.append({"gravedad": g, "mensaje": m})

    if len(tri) == 0:
        return {"estado": RECHAZO, "hallazgos": [{"gravedad": RECHAZO, "mensaje": "La malla está vacía."}]}

    pts = tri.reshape(-1, 3)
    minimo, maximo = pts.min(axis=0), pts.max(axis=0)
    medidas = maximo - minimo

    # Un STL no dice en qué unidad está: si es diminuta, casi seguro vino en metros o en pulgadas.
    if 0 < float(medidas.max()) < 5:
        agregar(ADVERTENCIA, f"La pieza mide {medidas[0]:.2f}×{medidas[1]:.2f}×{medidas[2]:.2f} mm: si no es tan "
                "chica, el archivo está en otra unidad (metros: --escala 1000; pulgadas: --escala 25.4; "
                "centímetros: --escala 10). Preguntar cuánto tiene que medir.")

    # Malla cerrada y orientada
    claves = np.round(pts / 1e-4).astype(np.int64)
    _, primeros, idx = np.unique(claves, axis=0, return_index=True, return_inverse=True)
    caras = idx.reshape(-1, 3)
    vertices = pts[primeros]
    degeneradas = (caras[:, 0] == caras[:, 1]) | (caras[:, 1] == caras[:, 2]) | (caras[:, 0] == caras[:, 2])
    caras_ok = caras[~degeneradas]
    dirigidas = np.concatenate([caras_ok[:, [0, 1]], caras_ok[:, [1, 2]], caras_ok[:, [2, 0]]])
    no_dirigidas = np.sort(dirigidas, axis=1)
    _, cuenta = np.unique(no_dirigidas, axis=0, return_counts=True)
    bordes_abiertos = int((cuenta == 1).sum())
    no_manifold = int((cuenta > 2).sum())
    _, cuenta_dir = np.unique(dirigidas, axis=0, return_counts=True)
    mal_orientadas = int((cuenta_dir > 1).sum())

    v0, v1, v2 = tri[:, 0], tri[:, 1], tri[:, 2]
    cruz = np.cross(v1 - v0, v2 - v0)
    area_tri = 0.5 * np.linalg.norm(cruz, axis=1)
    volumen = float(np.einsum("ij,ij->i", v0, np.cross(v1, v2)).sum() / 6.0)
    area_total = float(area_tri.sum())
    with np.errstate(invalid="ignore", divide="ignore"):
        normal = cruz / np.linalg.norm(cruz, axis=1, keepdims=True)
    normal = np.nan_to_num(normal)
    if volumen < 0:
        normal = -normal

    if bordes_abiertos:
        agregar(RECHAZO, f"La malla no es cerrada: {bordes_abiertos} bordes abiertos. Repararla antes de laminar.")
    if no_manifold:
        agregar(RECHAZO, f"La malla tiene {no_manifold} bordes compartidos por más de dos caras (no es manifold).")
    if mal_orientadas and not bordes_abiertos and not no_manifold:
        agregar(ADVERTENCIA, f"{mal_orientadas} bordes con caras de orientación invertida.")
    if degeneradas.sum() > max(10, 0.005 * len(tri)):
        agregar(ADVERTENCIA, f"{int(degeneradas.sum())} triángulos degenerados (sin área): conviene reparar la malla.")
    if volumen < 0:
        agregar(ADVERTENCIA, "Las normales apuntan hacia adentro (volumen negativo). Orca suele corregirlo.")

    # Cáscara fina: 2·V/A es el espesor de pared de una cáscara pareja (una máscara hueca generada con IA). Solo
    # cuenta si es chico al lado de la pieza: una placa de 1 mm o una pieza chica maciza no son cáscaras.
    espesor_medio = 2 * abs(volumen) / area_total if area_total > 0 else 0.0
    cascara = bool(not bordes_abiertos and not no_manifold and 0 < espesor_medio < ESPESOR_FINO
                   and espesor_medio < 0.1 * float(np.min(medidas)))
    if cascara:
        rota = espesor_medio < ESPESOR_MINIMO
        agregar(RECHAZO if rota else ADVERTENCIA,
                f"Es una cáscara de unos {espesor_medio:.2f} mm de pared en promedio "
                f"({'no se puede imprimir bien' if rota else 'frágil'}). Si viene de un generador de IA, "
                "engrosarla a 2 mm con engrosar_stl.py; si es a propósito, revisar que aguante.")

    # Partes separadas: una que no apoya en la cama ni toca otra parte se imprimiría en el aire
    partes = {"partes": 1, "sin_unir": [], "en_el_aire": [], "sin_saber": []}
    if not bordes_abiertos and not no_manifold and len(caras_ok):
        partes = partes_sueltas(vertices, caras_ok, float(minimo[2]), 1.0 if volumen >= 0 else -1.0)
    if partes["en_el_aire"]:
        n = len(partes["en_el_aire"])
        agregar(RECHAZO, f"{n} parte{'s' if n > 1 else ''} suelta{'s' if n > 1 else ''} en el aire: no apoya"
                f"{'n' if n > 1 else ''} en la cama ni toca{'n' if n > 1 else ''} la pieza (Z desde "
                f"{min(partes['en_el_aire']):g} mm). Unirla{'s' if n > 1 else ''} a la pieza o sacarla"
                f"{'s' if n > 1 else ''}.")
    if partes["sin_unir"]:
        n = len(partes["sin_unir"])
        agregar(ADVERTENCIA, f"{n} parte{'s' if n > 1 else ''} separada{'s' if n > 1 else ''} que toca"
                f"{'n' if n > 1 else ''} la pieza sin estar unida{'s' if n > 1 else ''}: unirla"
                f"{'s' if n > 1 else ''} (unir) para que salga como una sola pieza.")
    if partes["sin_saber"]:
        n = len(partes["sin_saber"])
        agregar(ADVERTENCIA, f"{n} parte{'s' if n > 1 else ''} separada{'s' if n > 1 else ''} que no apoya"
                f"{'n' if n > 1 else ''} en la cama: revisar que esté{'n' if n > 1 else ''} unida"
                f"{'s' if n > 1 else ''} a la pieza (sin manifold3d no se puede ver si se tocan).")

    # Entra en la cama (sin impresora, por ejemplo en /diseno, no se revisa)
    entra = None
    sugerencia = None
    if impresora:
        a = impresora["area"]
        disponible = np.array([a["x_max"] - a["x_min"], a["y_max"] - a["y_min"], a["z_max"]], dtype=float)
        entra = bool(np.all(medidas <= disponible + 1e-6))
    if impresora and not entra:
        for perm in itertools.permutations(range(3)):
            if np.all(medidas[list(perm)] <= disponible + 1e-6):
                sugerencia = perm
                break
        if sugerencia:
            agregar(RECHAZO, "No entra en la cama así orientada, pero entra girándola 90° (usar --rotar).")
        else:
            agregar(RECHAZO, f"No entra en la impresora ({disponible[0]:g}×{disponible[1]:g}×{disponible[2]:g} mm): "
                    "usar otra impresora más grande, partirla o escalarla.")

    # Apoyo en la cama
    z_min = minimo[2]
    en_cama = np.all(np.abs(tri[:, :, 2] - z_min) < 0.05, axis=1) & (normal[:, 2] < -0.99)
    area_apoyo = float(area_tri[en_cama].sum())
    huella = float(medidas[0] * medidas[1]) or 1.0
    if area_apoyo < 50 or area_apoyo / huella < 0.05:
        agregar(ADVERTENCIA, f"Poca superficie de apoyo ({area_apoyo / 100:.2f} cm²): usar brim o reorientar.")
    lado_menor = float(min(medidas[0], medidas[1])) or 1.0
    if medidas[2] / lado_menor > 3:
        agregar(ADVERTENCIA, "Pieza alta y fina: bajar aceleraciones, usar brim y poner el lado largo de la "
                "base a lo largo de Y.")

    # Voladizos
    centro_z = tri[:, :, 2].mean(axis=1)
    # Se ignoran los primeros 0,6 mm (chaflanes y escalones de la base).
    hacia_abajo = (normal[:, 2] < -1e-6) & (centro_z > z_min + 0.6)
    pendiente = np.degrees(np.arccos(np.clip(-normal[:, 2], -1, 1)))  # 0° = techo plano
    critico = hacia_abajo & (pendiente < umbral)
    area_voladizo = float(area_tri[critico].sum())
    zonas = []
    if critico.any():
        zs = centro_z[critico]
        zonas = [round(float(zs.min()), 1), round(float(zs.max()), 1)]
        agregar(ADVERTENCIA, f"Voladizos con menos de {umbral:g}° de pendiente: {area_voladizo / 100:.2f} cm² "
                f"(Z {zonas[0]}-{zonas[1]} mm). Si no son puentes cortos, activar soportes o reorientar.")

    # Medidas esperadas
    if esperado is not None:
        dif = np.abs(np.sort(medidas) - np.sort(np.array(esperado, dtype=float)))
        if np.any(dif > tolerancia):
            agregar(ADVERTENCIA, f"Las medidas ({medidas[0]:.2f}×{medidas[1]:.2f}×{medidas[2]:.2f} mm) difieren de las "
                    f"esperadas ({'×'.join(f'{e:g}' for e in esperado)}) en más de {tolerancia:g} mm.")

    # Peso macizo
    mat = comun.normalizar_material(material)
    densidad = comun.cargar_materiales().get(mat, {}).get("densidad", 1.24) if mat else 1.24
    gramos_macizo = abs(volumen) / 1000 * densidad

    estado = comun.peor(*(h["gravedad"] for h in hallazgos)) if hallazgos else APROBADO
    return {
        "estado": estado,
        "triangulos": int(len(tri)),
        "medidas_mm": [round(float(m), 3) for m in medidas],
        "minimo_mm": [round(float(m), 3) for m in minimo],
        "maximo_mm": [round(float(m), 3) for m in maximo],
        "volumen_cm3": round(abs(volumen) / 1000, 3),
        "superficie_cm2": round(area_total / 100, 2),
        "cascara_fina": cascara,
        "espesor_medio_mm": round(espesor_medio, 2) if cascara else None,
        "peso_macizo_g": round(gramos_macizo, 1),
        "cerrada": bordes_abiertos == 0 and no_manifold == 0,
        "partes": partes["partes"],
        "partes_en_el_aire": len(partes["en_el_aire"]),
        "partes_sin_unir": len(partes["sin_unir"]),
        "entra_en_cama": entra,
        "rotacion_sugerida": list(sugerencia) if sugerencia else None,
        "apoyo_cm2": round(area_apoyo / 100, 2),
        "voladizo_cm2": round(area_voladizo / 100, 2),
        "voladizo_z_mm": zonas,
        "hallazgos": hallazgos,
    }


ESPESOR_FINO = 1.6     # mm de pared promedio: menos es una cáscara frágil
ESPESOR_MINIMO = 0.6   # menos de una línea y media de una boquilla de 0,4 mm: no sale bien


# Las seis maneras de apoyar una pieza sobre una de sus caras: lo que hay que pasarle a --rotar y qué queda abajo.
ORIENTACIONES = [("0,0,0", "como viene"), ("180,0,0", "dada vuelta"), ("90,0,0", "el frente abajo"),
                 ("-90,0,0", "el fondo abajo"), ("0,90,0", "un costado abajo"), ("0,-90,0", "el otro costado abajo")]


def orientaciones(tri: np.ndarray, impresora: dict | None = None, umbral: float = 45.0) -> list[dict]:
    """Para un STL que no se diseñó acá: cómo queda apoyado sobre cada una de sus seis caras (superficie de apoyo,
    voladizos que pedirían soporte, alto y si entra en la cama), de la más conveniente a la menos. Es una guía: la
    dirección de la carga y la cara que se ve las decide quien conoce la pieza."""
    salida = []
    for grados, nombre in ORIENTACIONES:
        t = rotar(tri, [float(g) for g in grados.split(",")])
        z_min = float(t[:, :, 2].min())
        cruz = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
        doble = np.linalg.norm(cruz, axis=1)
        area = doble / 2
        normal_z = np.divide(cruz[:, 2], doble, out=np.zeros_like(doble), where=doble > 0)
        en_cama = np.all(np.abs(t[:, :, 2] - z_min) < 0.05, axis=1) & (normal_z < -0.99)
        centro_z = t[:, :, 2].mean(axis=1)
        pendiente = np.degrees(np.arccos(np.clip(-normal_z, -1, 1)))
        critico = (normal_z < -1e-6) & (centro_z > z_min + 0.6) & (pendiente < umbral)
        medidas = t.reshape(-1, 3).max(axis=0) - t.reshape(-1, 3).min(axis=0)
        apoyo, voladizo, alto = float(area[en_cama].sum()) / 100, float(area[critico].sum()) / 100, float(medidas[2])
        entra = None
        if impresora:
            a = impresora["area"]
            x, y = a["x_max"] - a["x_min"], a["y_max"] - a["y_min"]
            entra = bool(alto <= a["z_max"] + 1e-6 and ((medidas[0] <= x + 1e-6 and medidas[1] <= y + 1e-6)
                                                        or (medidas[1] <= x + 1e-6 and medidas[0] <= y + 1e-6)))
        salida.append({"rotar": grados, "como": nombre, "apoyo_cm2": round(apoyo, 2), "voladizo_cm2": round(voladizo, 2),
                       "alto_mm": round(alto, 1), "entra": entra,
                       "puntaje": round(voladizo - 0.5 * apoyo + alto / 50 + (1e6 if entra is False else 0), 3)})
    return sorted(salida, key=lambda o: o["puntaje"])


def entra_en(medidas, impresora: dict) -> str | None:
    """'tal cual', 'girándola' o None si la pieza no entra en esa impresora."""
    a = impresora["area"]
    disponible = np.array([a["x_max"] - a["x_min"], a["y_max"] - a["y_min"], a["z_max"]], dtype=float)
    medidas = np.asarray(medidas, dtype=float)
    if np.all(medidas <= disponible + 1e-6):
        return "tal cual"
    for perm in itertools.permutations(range(3)):
        if np.all(medidas[list(perm)] <= disponible + 1e-6):
            return "girándola"
    return None


def otras_donde_entra(medidas, impresoras, actual: dict | None = None) -> list[dict]:
    """De las otras impresoras del usuario, en cuáles entra la pieza."""
    salida = []
    for imp in impresoras:
        if actual is not None and imp.get("id") == actual.get("id"):
            continue
        como = entra_en(medidas, imp)
        if como:
            a = imp["area"]
            salida.append({"id": imp.get("id"), "nombre": imp.get("nombre"), "como": como,
                           "area_mm": [a["x_max"] - a["x_min"], a["y_max"] - a["y_min"], a["z_max"]]})
    return salida


def informe_texto(r: dict, nombre: str) -> str:
    m = r.get("medidas_mm", [0, 0, 0])
    lineas = [
        f"RESULTADO: {comun.TITULO[r['estado']]}",
        f"Archivo: {nombre}",
    ]
    if "triangulos" in r:
        lineas += [
            f"Medidas: {m[0]:.2f} × {m[1]:.2f} × {m[2]:.2f} mm | Triángulos: {r['triangulos']}",
            f"Volumen: {r['volumen_cm3']} cm³ (maciza pesaría {r['peso_macizo_g']} g) | "
            f"Malla cerrada: {'sí' if r['cerrada'] else 'NO'}",
            f"Entra en la cama: {'sin impresora' if r['entra_en_cama'] is None else ('sí' if r['entra_en_cama'] else 'NO')}"
            f" | Apoyo: {r['apoyo_cm2']} cm² | "
            f"Voladizos críticos: {r['voladizo_cm2']} cm²",
        ]
    if r.get("escala_aplicada") is not None:
        lineas.append(f"Escalada × {r['escala_aplicada']:g}: las medidas de arriba ya son las nuevas"
                      + ("" if r.get("salida") else " (con --salida se guarda así)"))
    if r.get("entra_en_otras") is not None:
        if r["entra_en_otras"]:
            lineas.append("Entra en otra impresora tuya: " + ", ".join(
                f"{o['nombre']} ({o['como']})" for o in r["entra_en_otras"]))
        else:
            lineas.append("No entra en ninguna de tus otras impresoras preparadas.")
    if r["hallazgos"]:
        lineas.append("Hallazgos:")
        etiqueta = {RECHAZO: "[RECHAZO]", ADVERTENCIA: "[ADVERTENCIA]"}
        for h in sorted(r["hallazgos"], key=lambda h: h["gravedad"] != RECHAZO):
            lineas.append(f"  {etiqueta[h['gravedad']]} {h['mensaje']}")
    return "\n".join(lineas)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Revisión de una malla STL.")
    ap.add_argument("stl", type=Path)
    ap.add_argument("--impresora", default="ninguna",
                    help="JSON con los datos de la impresora (taller-3d/impresoras/<id>.json) para revisar que "
                         "entre en la cama; 'ninguna' (por defecto) no lo revisa")
    ap.add_argument("--material")
    ap.add_argument("--esperado", help="medidas esperadas, por ejemplo 40x20x10")
    ap.add_argument("--tolerancia", type=float, default=0.2)
    ap.add_argument("--umbral-voladizo", type=float, default=45.0)
    ap.add_argument("--rotar", help="grados en X,Y,Z, por ejemplo 90,0,0")
    ap.add_argument("--escala", type=float, help="multiplicar todas las medidas, por ejemplo 1.5")
    ap.add_argument("--alto", type=float, help="escalar parejo hasta este alto en Z, en mm (después de --rotar)")
    ap.add_argument("--apoyar", action="store_true", help="bajar la pieza hasta Z=0")
    ap.add_argument("--centrar", action="store_true", help="centrar la pieza en la cama")
    ap.add_argument("--salida", type=Path, help="guardar la malla transformada")
    ap.add_argument("--orientar", action="store_true",
                    help="para un STL traído: compara las seis maneras de apoyarlo y dice qué pasarle a --rotar")
    ap.add_argument("--otras", type=Path, action="append", default=[],
                    help="carpeta con los datos de las otras impresoras del usuario (taller-3d/impresoras): si no "
                         "entra en la elegida, dice en cuál entra")
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)

    impresora = None if a.impresora.lower() in ("ninguna", "none", "-") else comun.cargar_impresora(a.impresora)
    if a.centrar and not impresora:
        raise SystemExit("--centrar necesita una impresora (--impresora <datos>).")
    if a.escala is not None and a.alto is not None:
        raise SystemExit("Usar --escala o --alto, no los dos (no se escribió nada).")
    for nombre, valor, tope in (("--escala", a.escala, 1000.0), ("--alto", a.alto, 5000.0)):
        if valor is not None and not (np.isfinite(valor) and 0 < valor <= tope):
            raise SystemExit(f"{nombre} tiene que ser un número mayor que 0 y hasta {tope:g} (no se escribió nada).")
    tri = leer_stl(a.stl)
    if a.rotar:
        tri = rotar(tri, [float(v) for v in a.rotar.split(",")])
    factor = None
    if a.escala is not None:
        factor = a.escala
    elif a.alto is not None:
        alto_actual = float(tri[:, :, 2].max() - tri[:, :, 2].min())
        if alto_actual <= 0:
            raise SystemExit("La pieza no tiene alto en Z: no se puede escalar con --alto (no se escribió nada).")
        factor = a.alto / alto_actual
    if factor is not None:
        tri = tri * factor
    if a.apoyar or a.centrar or a.rotar or factor is not None:
        tri = tri - np.array([0.0, 0.0, tri[:, :, 2].min()])
    if a.centrar:
        ar = impresora["area"]
        centro = np.array([(ar["x_min"] + ar["x_max"]) / 2, (ar["y_min"] + ar["y_max"]) / 2])
        pts = tri.reshape(-1, 3)
        actual = (pts[:, :2].min(axis=0) + pts[:, :2].max(axis=0)) / 2
        tri = tri + np.array([*(centro - actual), 0.0])
    esperado = [float(v) for v in a.esperado.lower().replace("×", "x").split("x")] if a.esperado else None
    r = analizar(tri, impresora, a.material, esperado, a.tolerancia, a.umbral_voladizo)
    if factor is not None:
        r["escala_aplicada"] = round(factor, 6)
    if a.otras and r.get("entra_en_cama") is not True:
        r["entra_en_otras"] = otras_donde_entra(r["medidas_mm"], comun.impresoras_en(a.otras), impresora)
    if a.salida:
        escribir_stl(a.salida, tri)
        r["salida"] = str(a.salida)
    print(informe_texto(r, a.stl.name))
    if a.orientar:
        r["orientaciones"] = orientaciones(tri, impresora, a.umbral_voladizo)
        print("Cómo apoyarla (de más a menos conveniente; la carga y la cara vista las decidís vos):")
        for o in r["orientaciones"]:
            print(f"  --rotar {o['rotar']:<8} {o['como']}: apoyo {o['apoyo_cm2']} cm², voladizos {o['voladizo_cm2']} cm², "
                  f"alto {o['alto_mm']} mm" + ("" if o["entra"] is not False else " — no entra en la cama"))
    if a.json:
        a.json.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    comun.salir(r["estado"])


if __name__ == "__main__":
    main()
