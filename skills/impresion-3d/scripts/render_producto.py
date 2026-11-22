#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
"""Fotos de producto de una pieza, renderizadas con Blender (el módulo bpy) en el espacio de Claude.

La pieza va con un material de plástico del color y el tipo de filamento (PETG brillante, PLA satinado),
líneas de capa sutiles y tres luces de estudio. Por defecto salen cuatro fotos desde ángulos distintos,
cuadradas y sin texto, numeradas en el orden de la galería:
  producto-1-principal.jpg  a tres cuartos, fondo blanco puro y sin sombra (la primera foto de Mercado Libre)
  producto-2-atras.jpg      a tres cuartos desde el otro lado, fondo blanco con sombra
  producto-3-frente.jpg     de frente, fondo blanco con sombra
  producto-4-arriba.jpg     desde arriba, fondo blanco con sombra
  producto-5-tienda.jpg     solo si se pide: el ángulo de la principal con fondo claro cálido (redes)
La pieza ocupa el 80 % del cuadro. Son imágenes ilustrativas: la descripción lo aclara hasta que haya
fotos reales de la pieza impresa.

Requiere: pip install --break-system-packages bpy pillow   (bpy pesa unos 400 MB; una vez por conversación)

En la PC, si está el conector de Blender: renderizar_crudos() corre en el Blender del usuario, en segundo plano y
una vista por llamada (con un i5 de 6 núcleos, unas 3 veces más rápido que acá), y deja los renders en crudo;
después, acá, --desde-crudos arma las fotos con Pillow, que el Blender de la PC no trae.
Uso:
  python3 -I render_producto.py --stl pieza.stl --salida <carpeta de la pieza>/producto --color azul \\
      [--material PETG] [--capa 0.2] [--tomas principal,atras,frente,arriba] [--tam 1200] [--muestras 16]
Cada ángulo se renderiza una vez (principal y tienda comparten el mismo): con 2 núcleos, 1200 px y
16 muestras, las cuatro tardan unos 7 minutos.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
import time
from pathlib import Path

COLORES = {
    "negro": "#242424", "blanco": "#EDEDED", "gris": "#8A8D91", "plateado": "#B8BCC2", "rojo": "#C62828",
    "azul": "#1F5FD6", "celeste": "#4FA3E0", "verde": "#2E8B57", "amarillo": "#F2C200", "naranja": "#F26A1B",
    "violeta": "#7B3FBF", "rosa": "#E86A9E", "marron": "#7A4B2A", "marrón": "#7A4B2A", "dorado": "#C9A227",
    "beige": "#D8C3A0", "natural": "#E6DCC8", "turquesa": "#1BA6A6", "lila": "#B79CD9", "bordo": "#7B1E2B",
    "transparente": "#DDE6EA", "black": "#242424", "white": "#EDEDED", "grey": "#8A8D91", "gray": "#8A8D91",
    "red": "#C62828", "blue": "#1F5FD6", "green": "#2E8B57", "yellow": "#F2C200", "orange": "#F26A1B",
}
BRILLO = {"PETG": 0.28, "PLA": 0.42, "ABS": 0.5, "ASA": 0.55, "TPU": 0.6, "PC": 0.3, "PA": 0.55}
VISTAS = {  # vista: (azimut de la cámara, elevación, giro de la pieza), en grados
    # el otro lado se muestra girando la pieza y no la cámara: la luz y la sombra quedan iguales
    "tres_cuartos": (-38, 24, 0), "atras": (-38, 24, 180), "frente": (0, 8, 0), "arriba": (-30, 62, 0),
}
TOMAS = {  # toma: (vista, fondo, archivo); el número del archivo es el orden en la galería
    "principal": ("tres_cuartos", "blanco_sin_sombra", "producto-1-principal.jpg"),
    "atras": ("atras", "blanco", "producto-2-atras.jpg"),
    "frente": ("frente", "blanco", "producto-3-frente.jpg"),
    "arriba": ("arriba", "blanco", "producto-4-arriba.jpg"),
    "tienda": ("tres_cuartos", "calido", "producto-5-tienda.jpg"),
}
TOMAS_POR_DEFECTO = ["principal", "atras", "frente", "arriba"]   # cuatro ángulos distintos para la galería
# De espaldas, lo que queda detrás (la base de un soporte) mira a la contraluz y se quema: se baja.
CONTRALUZ = {"atras": 0.4}


COLOR_POR_DEFECTO = "#8A8D91"   # gris neutro si el color no se reconoce (y se avisa)


def color_de(texto: str) -> str:
    """#RRGGBB del color dicho: el nombre que aparece primero (\"verde azulado\" es verde)."""
    t = (texto or "").strip().lower()
    if t.startswith("#") and len(t) == 7:
        return t
    hallados = sorted((t.find(n), -len(n), v) for n, v in COLORES.items() if n in t)
    return hallados[0][2] if hallados else COLOR_POR_DEFECTO


