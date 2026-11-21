# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
"""CAD por código para piezas imprimibles, sobre manifold3d.

Unidades en mm. Ejes: X ancho, Y fondo, Z alto; Z = 0 es la cama.
Todas las funciones devuelven sólidos cerrados (manifold), así que las uniones y restas
siempre dan mallas válidas para laminar.

Uso en el script de una pieza:

    import sys
    sys.path.insert(0, "<carpeta scripts de la skill impresion-3d>")
    from cad import *

    placa = caja(60, 20, 4, radio=3)
    placa = restar(placa, mover(agujero_tornillo("M4", 4), x=10, y=10),
                   mover(agujero_tornillo("M4", 4), x=50, y=10))
    exportar_stl(placa, "pieza.stl")

Requiere: pip install --break-system-packages manifold3d numpy
"""
from __future__ import annotations

import math
import struct
from functools import reduce
from pathlib import Path

import numpy as np
from manifold3d import CrossSection, Error, JoinType, Manifold, OpType

__all__ = [
    "Manifold", "caja", "cilindro", "cono", "esfera", "tubo", "prisma", "ranura", "revolucion",
    "hexagono", "agujero", "agujero_tornillo", "alojamiento_tuerca", "agujero_inserto",
    "chaflan_inferior", "unir", "restar", "intersectar", "mover", "rotar", "espejar", "escalar",
    "apoyar", "centrar", "medidas", "exportar_stl", "holgura", "TORNILLOS", "HOLGURAS",
]

EPS = 0.01  # sobrante para que las restas no dejen caras coincidentes

# Medidas de partida (ISO 4762 cabeza cilíndrica, ISO 10642 avellanada, ISO 4032 tuerca).
# "rosca_plastico": agujero para que el tornillo haga su propia rosca en el plástico.
# "inserto": agujero típico para insertos roscados de latón instalados con calor.
TORNILLOS = {
    "M2": {"pasante": 2.4, "rosca_plastico": 1.8, "cabeza_d": 3.8, "cabeza_h": 2.0, "avellanado_d": 4.4,
           "tuerca": 4.0, "tuerca_h": 1.6, "inserto": 3.2},
    "M2.5": {"pasante": 2.9, "rosca_plastico": 2.2, "cabeza_d": 4.5, "cabeza_h": 2.5, "avellanado_d": 5.5,
             "tuerca": 5.0, "tuerca_h": 2.0, "inserto": 3.6},
    "M3": {"pasante": 3.4, "rosca_plastico": 2.7, "cabeza_d": 5.5, "cabeza_h": 3.0, "avellanado_d": 6.7,
           "tuerca": 5.5, "tuerca_h": 2.4, "inserto": 4.0},
    "M4": {"pasante": 4.5, "rosca_plastico": 3.6, "cabeza_d": 7.0, "cabeza_h": 4.0, "avellanado_d": 9.0,
           "tuerca": 7.0, "tuerca_h": 3.2, "inserto": 5.6},
    "M5": {"pasante": 5.5, "rosca_plastico": 4.5, "cabeza_d": 8.5, "cabeza_h": 5.0, "avellanado_d": 11.2,
           "tuerca": 8.0, "tuerca_h": 4.7, "inserto": 6.4},
    "M6": {"pasante": 6.6, "rosca_plastico": 5.4, "cabeza_d": 10.0, "cabeza_h": 6.0, "avellanado_d": 13.4,
           "tuerca": 10.0, "tuerca_h": 5.2, "inserto": 8.0},
}

# Holguras de partida por lado (mm) entre dos piezas impresas. Calibrar con el test de
# tolerancia de Orca y anotar el resultado en aprendizajes.md.
HOLGURAS = {
    "presion": {"PLA": 0.10, "PETG": 0.12},
    "justo": {"PLA": 0.15, "PETG": 0.20},
    "deslizante": {"PLA": 0.25, "PETG": 0.30},
    "giratorio": {"PLA": 0.35, "PETG": 0.40},
}


def holgura(tipo: str = "justo", material: str = "PETG") -> float:
    """Holgura por lado recomendada para un encastre ('presion', 'justo', 'deslizante', 'giratorio')."""
    tabla = HOLGURAS[tipo]
    return tabla.get(material.upper(), max(tabla.values()))


def _segmentos(diametro: float) -> int:
    """Cantidad de lados de un círculo para que cada lado mida ~0,4 mm (una línea de boquilla)."""
    return int(max(24, min(360, math.ceil(math.pi * max(diametro, 0.1) / 0.4))))


# --- Sólidos básicos -------------------------------------------------------------------

def caja(x: float, y: float, z: float, radio: float = 0.0, centrada: bool = False) -> Manifold:
    """Prisma rectangular apoyado en Z=0. 'radio' redondea las aristas verticales."""
    if radio > 0:
        r = min(radio, x / 2 - 1e-3, y / 2 - 1e-3)
        cs = CrossSection.square((x - 2 * r, y - 2 * r)).translate((r, r))
        cs = cs.offset(r, JoinType.Round, circular_segments=_segmentos(2 * r))
        solido = Manifold.extrude(cs, z)
    else:
        solido = Manifold.cube((x, y, z))
    return solido.translate((-x / 2, -y / 2, 0)) if centrada else solido


