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
    "apoyar", "centrar", "medidas", "exportar_stl", "importar_stl", "hueco_para", "holgura", "TORNILLOS", "HOLGURAS",
    "deformar", "desgastar", "marca_golpe", "marca_tajo", "marca_rayon", "marca_picadura",
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


# --- Importar ----------------------------------------------------------------------------

def importar_stl(ruta) -> Manifold:
    """Trae un STL (hecho en Blender o bajado) como sólido, para unirlo o restarlo con piezas de código.

    Usa las mismas unidades del archivo (mm). La malla tiene que ser cerrada: si no, falla y dice qué hacer.
    """
    from manifold3d import Mesh
    from revisar_stl import leer_stl

    ruta = Path(ruta)
    tri = leer_stl(ruta)
    if not len(tri):
        raise ValueError(f"{ruta.name} no tiene triángulos.")
    # En un STL cada triángulo trae sus vértices: se juntan los que coinciden para que la malla se cierre.
    vert, indices = np.unique(np.round(tri.reshape(-1, 3), 4), axis=0, return_inverse=True)
    caras = indices.reshape(-1, 3)
    caras = caras[(caras[:, 0] != caras[:, 1]) & (caras[:, 1] != caras[:, 2]) & (caras[:, 0] != caras[:, 2])]
    solido = None
    for orden in (caras, caras[:, [0, 2, 1]]):          # si vino dada vuelta, se prueba al revés
        prueba = Manifold(Mesh(vert_properties=vert.astype(np.float32), tri_verts=orden.astype(np.uint32)))
        if prueba.status() == Error.NoError and not prueba.is_empty() and prueba.volume() > 0:
            solido = prueba
            break
    if solido is None:
        raise ValueError(f"{ruta.name} no es una malla cerrada: no se puede unir ni restar. En Blender, aplicar "
                         "Remesh (Voxel) o Make Manifold (3D Print Toolbox) y exportar de nuevo.")
    return solido


def hueco_para(pieza: Manifold, profundidad: float, holgura_mm: float = 0.3) -> Manifold:
    """Hueco para que `pieza` entre de arriba hacia abajo en otra (una máscara en su base, una figura en su peana).

    Es la sombra vista desde arriba de los últimos `profundidad` mm de la pieza (contados desde su punto más bajo),
    agrandada `holgura_mm` por lado, sin islas adentro (serían astillas imposibles de imprimir) y extruida hacia
    arriba, así no tiene trabas aunque la pieza esté inclinada. Sale con el piso en Z = 0 y 1 mm más alto que la
    profundidad: subirlo hasta el piso del hueco y restarlo de la base; la pieza va con su punto más bajo en ese
    piso, en la misma posición en X e Y que tenía al calcular el hueco.
    """
    if profundidad <= 0:
        raise ValueError("La profundidad del hueco tiene que ser mayor que 0.")
    x0, y0, z0, x1, y1, _ = pieza.bounding_box()
    franja = pieza ^ Manifold.cube((x1 - x0 + 2, y1 - y0 + 2, profundidad + 0.5)).translate((x0 - 1, y0 - 1, z0))
    if franja.is_empty():
        raise ValueError("La pieza no tiene nada en esa franja de abajo.")
    sombra = franja.project().offset(holgura_mm, JoinType.Round, circular_segments=24) if holgura_mm > 0 \
        else franja.project()
    contornos = [np.asarray(c) for c in sombra.to_polygons()]
    afuera = [c for c in contornos if 0.5 * np.sum(c[:, 0] * np.roll(c[:, 1], -1) - np.roll(c[:, 0], -1) * c[:, 1]) > 0]
    return Manifold.extrude(CrossSection(afuera), profundidad + 1)


# --- Exportar ----------------------------------------------------------------------------

# ------------------------------------------------------------------ desgaste y daño: se deforma, no se corta
# Un golpe de verdad hunde el material con bordes suaves y le levanta un labio alrededor; un tajo de filo deja un
# surco con el material corrido a un costado y astillados chicos; un rayón tiembla, cambia de hondo y se corta.
# Restar esferas o cajas deja bordes perfectos, que se ven falsos. Por eso acá se mueven los puntos de la malla.