def rugosidad(material: str | None, color: str | None) -> float:
    r = BRILLO.get((material or "").upper(), 0.4)
    t = (color or "").lower()
    if "mate" in t:
        r = 0.72
    if "seda" in t or "silk" in t:
        r = 0.15
    return r


# ------------------------------------------------------------------ composición (sin Blender)

def componer(render, mascara, fondo: str, lado: int = 1200, ocupacion: float = 0.80):
    """Pone el render (RGBA, con la sombra en el alfa) sobre el fondo, con la pieza al 80 % del cuadro.

    mascara: render del mismo cuadro sin el piso (su alfa es solo la pieza).
    fondo: blanco_sin_sombra | blanco | calido.
    """
    from PIL import Image, ImageChops

    render, mascara = render.convert("RGBA"), mascara.convert("RGBA")
    alfa_pieza = mascara.split()[3]
    caja = alfa_pieza.point(lambda a: 255 if a > 128 else 0).getbbox()
    if not caja:
        raise ValueError("La pieza no aparece en el render.")
    escala = lado * ocupacion / max(caja[2] - caja[0], caja[3] - caja[1])
    tam = (max(1, round(render.width * escala)), max(1, round(render.height * escala)))
    if fondo == "blanco_sin_sombra":
        r, g, b, _ = render.split()
        capa = Image.merge("RGBA", (r, g, b, alfa_pieza))
    else:
        r, g, b, a = render.split()
        a = a.point(lambda v: max(0, round((v - 8) * 255 / 247)))   # sin velo ni escalón: el fondo queda parejo
        capa = Image.merge("RGBA", (r, g, b, a))
    capa = capa.resize(tam, Image.LANCZOS)
    cx, cy = (caja[0] + caja[2]) / 2 * escala, (caja[1] + caja[3]) / 2 * escala
    if fondo == "calido":
        base = Image.new("RGBA", (lado, lado))
        for y in range(lado):
            t = y / lado
            base.paste((round(246 - 18 * t), round(243 - 18 * t), round(238 - 18 * t), 255), (0, y, lado, y + 1))
    else:
        base = Image.new("RGBA", (lado, lado), (255, 255, 255, 255))
    lienzo = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    pos = (round(lado / 2 - cx), round(lado / 2 - cy))
    lienzo.paste(capa, pos)
    if fondo != "blanco_sin_sombra":                    # la sombra se apaga antes del borde: el borde queda limpio
        pieza = Image.new("L", (lado, lado), 0)
        pieza.paste(alfa_pieza.resize(tam, Image.LANCZOS), pos)
        r, g, b, a = lienzo.split()
        a = ImageChops.lighter(pieza, ImageChops.multiply(a, _borde_suave(lado)))
        lienzo = Image.merge("RGBA", (r, g, b, a))
    base.alpha_composite(lienzo)
    return base.convert("RGB")


def _borde_suave(lado: int, banda: float = 0.09):
    """Máscara que vale 255 en el centro y baja suave a 0 en la franja de los bordes."""
    from PIL import Image, ImageChops

    ancho = max(1, round(lado * banda))

    def valor(i: int) -> int:
        d = max(0.0, min(1.0, min(i, lado - 1 - i) / ancho))
        return round(255 * d * d * (3 - 2 * d))

    fila = Image.new("L", (lado, 1))
    fila.putdata([valor(i) for i in range(lado)])
    fx = fila.resize((lado, lado), Image.NEAREST)
    return ImageChops.darker(fx, fx.transpose(getattr(Image, "Transpose", Image).TRANSPOSE))


# ------------------------------------------------------------------ escena de Blender