def cilindro(d: float, h: float, d_arriba: float | None = None) -> Manifold:
    """Cilindro (o tronco de cono) con el eje en el origen y la base en Z=0."""
    d2 = d if d_arriba is None else d_arriba
    return Manifold.cylinder(h, d / 2, d2 / 2, circular_segments=_segmentos(max(d, d2)))


def cono(d_base: float, h: float, d_punta: float = 0.0) -> Manifold:
    return cilindro(d_base, h, d_punta)


def esfera(d: float) -> Manifold:
    return Manifold.sphere(d / 2, _segmentos(d))


def tubo(d_ext: float, d_int: float, h: float) -> Manifold:
    return restar(cilindro(d_ext, h), mover(cilindro(d_int, h + 2 * EPS), z=-EPS))


def _antihorario(puntos) -> np.ndarray:
    p = np.asarray(puntos, dtype=float)
    area = 0.5 * np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])
    return p if area >= 0 else p[::-1]


def prisma(puntos_xy, h: float) -> Manifold:
    """Extruye un polígono (lista de (x, y), en cualquier sentido) hasta la altura h."""
    return Manifold.extrude(CrossSection([_antihorario(puntos_xy)]), h)


def ranura(largo: float, ancho: float, h: float) -> Manifold:
    """Ranura con extremos redondos (agujero chino), centrada en el origen, a lo largo de X."""
    recto = max(largo - ancho, 1e-3)
    cs = CrossSection.square((recto, 1e-3), center=True).offset(ancho / 2, JoinType.Round,
                                                                 circular_segments=_segmentos(ancho))
    return Manifold.extrude(cs, h)


def revolucion(perfil_xz, grados: float = 360.0) -> Manifold:
    """Gira un perfil (lista de (radio, z), radio >= 0) alrededor del eje Z."""
    perfil = _antihorario(perfil_xz)
    d = 2 * float(perfil[:, 0].max())
    return Manifold.revolve(CrossSection([perfil]), _segmentos(d), grados)


def hexagono(entre_caras: float, h: float) -> Manifold:
    """Prisma hexagonal (para alojar tuercas), centrado en el origen."""
    r = entre_caras / math.sqrt(3)
    puntos = [(r * math.cos(math.radians(60 * i)), r * math.sin(math.radians(60 * i))) for i in range(6)]
    return prisma(puntos, h)


# --- Agujeros (para restar) ---------------------------------------------------------------

def agujero(d: float, h: float, holgura_mm: float = 0.0) -> Manifold:
    """Cilindro para restar, un poco más largo arriba y abajo para cortar limpio."""
    return mover(cilindro(d + 2 * holgura_mm, h + 2 * EPS), z=-EPS)


def agujero_tornillo(metrica: str, largo: float, tipo: str = "pasante", cabeza: str | None = None,
                     profundidad_cabeza: float | None = None) -> Manifold:
    """Agujero para tornillo métrico desde Z=0 hasta 'largo'.

    tipo: 'pasante' (el tornillo pasa libre) o 'rosca_plastico' (el tornillo rosca en la pieza).
    cabeza: None, 'cilindrica' (rebaje arriba) o 'avellanada' (cono arriba).
    """
    t = TORNILLOS[metrica]
    forma = agujero(t[tipo], largo)
    if cabeza == "cilindrica":
        prof = profundidad_cabeza if profundidad_cabeza is not None else t["cabeza_h"] + 0.2
        forma = unir(forma, mover(cilindro(t["cabeza_d"] + 0.5, prof + EPS), z=largo - prof))
    elif cabeza == "avellanada":
        dc = t["avellanado_d"] + 0.3
        alto = (dc - t["pasante"]) / 2  # 90°
        forma = unir(forma, mover(cilindro(t["pasante"], alto + EPS, dc + 2 * EPS), z=largo - alto))
    return forma


def alojamiento_tuerca(metrica: str, profundidad: float | None = None, holgura_mm: float = 0.15) -> Manifold:
    """Hueco hexagonal para una tuerca, desde Z=0."""
    t = TORNILLOS[metrica]
    prof = profundidad if profundidad is not None else t["tuerca_h"] + 0.3
    return mover(hexagono(t["tuerca"] + 2 * holgura_mm, prof + EPS), z=-EPS)


def agujero_inserto(metrica: str, profundidad: float) -> Manifold:
    """Agujero para inserto roscado de latón (verificar con la ficha del inserto)."""
    return agujero(TORNILLOS[metrica]["inserto"], profundidad)