def deformar(solido: Manifold, funcion, malla: float = 0.6, tolerancia: float = 0.02) -> Manifold:
    """Afina la malla (triángulos de `malla` mm), mueve sus puntos con `funcion` (recibe un arreglo N×3 y devuelve
    otro igual) y vuelve a simplificarla. Para dar forma orgánica a algo hecho con medidas: abollar, doblar un borde,
    torcer. Los agujeros y encastres que tienen que quedar exactos se cortan después de deformar."""
    if malla <= 0:
        raise ValueError("El tamaño de malla tiene que ser mayor que cero.")
    fino = solido.refine_to_length(float(malla))
    movido = fino.warp_batch(lambda v: np.asarray(funcion(np.array(v, dtype=float)), dtype=float))
    return movido.simplify(float(tolerancia))


def _ruido(x, fases):
    return 0.6 * np.sin(x + fases[0]) + 0.3 * np.sin(2.7 * x + fases[1]) + 0.15 * np.sin(6.1 * x + fases[2])


def _marca(punto, normal, direccion, alcance, perfil) -> dict:
    n = np.asarray(normal, dtype=float)
    n = n / np.linalg.norm(n)
    d = np.asarray(direccion, dtype=float)
    d = d - n * float(d @ n)
    if np.linalg.norm(d) < 1e-9:
        raise ValueError("La dirección de la marca no puede ser la misma que la normal.")
    d = d / np.linalg.norm(d)
    return {"p": np.asarray(punto, dtype=float), "n": n, "d": d, "c": np.cross(n, d), "alcance": float(alcance),
            "perfil": perfil}


def _azar(azar):
    return azar if azar is not None else np.random.default_rng(0)


def marca_golpe(punto, normal, direccion, largo: float, ancho: float, hondo: float, azar=None) -> dict:
    """Una abolladura: hundimiento suave de radios `largo` × `ancho` (a lo largo de `direccion`) y `hondo` mm, con
    forma algo irregular y un labio apenas levantado alrededor. `normal` apunta hacia afuera de la pieza."""
    fases = _azar(azar).uniform(0, 2 * math.pi, 3)

    def perfil(s, t):
        r = np.sqrt((s / largo) ** 2 + (t / ancho) ** 2) / (1 + 0.18 * _ruido(np.arctan2(t / ancho, s / largo) * 2, fases))
        return hondo * np.exp(-1.3 * r ** 2.4) - 0.10 * hondo * np.exp(-((r - 1.35) / 0.28) ** 2)
    return _marca(punto, normal, direccion, 2.2 * max(largo, ancho), perfil)


def marca_tajo(punto, normal, direccion, largo: float, hondo: float = 1.3, ancho: float = 0.9, azar=None) -> dict:
    """Un tajo de filo: surco en V que entra de golpe y sale de a poco, con el material corrido a un costado,
    astillados chicos al azar en los bordes y la superficie que cede un poco alrededor."""
    azar = _azar(azar)
    fases, fases2 = azar.uniform(0, 2 * math.pi, 3), azar.uniform(0, 2 * math.pi, 3)
    astillas = [(azar.uniform(-0.45, 0.45) * largo, azar.choice([-1, 1]), azar.uniform(0.7, 1.9), azar.uniform(0.35, 0.8))
                for _ in range(int(azar.integers(5, 10)))]
    lado = azar.choice([-1, 1])

    def perfil(s, t):
        u = s / largo + 0.5
        entra = np.clip(u / 0.12, 0, 1) * np.clip((1 - u) / 0.45, 0, 1) ** 0.8
        w = ancho * (1 + 0.3 * _ruido(s * 0.55, fases))
        tt = t - 0.5 * _ruido(s * 0.16, fases2)
        total = (hondo * np.clip(1 - np.abs(tt) / w, 0, None) ** 1.2
                 - 0.38 * hondo * np.exp(-((tt - lado * 1.5 * w) / (0.6 * w)) ** 2)
                 - 0.12 * hondo * np.exp(-((tt + lado * 1.6 * w) / (0.6 * w)) ** 2)
                 + 0.45 * hondo * np.exp(-(tt / (4.5 * w)) ** 2))
        for s0, lado_a, tam, fuerza in astillas:
            total = total + fuerza * hondo * np.exp(-((s - s0) / tam) ** 2 - ((tt - lado_a * 1.15 * w) / (0.75 * tam)) ** 2)
        return entra * total
    return _marca(punto, normal, direccion, 0.62 * largo, perfil)