def _escena(stl: Path, color_hex: str, rug: float, capa_mm: float):
    import bpy
    import mathutils

    bpy.ops.wm.read_factory_settings(use_empty=True)
    escena = bpy.context.scene
    try:
        bpy.ops.wm.stl_import(filepath=str(stl))
    except AttributeError:                              # Blender 4.0 o anterior
        bpy.ops.import_mesh.stl(filepath=str(stl))
    pieza = bpy.context.selected_objects[0]
    bpy.context.view_layer.objects.active = pieza
    esquinas = [pieza.matrix_world @ mathutils.Vector(c) for c in pieza.bound_box]
    mn = mathutils.Vector([min(v[i] for v in esquinas) for i in range(3)])
    mx = mathutils.Vector([max(v[i] for v in esquinas) for i in range(3)])
    k = 2.0 / max(mx - mn)                              # la pieza mide 2 unidades en su lado mayor
    pieza.location = (-(mn.x + mx.x) / 2 * k, -(mn.y + mx.y) / 2 * k, -mn.z * k)
    pieza.scale = (k, k, k)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    if hasattr(bpy.ops.object, "shade_smooth_by_angle"):
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(30))
    alto = (mx.z - mn.z) * k

    h = color_hex.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lineal = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    mat = bpy.data.materials.new("plastico")
    if mat.node_tree is None:                          # Blender 4 (en el 5 los materiales ya traen nodos)
        mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*lineal, 1.0)
    bsdf.inputs["Roughness"].default_value = rug
    coord, sep = nt.nodes.new("ShaderNodeTexCoord"), nt.nodes.new("ShaderNodeSeparateXYZ")
    mult = nt.nodes.new("ShaderNodeMath")
    mult.operation = "MULTIPLY"
    mult.inputs[1].default_value = 2 * math.pi / (capa_mm * k)      # una onda por capa
    seno = nt.nodes.new("ShaderNodeMath")
    seno.operation = "SINE"
    relieve = nt.nodes.new("ShaderNodeBump")
    relieve.inputs["Strength"].default_value = 0.35
    relieve.inputs["Distance"].default_value = capa_mm * k * 0.25
    nt.links.new(coord.outputs["Object"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], mult.inputs[0])
    nt.links.new(mult.outputs[0], seno.inputs[0])
    nt.links.new(seno.outputs[0], relieve.inputs["Height"])
    nt.links.new(relieve.outputs["Normal"], bsdf.inputs["Normal"])
    pieza.data.materials.append(mat)

    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
    piso = bpy.context.active_object
    piso.is_shadow_catcher = True

    def luz(nombre, pos, energia, tam):
        datos = bpy.data.lights.new(nombre, "AREA")
        datos.energy, datos.size = energia, tam
        o = bpy.data.objects.new(nombre, datos)
        escena.collection.objects.link(o)
        o.location = pos
        o.rotation_euler = (mathutils.Vector((0, 0, alto / 2)) - mathutils.Vector(pos)).to_track_quat("-Z", "Y").to_euler()

    luz("principal", (-3.5, -3.0, 4.5), 420, 3.0)
    luz("relleno", (4.0, -2.5, 2.0), 140, 4.0)
    luz("contra", (0.5, 4.5, 3.5), 320, 2.5)
    mundo = bpy.data.worlds.new("mundo")
    escena.world = mundo
    if mundo.node_tree is None:
        mundo.use_nodes = True
    fondo = mundo.node_tree.nodes["Background"]
    fondo.inputs["Color"].default_value = (0.9, 0.9, 0.9, 1)
    fondo.inputs["Strength"].default_value = 0.18

    camara = bpy.data.objects.new("camara", bpy.data.cameras.new("camara"))
    camara.data.lens = 70
    escena.collection.objects.link(camara)
    escena.camera = camara
    escena.render.engine = "CYCLES"
    escena.cycles.device = "CPU"
    escena.render.film_transparent = True
    escena.render.use_persistent_data = True
    escena.render.image_settings.file_format = "PNG"
    escena.render.image_settings.color_mode = "RGBA"
    escena.view_settings.view_transform = "Standard"
    radio = max(((mx - mn) * k).length / 2, 0.5)
    return escena, camara, piso, mathutils.Vector((0, 0, alto / 2)), radio