def chaflan_inferior(solido: Manifold, mm: float = 0.4, pasos: int = 4) -> Manifold:
    """Achaflana a ~45° el borde que apoya en la cama (evita la 'pata de elefante').

    Pensado para piezas de base plana: toma el contorno justo arriba del chaflán y arma la
    franja inferior en escalones de mm/pasos, cada uno un poco más chico hacia abajo.
    Los agujeros que llegan a la cama quedan con la entrada achaflanada.
    """
    x0, y0, z0, x1, y1, z1 = solido.bounding_box()
    if mm <= 0 or (z1 - z0) <= mm:
        return solido
    huella = solido.slice(z0 + mm + 1e-3)
    if huella.is_empty():
        return solido
    franja = mover(caja(x1 - x0 + 2, y1 - y0 + 2, mm + EPS), x=x0 - 1, y=y0 - 1, z=z0 - EPS)
    sin_franja = restar(solido, franja)
    alto = mm / pasos
    partes = []
    for i in range(pasos):
        reduccion = mm * (1 - (i + 0.5) / pasos)
        cs = huella.offset(-reduccion, JoinType.Miter)
        if not cs.is_empty():
            partes.append(mover(Manifold.extrude(cs, alto + EPS), z=z0 + i * alto))
    return unir(sin_franja, *partes) if partes else solido


# --- Operaciones -------------------------------------------------------------------------

def unir(*solidos: Manifold) -> Manifold:
    solidos = [s for s in solidos if s is not None]
    return Manifold.batch_boolean(list(solidos), OpType.Add) if len(solidos) > 1 else solidos[0]


def restar(base: Manifold, *recortes: Manifold) -> Manifold:
    recortes = [r for r in recortes if r is not None]
    if not recortes:
        return base
    return Manifold.batch_boolean([base, *recortes], OpType.Subtract)


def intersectar(*solidos: Manifold) -> Manifold:
    return reduce(lambda a, b: a ^ b, solidos)


def mover(solido: Manifold, x: float = 0, y: float = 0, z: float = 0) -> Manifold:
    return solido.translate((x, y, z))


def rotar(solido: Manifold, x: float = 0, y: float = 0, z: float = 0) -> Manifold:
    """Rotación en grados alrededor de los ejes X, Y y Z (en ese orden), centrada en el origen."""
    return solido.rotate((x, y, z))


def espejar(solido: Manifold, eje: str = "x") -> Manifold:
    normal = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[eje.lower()]
    return solido.mirror(normal)


def escalar(solido: Manifold, factor) -> Manifold:
    f = (factor, factor, factor) if isinstance(factor, (int, float)) else tuple(factor)
    return solido.scale(f)


def apoyar(solido: Manifold) -> Manifold:
    """Baja la pieza hasta que toque Z=0."""
    return mover(solido, z=-solido.bounding_box()[2])


def centrar(solido: Manifold, x: float | None = None, y: float | None = None,
            impresora: dict | None = None) -> Manifold:
    """Centra la pieza en (x, y) o, con los datos de la impresora, en el centro de su cama."""
    if impresora is not None:
        area = impresora["area"]
        x = (area["x_min"] + area["x_max"]) / 2 if x is None else x
        y = (area["y_min"] + area["y_max"]) / 2 if y is None else y
    if x is None or y is None:
        raise ValueError("centrar necesita x e y, o los datos de la impresora (impresora=...).")
    x0, y0, _, x1, y1, _ = solido.bounding_box()
    return mover(solido, x=x - (x0 + x1) / 2, y=y - (y0 + y1) / 2)


def medidas(solido: Manifold) -> tuple[float, float, float]:
    x0, y0, z0, x1, y1, z1 = solido.bounding_box()
    return (round(x1 - x0, 3), round(y1 - y0, 3), round(z1 - z0, 3))


# --- Exportar ----------------------------------------------------------------------------

def exportar_stl(solido: Manifold, ruta, nombre: str = "taller-3d", apoyar_en_cama: bool = True) -> dict:
    """Guarda un STL binario. Verifica que el sólido sea válido y no esté vacío."""
    if solido.status() != Error.NoError:
        raise ValueError(f"El sólido no es válido: {solido.status()}")
    if solido.is_empty():
        raise ValueError("El sólido está vacío: revisá las restas y posiciones.")
    solido = solido.simplify(1e-3)  # quita astillas de área cero que dejan las operaciones
    if apoyar_en_cama:
        solido = apoyar(solido)
    malla = solido.to_mesh()
    vert = np.asarray(malla.vert_properties, dtype=np.float64)[:, :3]
    caras = np.asarray(malla.tri_verts, dtype=np.int64)
    tri = vert[caras]
    normales = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    largo = np.linalg.norm(normales, axis=1, keepdims=True)
    normales = np.divide(normales, largo, out=np.zeros_like(normales), where=largo > 0)
    reg = np.zeros(len(tri), dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    reg["n"] = normales
    reg["v"] = tri
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "wb") as f:
        f.write(nombre.encode("ascii", "replace")[:80].ljust(80, b" "))
        f.write(struct.pack("<I", len(tri)))
        f.write(reg.tobytes())
    return {
        "archivo": str(ruta),
        "medidas_mm": medidas(solido),
        "volumen_cm3": round(solido.volume() / 1000, 3),
        "triangulos": int(len(tri)),
        "genero": int(solido.genus()),
    }
