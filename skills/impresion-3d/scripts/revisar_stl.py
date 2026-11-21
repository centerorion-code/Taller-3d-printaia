#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
"""Revisión de una malla STL antes de laminar.

Revisa que la malla sea cerrada y válida, mide la pieza, verifica que entre en la cama,
estima la superficie de apoyo, marca voladizos que pueden necesitar soporte y compara
con las medidas esperadas. Opcionalmente rota, apoya y centra la pieza y la guarda.

Uso:
  python3 revisar_stl.py pieza.stl [--impresora ender-3-v3-plus] [--material PETG]
         [--esperado 40x20x10] [--tolerancia 0.2] [--umbral-voladizo 45]
         [--rotar 90,0,0] [--apoyar] [--centrar] [--salida pieza_orientada.stl]
         [--json informe.json]

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

    # Malla cerrada y orientada
    claves = np.round(pts / 1e-4).astype(np.int64)
    _, idx = np.unique(claves, axis=0, return_inverse=True)
    caras = idx.reshape(-1, 3)
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
                    "hay que partirla o escalarla.")

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
        "peso_macizo_g": round(gramos_macizo, 1),
        "cerrada": bordes_abiertos == 0 and no_manifold == 0,
        "entra_en_cama": entra,
        "rotacion_sugerida": list(sugerencia) if sugerencia else None,
        "apoyo_cm2": round(area_apoyo / 100, 2),
        "voladizo_cm2": round(area_voladizo / 100, 2),
        "voladizo_z_mm": zonas,
        "hallazgos": hallazgos,
    }


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
    if r["hallazgos"]:
        lineas.append("Hallazgos:")
        etiqueta = {RECHAZO: "[RECHAZO]", ADVERTENCIA: "[ADVERTENCIA]"}
        for h in sorted(r["hallazgos"], key=lambda h: h["gravedad"] != RECHAZO):
            lineas.append(f"  {etiqueta[h['gravedad']]} {h['mensaje']}")
    return "\n".join(lineas)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Revisión de una malla STL.")
    ap.add_argument("stl", type=Path)
    ap.add_argument("--impresora", default="ender-3-v3-plus",
                    help="datos de la impresora; 'ninguna' para no revisar la cama (solo diseño)")
    ap.add_argument("--material")
    ap.add_argument("--esperado", help="medidas esperadas, por ejemplo 40x20x10")
    ap.add_argument("--tolerancia", type=float, default=0.2)
    ap.add_argument("--umbral-voladizo", type=float, default=45.0)
    ap.add_argument("--rotar", help="grados en X,Y,Z, por ejemplo 90,0,0")
    ap.add_argument("--apoyar", action="store_true", help="bajar la pieza hasta Z=0")
    ap.add_argument("--centrar", action="store_true", help="centrar la pieza en la cama")
    ap.add_argument("--salida", type=Path, help="guardar la malla transformada")
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)

    impresora = None if a.impresora.lower() in ("ninguna", "none", "-") else comun.cargar_impresora(a.impresora)
    if a.centrar and not impresora:
        raise SystemExit("--centrar necesita una impresora (--impresora <datos>).")
    tri = leer_stl(a.stl)
    if a.rotar:
        tri = rotar(tri, [float(v) for v in a.rotar.split(",")])
    if a.apoyar or a.centrar or a.rotar:
        tri = tri - np.array([0.0, 0.0, tri[:, :, 2].min()])
    if a.centrar:
        ar = impresora["area"]
        centro = np.array([(ar["x_min"] + ar["x_max"]) / 2, (ar["y_min"] + ar["y_max"]) / 2])
        pts = tri.reshape(-1, 3)
        actual = (pts[:, :2].min(axis=0) + pts[:, :2].max(axis=0)) / 2
        tri = tri + np.array([*(centro - actual), 0.0])
    esperado = [float(v) for v in a.esperado.lower().replace("×", "x").split("x")] if a.esperado else None
    r = analizar(tri, impresora, a.material, esperado, a.tolerancia, a.umbral_voladizo)
    if a.salida:
        escribir_stl(a.salida, tri)
        r["salida"] = str(a.salida)
    print(informe_texto(r, a.stl.name))
    if a.json:
        a.json.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    comun.salir(r["estado"])


if __name__ == "__main__":
    main()