def _apuntar(camara, centro, radio, vista: str, pieza=None, escena=None, borde: float = 0.39):
    """Pone la cámara en la vista y la acerca hasta que la pieza llegue a `borde` del centro del cuadro
    (0,39 ≈ la pieza en el 78 % del render, que después se recorta al 80 % de la foto sin agrandarla)."""
    import bpy
    import mathutils
    az, el = (math.radians(x) for x in VISTAS[vista][:2])
    fov = 2 * math.atan(36 / 2 / camara.data.lens)
    direccion = mathutils.Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)))

    def colocar(d):
        camara.location = centro + d * direccion
        camara.rotation_euler = (centro - camara.location).to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update()

    dist = radio / math.sin(fov / 2) * 1.45
    colocar(dist)
    if pieza is None or escena is None:
        return
    from bpy_extras.object_utils import world_to_camera_view
    vertices = pieza.data.vertices
    paso = max(1, len(vertices) // 4000)
    puntos = [pieza.matrix_world @ vertices[i].co for i in range(0, len(vertices), paso)]
    for _ in range(4):
        proy = [world_to_camera_view(escena, camara, p) for p in puntos]
        lejos = max(max(abs(q.x - 0.5), abs(q.y - 0.5)) for q in proy)
        if lejos <= 0:
            break
        nueva = dist * lejos / borde
        if abs(nueva - dist) < dist * 0.01:
            break
        dist = max(nueva, radio * 1.05)                 # nunca adentro de la pieza
        colocar(dist)


def vistas_de(tomas: list[str]) -> list[str]:
    """Las vistas que hay que renderizar para esas tomas, en orden y sin repetir (principal y tienda comparten)."""
    malas = [t for t in tomas if t not in TOMAS]
    if malas:
        raise ValueError(f"Tomas desconocidas: {', '.join(malas)} (hay {', '.join(TOMAS)}).")
    return list(dict.fromkeys(TOMAS[t][0] for t in tomas))


def _usar_gpu(escena) -> str:
    """Si Blender encuentra una placa de video para Cycles, renderiza con ella. Devuelve qué quedó usando."""
    import bpy
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
    except (KeyError, AttributeError):
        return "CPU"
    for tipo in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
        try:
            prefs.compute_device_type = tipo
            prefs.get_devices()
        except (TypeError, ValueError, RuntimeError):
            continue
        gpus = [d for d in prefs.devices if d.type == tipo]
        if gpus:
            for d in prefs.devices:
                d.use = d.type == tipo
            escena.cycles.device = "GPU"
            return f"{tipo}: {', '.join(d.name for d in gpus)}"
    return "CPU"


def renderizar_crudos(stl, carpeta, vistas: list[str], color: str = "", material: str | None = None,
                      capa_mm: float = 0.2, lado: int = 1200, muestras: int = 16, gpu: bool = False) -> dict:
    """Solo Blender, sin Pillow: deja <vista>.png (con el piso que atrapa la sombra) y <vista>-mascara.png (solo
    la pieza) en `carpeta`. Es lo que corre en el Blender de la PC por el conector de Blender, una vista por
    llamada; después componer_tomas() arma las fotos en el espacio de Claude."""
    import bpy
    malas = [v for v in vistas if v not in VISTAS]
    if malas:
        raise ValueError(f"Vistas desconocidas: {', '.join(malas)} (hay {', '.join(VISTAS)}).")
    if capa_mm <= 0:
        raise ValueError("La altura de capa tiene que ser mayor que cero.")
    t0 = time.time()
    escena, camara, piso, centro, radio = _escena(Path(stl), color_de(color), rugosidad(material, color), capa_mm)
    dispositivo = _usar_gpu(escena) if gpu else "CPU"
    pieza = next(o for o in escena.objects if o.type == "MESH" and not o.is_shadow_catcher)
    escena.render.resolution_x = escena.render.resolution_y = round(lado * 1.1)
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    contra = escena.objects.get("contra")
    energia_contra = contra.data.energy if contra else 0
    crudos = []
    for vista in vistas:
        pieza.rotation_euler = (0, 0, math.radians(VISTAS[vista][2]))
        if contra:
            contra.data.energy = energia_contra * CONTRALUZ.get(vista, 1.0)
        _apuntar(camara, centro, radio, vista, pieza, escena)
        piso.hide_render = False
        escena.cycles.samples, escena.cycles.use_denoising = muestras, True
        escena.render.filepath = str(carpeta / f"{vista}.png")
        bpy.ops.render.render(write_still=True)
        piso.hide_render = True                         # la máscara: solo la pieza
        escena.cycles.samples, escena.cycles.use_denoising = 16, False
        escena.render.filepath = str(carpeta / f"{vista}-mascara.png")
        bpy.ops.render.render(write_still=True)
        crudos += [str(carpeta / f"{vista}.png"), str(carpeta / f"{vista}-mascara.png")]
    return {"crudos": crudos, "segundos": round(time.time() - t0, 1), "dispositivo": dispositivo,
            "blender": bpy.app.version_string}


def componer_tomas(carpeta, salida, tomas: list[str], lado: int = 1200) -> list[str]:
    """Solo Pillow, sin Blender: arma las fotos de las tomas con los renders crudos de `carpeta`."""
    from PIL import Image

    carpeta, salida = Path(carpeta), Path(salida)
    faltan = [v for v in vistas_de(tomas)
              if not (carpeta / f"{v}.png").exists() or not (carpeta / f"{v}-mascara.png").exists()]
    if faltan:
        raise ValueError(f"Faltan los renders de {', '.join(faltan)} en {carpeta} "
                         "(<vista>.png y <vista>-mascara.png).")
    salida.mkdir(parents=True, exist_ok=True)
    archivos = []
    for toma in tomas:
        vista, fondo, nombre = TOMAS[toma]
        with Image.open(carpeta / f"{vista}.png") as render, Image.open(carpeta / f"{vista}-mascara.png") as mascara:
            componer(render, mascara, fondo, lado).save(salida / nombre, quality=92)
        archivos.append(str(salida / nombre))
    return archivos


def renderizar(stl: Path, salida: Path, color: str = "", material: str | None = None, capa_mm: float = 0.2,
               tomas: list[str] | None = None, lado: int = 1200, muestras: int = 16) -> dict:
    """Todo en el espacio de Claude: los renders con bpy y las fotos con Pillow."""
    tomas = tomas or list(TOMAS_POR_DEFECTO)
    vistas = vistas_de(tomas)
    with tempfile.TemporaryDirectory() as tmp:
        r = renderizar_crudos(stl, tmp, vistas, color, material, capa_mm, lado, muestras)
        archivos = componer_tomas(tmp, salida, tomas, lado)
    return {"archivos": archivos, "segundos": round(r["segundos"]), "lado": lado,
            "color": color_de(color), "material": material}


def main(argv=None) -> None:
    a = argparse.ArgumentParser(description="Fotos de producto con Blender (bpy), sin texto y listas para la tienda.")
    a.add_argument("--stl", type=Path, help="el STL de la pieza (no hace falta con --desde-crudos)")
    a.add_argument("--salida", type=Path, required=True, help="carpeta donde dejar las fotos (producto/ de la pieza)")
    a.add_argument("--color", default="", help="nombre (azul, negro mate, PLA seda dorado…) o #RRGGBB")
    a.add_argument("--material", help="PLA, PETG, ABS, ASA, TPU…")
    a.add_argument("--capa", type=float, default=0.2, help="altura de capa en mm (para las líneas de capa)")
    a.add_argument("--tomas", default=",".join(TOMAS_POR_DEFECTO), help=f"separadas por coma: {', '.join(TOMAS)}")
    a.add_argument("--tam", type=int, default=1200)
    a.add_argument("--muestras", type=int, default=16)
    a.add_argument("--json", type=Path)
    a.add_argument("--desde-crudos", type=Path, metavar="CARPETA",
                   help="solo arma las fotos (con Pillow) desde los renders crudos hechos en el Blender de la PC")
    args = a.parse_args(argv)
    tomas = [t.strip() for t in args.tomas.split(",") if t.strip()]
    if args.desde_crudos:
        try:
            archivos = componer_tomas(args.desde_crudos, args.salida, tomas, args.tam)
        except ValueError as error:
            raise SystemExit(str(error))
        for archivo in archivos:
            print(f"Foto: {archivo}")
        if args.json:
            args.json.write_text(json.dumps({"archivos": archivos}, ensure_ascii=False, indent=2), encoding="utf-8")
        return
    if not args.stl or not args.stl.exists():
        raise SystemExit(f"No existe {args.stl}" if args.stl else "Falta --stl (o --desde-crudos).")
    try:
        import bpy  # noqa: F401
    except ImportError:
        print("Falta Blender para Python: pip install --break-system-packages bpy pillow (unos 400 MB). Si no se "
              "puede, usar vista_previa.py pieza.stl foto_producto.png --producto.")
        sys.exit(2)
    try:
        r = renderizar(args.stl, args.salida, args.color, args.material, args.capa, tomas, args.tam, args.muestras)
    except ValueError as error:
        raise SystemExit(str(error))
    pedido = (args.color or "").strip().lower()
    if pedido and not (pedido.startswith("#") and len(pedido) == 7) and not any(n in pedido for n in COLORES):
        print(f"No reconocí el color «{args.color}»: salió gris. Pasalo como #RRGGBB para el tono justo.")
    for archivo in r["archivos"]:
        print(f"Foto: {archivo}")
    print(f"Listo en {r['segundos']} s.")
    if args.json:
        args.json.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
