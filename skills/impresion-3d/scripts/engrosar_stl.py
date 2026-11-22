#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
"""Engrosa una cáscara fina para que se pueda imprimir, sin tocar la cara de afuera.

Los modelos generados con IA desde una foto (Hunyuan 3D y parecidos) suelen salir como una cáscara de menos de
1 mm de pared: una máscara hueca, una figura vacía por dentro. Este script mueve hacia el hueco solo la
superficie de adentro (la que mira al centro de la pieza) lo que falta para llegar a la pared pedida, rehace la
malla con voxels para cerrar los cruces que quedan y la simplifica. La cara de afuera, donde está el detalle,
queda donde estaba (se informa cuánto se movió).

Si la pieza no tiene un adentro claro (una lámina, una hoja), engrosa para los dos lados por igual.

Requiere Blender para Python, como render_producto.py: pip install --break-system-packages bpy
Uso:
  python3 -I engrosar_stl.py --stl mascara.stl --salida mascara-2mm.stl [--pared 2.0] [--voxel 0.25]
      [--caras 600000] [--lados auto|adentro|ambos] [--json datos.json]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from revisar_stl import componentes, escribir_stl, leer_stl  # noqa: E402


def soldar(tri: np.ndarray, decimales: int = 4):
    """Vértices compartidos (los STL repiten cada vértice en cada triángulo) y caras con índices."""
    puntos = tri.reshape(-1, 3)
    unicos, inversa = np.unique(np.round(puntos, decimales), axis=0, return_inverse=True)
    caras = np.asarray(inversa).reshape(-1, 3)
    sanas = (caras[:, 0] != caras[:, 1]) & (caras[:, 1] != caras[:, 2]) & (caras[:, 0] != caras[:, 2])
    return unicos, caras[sanas]


def volumen_y_area(vert: np.ndarray, caras: np.ndarray) -> tuple[float, float]:
    a, b, c = vert[caras[:, 0]], vert[caras[:, 1]], vert[caras[:, 2]]
    volumen = float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6)
    area = float(np.linalg.norm(np.cross(b - a, c - a), axis=1).sum() / 2)
    return volumen, area


def centro_de_masa(vert: np.ndarray, caras: np.ndarray) -> np.ndarray:
    a, b, c = vert[caras[:, 0]], vert[caras[:, 1]], vert[caras[:, 2]]
    v6 = np.einsum("ij,ij->i", a, np.cross(b, c))
    return ((a + b + c) * v6[:, None]).sum(0) / (4 * v6.sum())


def quitar_sobras(vert: np.ndarray, caras: np.ndarray, minimo: float = 0.02):
    """Deja las partes con al menos `minimo` del volumen de la mayor. Los voxels pueden dejar islas chicas
    sueltas o burbujas cerradas dentro de la pared (volumen negativo): se sacan las dos cosas. Un hueco grande
    (una figura cerrada y hueca por dentro) queda, porque es parte del diseño."""
    etiqueta = componentes(caras, len(vert))[caras[:, 0]]
    a, b, c = vert[caras[:, 0]], vert[caras[:, 1]], vert[caras[:, 2]]
    v6 = np.einsum("ij,ij->i", a, np.cross(b, c))
    _, posicion = np.unique(etiqueta, return_inverse=True)
    volumenes = np.bincount(posicion, weights=v6) / 6
    quedan = np.abs(volumenes) >= minimo * volumenes.max()
    sacadas = int((~quedan).sum())
    return caras[quedan[posicion]], sacadas, float(np.abs(volumenes[~quedan]).sum())


def normales_de_vertice(vert: np.ndarray, caras: np.ndarray) -> np.ndarray:
    """Normal de cada vértice, promedio de las caras que lo tocan pesado por el área (hacia afuera del material)."""
    a, b, c = vert[caras[:, 0]], vert[caras[:, 1]], vert[caras[:, 2]]
    nc = np.cross(b - a, c - a)
    nv = np.zeros_like(vert)
    for k in range(3):
        np.add.at(nv, caras[:, k], nc)
    largo = np.linalg.norm(nv, axis=1, keepdims=True)
    return np.divide(nv, largo, out=np.zeros_like(nv), where=largo > 0)


def factor_parejo(vert: np.ndarray, caras: np.ndarray, normales: np.ndarray) -> np.ndarray:
    """Cuánto alargar el corrimiento de cada vértice para que las caras se muevan lo pedido (como "Even Thickness"
    del Solidify de Blender): en una esquina la normal va en diagonal y, sin esto, la pared queda más fina."""
    a, b, c = vert[caras[:, 0]], vert[caras[:, 1]], vert[caras[:, 2]]
    nc = np.cross(b - a, c - a)
    peso = np.linalg.norm(nc, axis=1)
    nf = np.divide(nc, peso[:, None], out=np.zeros_like(nc), where=peso[:, None] > 0)
    suma, pesos = np.zeros(len(vert)), np.zeros(len(vert))
    for k in range(3):
        np.add.at(suma, caras[:, k], (normales[caras[:, k]] * nf).sum(1) * peso)
        np.add.at(pesos, caras[:, k], peso)
    media = np.divide(suma, pesos, out=np.ones_like(suma), where=pesos > 0)
    return 1 / np.clip(media, 1 / 3, 1)


def malla_blender(nombre: str, vert: np.ndarray, caras: np.ndarray):
    import bpy

    me = bpy.data.meshes.new(nombre)
    me.vertices.add(len(vert))
    me.vertices.foreach_set("co", vert.astype(np.float32).ravel())
    me.loops.add(len(caras) * 3)
    me.loops.foreach_set("vertex_index", caras.astype(np.int32).ravel())
    me.polygons.add(len(caras))
    me.polygons.foreach_set("loop_start", np.arange(0, len(caras) * 3, 3, dtype=np.int32))
    try:
        me.polygons.foreach_set("loop_total", np.full(len(caras), 3, dtype=np.int32))
    except (AttributeError, TypeError, RuntimeError):
        pass  # en Blender 4 en adelante el tamaño de cada cara sale de loop_start
    me.update(calc_edges=True)
    obj = bpy.data.objects.new(nombre, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def triangulos_de(obj) -> np.ndarray:
    """Triángulos (n, 3, 3) de un objeto de Blender con sus modificadores aplicados."""
    import bpy

    grafo = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(grafo))
    me.calc_loop_triangles()
    co = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    idx = np.empty(len(me.loop_triangles) * 3, dtype=np.int32)
    me.loop_triangles.foreach_get("vertices", idx)
    tri = co.reshape(-1, 3)[idx.reshape(-1, 3)].astype(np.float64)
    bpy.data.meshes.remove(me)
    return tri


def rehacer(vert: np.ndarray, caras: np.ndarray, voxel: float) -> np.ndarray:
    """La malla rehecha con voxels de Blender (cierra cruces y agujeros chicos): triángulos (n, 3, 3)."""
    import bpy

    obj = malla_blender("rehacer", vert, caras)
    remesh = obj.modifiers.new("voxels", "REMESH")
    remesh.mode = "VOXEL"
    remesh.voxel_size = voxel
    remesh.adaptivity = 0.0
    tri = triangulos_de(obj)
    malla = obj.data
    bpy.data.objects.remove(obj)
    bpy.data.meshes.remove(malla)
    return tri


def a_manifold(tri: np.ndarray):
    from manifold3d import Error, Manifold, Mesh

    vert, caras = soldar(tri, decimales=5)
    for orden in (caras, caras[:, ::-1]):
        solido = Manifold(Mesh(vert_properties=vert.astype(np.float32), tri_verts=orden.astype(np.uint32)))
        if solido.status() == Error.NoError and not solido.is_empty() and solido.volume() > 0:
            return solido
    raise ValueError("Blender devolvió una malla que no está cerrada: probar con otro --voxel.")


def triangulos_manifold(solido) -> np.ndarray:
    malla = solido.to_mesh()
    vert = np.asarray(malla.vert_properties, dtype=np.float64)[:, :3]
    return vert[np.asarray(malla.tri_verts, dtype=np.int64)]


def engrosar(tri: np.ndarray, pared: float = 2.0, voxel: float | None = None, caras_max: int = 600_000,
             lados: str = "auto") -> dict:
    import bpy
    from mathutils.bvhtree import BVHTree

    vert, caras = soldar(tri)
    volumen, area = volumen_y_area(vert, caras)
    if volumen < 0:  # caras al revés: que las normales miren hacia afuera del material
        caras = caras[:, ::-1]
        volumen = -volumen
    espesor = 2 * volumen / area
    info = {"espesor_antes_mm": round(espesor, 2), "pared_mm": pared, "caras_antes": int(len(caras))}
    if espesor >= pared:
        info.update(cambio=False, motivo=f"la pared ya tiene unos {espesor:.2f} mm")
        return info | {"triangulos": tri}

    normales = normales_de_vertice(vert, caras)
    centro = centro_de_masa(vert, caras)
    adentro = ((vert - centro) * normales).sum(1) < 0
    fraccion = float(adentro.mean())
    if lados == "auto":
        lados = "adentro" if 0.2 <= fraccion <= 0.8 else "ambos"
    falta = pared - espesor
    corrimiento = normales * factor_parejo(vert, caras, normales)[:, None]
    nuevos = vert.copy()
    if lados == "adentro":
        nuevos[adentro] += corrimiento[adentro] * falta
    else:
        nuevos += corrimiento * (falta / 2)

    voxel = voxel or float(np.clip(pared / 8, 0.15, 0.5))
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    # Los voxels de Blender rellenan los huecos cerrados: en una figura cerrada y hueca por dentro, la superficie de
    # afuera y la del hueco se rehacen por separado y el hueco se resta después (una máscara abierta es una sola).
    _, posicion = np.unique(componentes(caras, len(vert))[caras[:, 0]], return_inverse=True)
    a, b, c = nuevos[caras[:, 0]], nuevos[caras[:, 1]], nuevos[caras[:, 2]]
    volumen_partes = np.bincount(posicion, weights=np.einsum("ij,ij->i", a, np.cross(b, c))) / 6
    huecos = volumen_partes[posicion] < 0
    rehecha = rehacer(nuevos, caras[~huecos], voxel)
    if huecos.any():
        hueco = rehacer(nuevos, caras[huecos][:, ::-1], voxel)       # dado vuelta: el hueco como sólido
        rehecha = triangulos_manifold(a_manifold(rehecha) - a_manifold(hueco))
    v2, c2 = soldar(rehecha, decimales=5)
    if len(c2) > caras_max:
        obj2 = malla_blender("rehecha", v2, c2)
        dec = obj2.modifiers.new("simplificar", "DECIMATE")
        dec.decimate_type = "COLLAPSE"
        dec.ratio = caras_max / len(c2)
        rehecha = triangulos_de(obj2)
        v2, c2 = soldar(rehecha, decimales=5)
    c2, sobras, volumen_sobras = quitar_sobras(v2, c2)
    rehecha = v2[c2]
    vol2, area2 = volumen_y_area(v2, c2)

    # cuánto se movió la cara de afuera: distancia de sus vértices a la malla nueva
    arbol = BVHTree.FromPolygons([tuple(p) for p in v2], [tuple(int(i) for i in c) for c in c2], all_triangles=True)
    afuera = np.flatnonzero(~adentro) if lados == "adentro" else np.arange(len(vert))
    muestra = np.random.default_rng(1).choice(afuera, min(3000, len(afuera)), replace=False)
    dist = np.array([arbol.find_nearest(tuple(vert[i]))[3] for i in muestra])
    info.update(
        cambio=True, lados=lados, voxel_mm=round(voxel, 3), fraccion_adentro=round(fraccion, 2),
        espesor_despues_mm=round(2 * abs(vol2) / area2, 2), caras_despues=int(len(c2)),
        volumen_cm3=round(abs(vol2) / 1000, 2), sobras_sacadas=sobras,
        volumen_sobras_mm3=round(volumen_sobras, 1),
        cara_de_afuera_movida_mm={"mediana": round(float(np.median(dist)), 3),
                                  "p95": round(float(np.percentile(dist, 95)), 3)},
    )
    return info | {"triangulos": rehecha}


def main(argv=None) -> None:
    a = argparse.ArgumentParser(description="Engrosa una cáscara fina (modelos de IA) sin tocar la cara de afuera.")
    a.add_argument("--stl", type=Path, required=True)
    a.add_argument("--salida", type=Path, required=True)
    a.add_argument("--pared", type=float, default=2.0, help="espesor de pared buscado en mm (2 por defecto)")
    a.add_argument("--voxel", type=float, help="tamaño del voxel en mm (por defecto pared/8, entre 0,15 y 0,5)")
    a.add_argument("--caras", type=int, default=600_000, help="máximo de triángulos de la malla final")
    a.add_argument("--lados", choices=["auto", "adentro", "ambos"], default="auto")
    a.add_argument("--json", type=Path)
    args = a.parse_args(argv)
    if not args.stl.exists():
        raise SystemExit(f"No existe {args.stl}")
    if not 0.4 <= args.pared <= 20:
        raise SystemExit("La pared tiene que estar entre 0,4 y 20 mm (no se escribió nada).")
    try:
        import bpy  # noqa: F401
    except ImportError:
        print("Falta Blender para Python: pip install --break-system-packages bpy (unos 400 MB).")
        sys.exit(2)
    t0 = time.time()
    try:
        info = engrosar(leer_stl(args.stl), args.pared, args.voxel, args.caras, args.lados)
    except ValueError as error:
        raise SystemExit(f"{error} (no se escribió nada)")
    tri = info.pop("triangulos")
    info["segundos"] = round(time.time() - t0)
    if info["cambio"]:
        escribir_stl(args.salida, tri, "taller-3d: engrosada")
        movida = info["cara_de_afuera_movida_mm"]
        print(f"Pared: {info['espesor_antes_mm']} mm → {info['espesor_despues_mm']} mm "
              f"(engrosada {'hacia adentro' if info['lados'] == 'adentro' else 'para los dos lados'}, "
              f"voxel {info['voxel_mm']} mm).")
        print(f"Cara de afuera: se movió {movida['mediana']} mm en la mitad de los puntos y hasta {movida['p95']} mm "
              f"en el 95 %.")
        print(f"Triángulos: {info['caras_antes']} → {info['caras_despues']} | volumen {info['volumen_cm3']} cm³ | "
              f"{info['segundos']} s")
        if info["sobras_sacadas"]:
            cuanto = (f"{info['volumen_sobras_mm3']:g} mm³ en total" if info["volumen_sobras_mm3"] >= 0.1
                      else "casi sin volumen")
            print(f"Saqué {info['sobras_sacadas']} sobras de los voxels (islas o burbujas, {cuanto}).")
        print(f"Guardada en {args.salida}")
    else:
        print(f"No hizo falta engrosar: {info['motivo']}. No se escribió nada.")
    if args.json:
        args.json.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