def marca_rayon(punto, normal, direccion, largo: float, fuerza: float = 1.0, azar=None) -> dict:
    """Un rayón: surco fino de bordes suaves que tiembla, se curva un poco, entra fuerte y se va perdiendo, y por
    momentos casi no marca. `fuerza` de 0,4 (apenas) a 1,3 (hondo: medio milímetro largo)."""
    azar = _azar(azar)
    fases, fases2 = azar.uniform(0, 2 * math.pi, 3), azar.uniform(0, 2 * math.pi, 3)
    temblor, curva = azar.uniform(0.3, 1.0) * fuerza, azar.uniform(-0.05, 0.05) * largo
    entrada = azar.uniform(0.05, 0.18)
    hondo, w = 0.5 * fuerza, 0.45 + 0.32 * fuerza
    picos = [(azar.uniform(-0.4, 0.4) * largo, azar.uniform(0.6, 1.4), azar.uniform(0.5, 1.1))
             for _ in range(int(azar.integers(1, 4)))]

    def perfil(s, t):
        u = s / largo + 0.5
        entra = np.clip(u / entrada, 0, 1) * np.clip(1 - u, 0, 1) ** 0.65 * (u > 0)
        tt = t - temblor * _ruido(u * 9, fases) - curva * np.sin(math.pi * np.clip(u, 0, 1))
        marca = 0.5 + 0.5 * np.clip(_ruido(u * 23, fases2) + 0.55, 0, 1)
        total = hondo * entra * marca * (np.exp(-(tt / w) ** 2) - 0.2 * np.exp(-((np.abs(tt) - 1.8 * w) / (0.6 * w)) ** 2))
        for s0, tam, fuerza_p in picos:
            total = total + hondo * fuerza_p * entra * np.exp(-((s - s0) / tam) ** 2 - (tt / (0.8 * tam)) ** 2)
        return total
    return _marca(punto, normal, direccion, 0.6 * largo, perfil)


def marca_picadura(punto, normal, radio: float = 1.8, hondo: float = 0.4) -> dict:
    """Una marca chica de uso: un hoyito suave."""
    n = np.asarray(normal, dtype=float)
    otra = np.cross(n, (0, 0, 1)) if abs(n[2]) < 0.9 * np.linalg.norm(n) else np.cross(n, (1, 0, 0))
    return _marca(punto, normal, otra, 3 * radio, lambda s, t: hondo * np.exp(-(s ** 2 + t ** 2) / radio ** 2))


def desgastar(solido: Manifold, marcas: list[dict], malla: float = 0.6, espesor: float = 3.0, curvatura: float = 80.0,
              donde=None, tolerancia: float = 0.02) -> Manifold:
    """Aplica marcas (marca_golpe, marca_tajo, marca_rayon, marca_picadura) a un sólido, hundiendo el material hacia
    adentro en cada una. Mueve por igual todo lo que está hasta `espesor` mm por debajo de la superficie, así una
    chapa abollada conserva su espesor (la abolladura se ve también del otro lado). `curvatura` es el radio de la
    superficie más cerrada donde hay marcas. `donde(v)`, opcional, devuelve qué puntos se pueden mover: sirve para
    dejar intactos los encastres y los agujeros (o cortarlos después de desgastar)."""
    def funcion(v):
        mueve = np.zeros_like(v)
        libre = np.ones(len(v), dtype=bool) if donde is None else np.asarray(donde(v), dtype=bool)
        for m in marcas:
            rel = v - m["p"]
            s, t, alto = rel @ m["d"], rel @ m["c"], rel @ m["n"]
            r2 = s ** 2 + t ** 2
            cerca = libre & (r2 < m["alcance"] ** 2) & (alto < 8) & (alto > -(espesor + 2.5 + r2 / (1.4 * curvatura)))
            if cerca.any():
                mueve[cerca] -= np.outer(m["perfil"](s[cerca], t[cerca]), m["n"])
        return v + mueve
    return deformar(solido, funcion, malla, tolerancia)


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
