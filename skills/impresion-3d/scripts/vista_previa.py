#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
"""Vista previa de un STL en PNG: perspectiva, frente, costado y planta, con medidas.

Uso:
  python3 vista_previa.py pieza.stl vista.png [--titulo "Soporte en L"]
  python3 vista_previa.py pieza.stl foto_producto.png --producto --color rojo   # imagen para la tienda (sin Blender)

Requiere: pip install --break-system-packages numpy matplotlib
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from revisar_stl import leer_stl  # noqa: E402

MAX_TRIANGULOS = 60000


def subdividir(tri: np.ndarray, largo_max: float, limite: int = MAX_TRIANGULOS) -> np.ndarray:
    """Parte los triángulos largos para que matplotlib los ordene bien por profundidad."""
    for _ in range(14):
        aristas = np.stack([np.linalg.norm(tri[:, (i + 1) % 3] - tri[:, i], axis=1) for i in range(3)], axis=1)
        k = aristas.argmax(axis=1)
        grandes = aristas.max(axis=1) > largo_max
        if not grandes.any() or len(tri) + int(grandes.sum()) > limite:
            break
        t, kk = tri[grandes], k[grandes]
        orden = np.stack([kk, (kk + 1) % 3, (kk + 2) % 3], axis=1)
        t = np.take_along_axis(t, orden[:, :, None].repeat(3, axis=2), axis=1)
        medio = (t[:, 0] + t[:, 1]) / 2
        a = np.stack([t[:, 0], medio, t[:, 2]], axis=1)
        b = np.stack([medio, t[:, 1], t[:, 2]], axis=1)
        tri = np.concatenate([tri[~grandes], a, b])
    return tri


def _colores(tri: np.ndarray, luz=(0.4, -0.6, 0.7)) -> np.ndarray:
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    largo = np.linalg.norm(n, axis=1, keepdims=True)
    n = np.divide(n, largo, out=np.zeros_like(n), where=largo > 0)
    luz = np.asarray(luz) / np.linalg.norm(luz)
    brillo = 0.35 + 0.65 * np.clip(n @ luz, 0, 1)
    base = np.array([0.18, 0.47, 0.71])
    return np.clip(base[None, :] * brillo[:, None] + 0.12, 0, 1)


COLORES = {
    "negro": "#2b2b2b", "blanco": "#f0f0f0", "gris": "#8a8d91", "rojo": "#c62828", "azul": "#1f5fbf",
    "verde": "#2e7d32", "amarillo": "#f2c40f", "naranja": "#ef6c00", "violeta": "#6a1b9a", "rosa": "#e57399",
    "celeste": "#4fb3e8", "marron": "#6d4c41", "marrón": "#6d4c41", "dorado": "#c9a227", "plateado": "#b8bcc2",
    "natural": "#e8e2d0", "transparente": "#cfe3ea",
}
LEYENDA_PRODUCTO = "Imagen ilustrativa (render 3D)"


def color_rgb(color: str | None) -> np.ndarray:
    """Color del filamento: nombre en español (negro, rojo...) o #RRGGBB."""
    texto = (color or "azul").strip().lower()
    for nombre, valor in COLORES.items():
        if texto == nombre or texto.startswith(nombre + " "):
            texto = valor
            break
    if not re.fullmatch(r"#?[0-9a-f]{6}", texto):
        raise SystemExit(f"Color desconocido: {color}. Usá un nombre ({', '.join(sorted(COLORES))}) o #RRGGBB.")
    texto = texto.lstrip("#")
    return np.array([int(texto[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def renderizar_producto(stl: Path, salida: Path, color: str | None = None, fondo: str = "#ffffff",
                        leyenda: bool = False) -> Path:
    """Una sola vista en perspectiva, del color del filamento, para la ficha de la tienda.

    Fondo blanco y la pieza en el 80 % del cuadro, sin texto (Mercado Libre no admite texto en las fotos): la
    descripción aclara que es ilustrativa. leyenda=True agrega "Imagen ilustrativa (render 3D)" abajo, para
    tiendas propias. No reemplaza la foto de la pieza impresa. Si hay Blender, render_producto.py sale mejor.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    tri = leer_stl(stl)
    if len(tri) > MAX_TRIANGULOS:
        tri = tri[::int(np.ceil(len(tri) / MAX_TRIANGULOS))]
    pts = tri.reshape(-1, 3)
    minimo, maximo = pts.min(axis=0), pts.max(axis=0)
    medidas = maximo - minimo
    tri = subdividir(tri, float(medidas.max()) / 60 or 1.0)
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    largo = np.linalg.norm(n, axis=1, keepdims=True)
    n = np.divide(n, largo, out=np.zeros_like(n), where=largo > 0)
    # Normales hacia afuera (si la malla viene dada vuelta, se corrige) y sin caras traseras:
    # así matplotlib no dibuja bordes de atrás que se ven como rayas oscuras.
    volumen = float(np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum())
    if volumen < 0:
        n = -n
    elev, azim = np.radians(24), np.radians(-58)
    ojo = np.array([np.cos(elev) * np.cos(azim), np.cos(elev) * np.sin(azim), np.sin(elev)])
    visibles = n @ ojo > 1e-6
    tri, n = tri[visibles], n[visibles]
    luz1 = np.array([0.5, -0.7, 0.8]) / np.linalg.norm([0.5, -0.7, 0.8])
    luz2 = np.array([-0.6, 0.3, 0.4]) / np.linalg.norm([-0.6, 0.3, 0.4])
    brillo = 0.30 + 0.58 * np.clip(n @ luz1, 0, 1) + 0.20 * np.clip(n @ luz2, 0, 1)
    base = color_rgb(color)
    colores = np.clip(base[None, :] * brillo[:, None] + 0.05 * brillo[:, None], 0, 1)

    centro = (minimo + maximo) / 2
    lado = float(medidas.max()) * 0.52 or 1.0
    fig = plt.figure(figsize=(8, 8), dpi=150)
    fig.patch.set_facecolor(fondo)
    ax = fig.add_axes((0, 0.03, 1, 0.97), projection="3d")
    ax.set_facecolor(fondo)
    ax.add_collection3d(Poly3DCollection(tri, facecolors=colores, edgecolors=colores, linewidths=0.1, antialiased=False))
    ax.set_xlim(centro[0] - lado, centro[0] + lado)
    ax.set_ylim(centro[1] - lado, centro[1] + lado)
    ax.set_zlim(centro[2] - lado, centro[2] + lado)
    try:
        ax.set_box_aspect((1, 1, 1), zoom=1.25)
    except TypeError:
        ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=24, azim=-58)
    ax.set_axis_off()
    salida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(salida, facecolor=fondo)
    plt.close(fig)
    _encuadrar(salida, fondo, leyenda=leyenda)
    return salida


def _encuadrar(png: Path, fondo: str, lado: int = 1200, margen: float = 0.10, leyenda: bool = False) -> None:
    """Recorta el fondo sobrante y centra la pieza en un cuadrado (80 % del lado); la leyenda, si se pide."""
    from PIL import Image, ImageChops, ImageDraw, ImageFont

    img = Image.open(png).convert("RGB")
    color_fondo = tuple(int(fondo.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    diferencia = ImageChops.difference(img, Image.new("RGB", img.size, color_fondo)).convert("L")
    caja = diferencia.point(lambda v: 255 if v > 12 else 0).getbbox()
    if caja:
        img = img.crop(caja)
    escala = (lado * (1 - 2 * margen)) / max(img.size)
    img = img.resize((max(1, round(img.width * escala)), max(1, round(img.height * escala))), Image.LANCZOS)
    lienzo = Image.new("RGB", (lado, lado), color_fondo)
    lienzo.paste(img, ((lado - img.width) // 2, (lado - img.height) // 2))
    if not leyenda:
        lienzo.save(png)
        return
    dibujo = ImageDraw.Draw(lienzo)
    try:
        fuente = ImageFont.truetype("DejaVuSans.ttf", 18)
    except OSError:
        fuente = ImageFont.load_default()
    ancho = dibujo.textlength(LEYENDA_PRODUCTO, font=fuente)
    dibujo.text((lado - ancho - 20, lado - 34), LEYENDA_PRODUCTO, fill=(154, 160, 166), font=fuente)
    lienzo.save(png)


def renderizar(stl: Path, salida: Path, titulo: str | None = None) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    tri = leer_stl(stl)
    if len(tri) > MAX_TRIANGULOS:
        paso = int(np.ceil(len(tri) / MAX_TRIANGULOS))
        tri = tri[::paso]
    pts = tri.reshape(-1, 3)
    minimo, maximo = pts.min(axis=0), pts.max(axis=0)
    medidas = maximo - minimo
    tri = subdividir(tri, float(medidas.max()) / 40 or 1.0)
    centro = (minimo + maximo) / 2
    lado = float(medidas.max()) * 0.55 or 1.0
    colores = _colores(tri)

    vistas = [("Perspectiva", 25, -55), ("Frente", 0, -90), ("Costado", 0, 0), ("Planta", 90, -90)]
    fig = plt.figure(figsize=(11, 8.5), dpi=110)
    for i, (nombre, elev, azim) in enumerate(vistas, 1):
        ax = fig.add_subplot(2, 2, i, projection="3d")
        coleccion = Poly3DCollection(tri, facecolors=colores, edgecolors=colores, linewidths=0.15, antialiased=False)
        ax.add_collection3d(coleccion)
        ax.set_xlim(centro[0] - lado, centro[0] + lado)
        ax.set_ylim(centro[1] - lado, centro[1] + lado)
        ax.set_zlim(centro[2] - lado, centro[2] + lado)
        ax.set_box_aspect((1, 1, 1))
        ax.view_init(elev=elev, azim=azim)
        ax.set_title(nombre, fontsize=11)
        ax.set_xlabel("X (mm)", fontsize=8)
        ax.set_ylabel("Y (mm)", fontsize=8)
        ax.set_zlabel("Z (mm)", fontsize=8)
        ax.tick_params(labelsize=7)
    encabezado = titulo or stl.stem
    fig.suptitle(f"{encabezado} — {medidas[0]:.1f} × {medidas[1]:.1f} × {medidas[2]:.1f} mm", fontsize=13)
    fig.tight_layout()
    salida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(salida)
    plt.close(fig)
    return salida


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Vista previa de un STL en PNG.")
    ap.add_argument("stl", type=Path)
    ap.add_argument("png", type=Path)
    ap.add_argument("--titulo")
    ap.add_argument("--producto", action="store_true",
                    help="una sola vista del color del filamento, para la tienda (fondo blanco, sin texto)")
    ap.add_argument("--leyenda", action="store_true",
                    help="con --producto: agrega «Imagen ilustrativa (render 3D)» abajo (Mercado Libre no admite texto)")
    ap.add_argument("--color", help="con --producto: color del filamento (nombre o #RRGGBB)")
    a = ap.parse_args(argv)
    if a.producto:
        print(renderizar_producto(a.stl, a.png, a.color, leyenda=a.leyenda))
    else:
        print(renderizar(a.stl, a.png, a.titulo))


if __name__ == "__main__":
    main()
