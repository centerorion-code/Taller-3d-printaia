#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
"""Reel vertical (9:16, 1080x1920) de una pieza para Instagram Reels, TikTok o YouTube Shorts.

Arma el video con las fotos de la pieza (las de producto, la vista previa, fotos reales) y, si hay, un
timelapse de la impresión. Cada foto entra con un acercamiento lento sobre un fondo desenfocado de la misma
foto, con un rótulo corto arriba (el gancho en la primera, datos en las del medio) y un cierre con el precio
y la tienda. El texto va en zona segura: lejos de los bordes y de la franja de abajo, que tapan los botones
de las apps. No publica nada: deja el video, la portada y un guion con lo que dice cada toma.

Requiere Pillow y ffmpeg (en el espacio de Claude ya están; si falta ffmpeg: apt-get install ffmpeg).
La música es opcional y tiene que tener licencia para uso comercial (skill ai-music-and-sound): nunca un tema
de moda bajado de internet. Un audio en tendencia se agrega a mano dentro de la app al publicar.

Uso:
  python3 -I reel_pieza.py --fotos producto/producto-1-principal.jpg producto/producto-3-frente.jpg vista.png \\
      --gancho "¿Estante flojo? Lo imprimí" --rotulos "Soporte en L|PETG, aguanta 8 kg|Se atornilla en 2 min" \\
      --cierre "$ 4.500" --marca york3d.es --salida reel/reel.mp4 [--timelapse timelapse.mp4] \\
      [--musica tema.mp3] [--segundos 2.6] [--publicacion producto/publicacion.json] [--json reel/reel.json]
Con --publicacion, lo que falte (cierre con el precio, rótulos) sale de la publicación armada por
producto_tienda.py.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ANCHO, ALTO, FPS = 1080, 1920, 30
MARGEN = 90                    # lados
ZONA_ARRIBA = 230              # arriba quedan el nombre de la cuenta y la hora
ZONA_ABAJO = 420               # abajo, el texto de la publicación y los botones de la app
FUENTES = [
    "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf",
    "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]
MAX_ROTULO = 60                # caracteres: en un reel se lee en un segundo y medio


def fuente(tam: int):
    from PIL import ImageFont
    for ruta in FUENTES:
        if Path(ruta).exists():
            return ImageFont.truetype(ruta, tam)
    try:
        return ImageFont.load_default(size=tam)
    except TypeError:          # Pillow viejo
        return ImageFont.load_default()


def partir(texto: str, letra, ancho: int, dibujo) -> list[str]:
    """Corta el texto en renglones que entren en `ancho`."""
    renglones, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if dibujo.textlength(prueba, font=letra) <= ancho or not actual:
            actual = prueba
        else:
            renglones.append(actual)
            actual = palabra
    if actual:
        renglones.append(actual)
    return renglones


def rotulo(lienzo, texto: str, y: int, tam: int = 78, fondo=(0, 0, 0, 170), color=(255, 255, 255, 255)) -> int:
    """Dibuja el texto centrado en una franja redondeada desde `y`. Devuelve dónde termina."""
    from PIL import Image, ImageDraw
    if not texto:
        return y
    capa = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    letra = fuente(tam)
    renglones = partir(texto, letra, ANCHO - 2 * MARGEN - 60, d)
    alto_renglon = int(tam * 1.22)
    ancho = max(d.textlength(r, font=letra) for r in renglones)
    caja = (ANCHO / 2 - ancho / 2 - 30, y, ANCHO / 2 + ancho / 2 + 30, y + alto_renglon * len(renglones) + 36)
    d.rounded_rectangle(caja, radius=28, fill=fondo)
    for i, r in enumerate(renglones):
        d.text((ANCHO / 2, y + 18 + i * alto_renglon), r, font=letra, fill=color, anchor="ma")
    lienzo.alpha_composite(capa)
    return int(caja[3])


def placa(foto: Path, texto: str = "", abajo: str = "") -> "Image.Image":
    """Un cuadro de 1080x1920: la foto entera al centro sobre la misma foto desenfocada, y los rótulos."""
    from PIL import Image, ImageFilter, ImageOps
    img = ImageOps.exif_transpose(Image.open(foto)).convert("RGB")
    fondo = ImageOps.fit(img, (ANCHO, ALTO)).filter(ImageFilter.GaussianBlur(40))
    fondo = Image.blend(fondo, Image.new("RGB", fondo.size, (20, 20, 20)), 0.35).convert("RGBA")
    util = (ANCHO - 2 * 40, ALTO - ZONA_ARRIBA - ZONA_ABAJO + 120)
    frente = ImageOps.contain(img, util)
    fondo.paste(frente, ((ANCHO - frente.width) // 2, (ALTO - frente.height) // 2 - 40))
    rotulo(fondo, texto, ZONA_ARRIBA)
    if abajo:
        rotulo(fondo, abajo, ALTO - ZONA_ABAJO - 40, tam=64, fondo=(255, 255, 255, 225), color=(20, 20, 20, 255))
    return fondo.convert("RGB")


def placa_cierre(foto: Path | None, precio: str, marca: str) -> "Image.Image":
    from PIL import Image
    base = placa(foto) if foto else Image.new("RGB", (ANCHO, ALTO), (24, 24, 24))
    base = base.convert("RGBA")
    velo = Image.new("RGBA", base.size, (0, 0, 0, 120))
    base.alpha_composite(velo)
    y = ALTO // 2 - 260
    if precio:
        y = rotulo(base, precio, y, tam=140, fondo=(255, 255, 255, 235), color=(20, 20, 20, 255)) + 40
    if marca:
        rotulo(base, marca, y, tam=76)
    return base.convert("RGB")


def _ffmpeg() -> str:
    ruta = shutil.which("ffmpeg")
    if not ruta:
        raise SystemExit("Falta ffmpeg (apt-get install ffmpeg, o en Windows: winget install ffmpeg).")
    return ruta


def _correr(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("ffmpeg falló:\n" + r.stderr[-1500:])


def tramo_foto(png: Path, salida: Path, segundos: float, entrando: bool) -> None:
    """Acercamiento lento (Ken Burns) sobre la placa: del 100 % al 108 %, o al revés."""
    n = max(1, round(segundos * FPS))
    zoom = f"1+0.08*on/{n}" if entrando else f"1.08-0.08*on/{n}"
    filtro = (f"scale={ANCHO * 2}:{ALTO * 2},zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":d={n}:s={ANCHO}x{ALTO}:fps={FPS},format=yuv420p")
    _correr([_ffmpeg(), "-y", "-loglevel", "error", "-i", str(png), "-vf", filtro, "-frames:v", str(n),
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(salida)])


def tramo_video(video: Path, salida: Path, segundos: float, texto: str, tmp: Path) -> None:
    """El timelapse, acelerado para que dure `segundos`, recortado a 9:16 y con su rótulo."""
    dur = _duracion(video)
    velocidad = max(1.0, dur / segundos) if dur else 1.0
    from PIL import Image
    capa = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
    rotulo(capa, texto, ZONA_ARRIBA)
    png = tmp / "rotulo-timelapse.png"
    capa.save(png)
    filtro = (f"[0:v]setpts=PTS/{velocidad:.4f},scale={ANCHO}:{ALTO}:force_original_aspect_ratio=increase,"
              f"crop={ANCHO}:{ALTO},fps={FPS}[v];[v][1:v]overlay=0:0,format=yuv420p")
    _correr([_ffmpeg(), "-y", "-loglevel", "error", "-i", str(video), "-i", str(png), "-filter_complex", filtro,
             "-t", f"{segundos:.2f}", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(salida)])


def _duracion(archivo: Path) -> float:
    sonda = shutil.which("ffprobe")
    if not sonda:
        return 0.0
    r = subprocess.run([sonda, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(archivo)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def unir(tramos: list[Path], salida: Path, segundos: list[float], musica: Path | None, fundido: float = 0.35) -> None:
    """Une los tramos con fundidos cruzados y, si hay, pone la música (con fundido de salida)."""
    cmd = [_ffmpeg(), "-y", "-loglevel", "error"]
    for t in tramos:
        cmd += ["-i", str(t)]
    if len(tramos) == 1:
        cadena, final = "[0:v]null[v]", "[v]"
    else:
        partes, previo, acumulado = [], "[0:v]", 0.0
        for i in range(1, len(tramos)):
            acumulado += segundos[i - 1] - fundido
            nombre = f"[x{i}]"
            partes.append(f"{previo}[{i}:v]xfade=transition=fade:duration={fundido}:offset={acumulado:.3f}{nombre}")
            previo = nombre
        cadena, final = ";".join(partes), previo
    total = sum(segundos) - fundido * (len(tramos) - 1)
    if musica:
        cmd += ["-i", str(musica)]
        cadena += (f";[{len(tramos)}:a]atrim=0:{total:.2f},afade=t=in:d=0.3,"
                   f"afade=t=out:st={max(0, total - 1.2):.2f}:d=1.2[a]")
        cmd += ["-filter_complex", cadena, "-map", final, "-map", "[a]", "-c:a", "aac", "-b:a", "160k"]
    else:
        cmd += ["-filter_complex", cadena, "-map", final]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-movflags", "+faststart", "-t", f"{total:.2f}", str(salida)]
    _correr(cmd)


def _de_publicacion(ruta: Path | None) -> dict:
    if not ruta:
        return {}
    pub = json.loads(Path(ruta).read_text(encoding="utf-8"))
    p = pub.get("producto", {})
    precio = p.get("regular_price") or p.get("precio") or (pub.get("precio") or {}).get("precio_sugerido")
    medidas = pub.get("medidas_mm")
    datos = {"nombre": p.get("name") or p.get("nombre"), "material": pub.get("material"),
             "precio": precio, "fotos": [str(Path(ruta).parent / f) for f in pub.get("fotos") or []]}
    if isinstance(medidas, (list, tuple)) and len(medidas) == 3:
        datos["medidas"] = " x ".join(f"{round(float(m))}" for m in medidas) + " mm"
    return datos


def plata(valor) -> str:
    """Mismo formato que el resto del taller: «$ 12.300»."""
    try:
        n = float(str(valor).replace("$", "").replace(".", "").replace(",", ".").strip())
    except ValueError:
        return str(valor)
    return "$ " + f"{round(n):,}".replace(",", ".")


def armar(fotos: list[Path], salida: Path, gancho: str = "", rotulos: list[str] | None = None,
          cierre: str = "", marca: str = "", segundos: float = 2.6, timelapse: Path | None = None,
          musica: Path | None = None, publicacion: Path | None = None) -> dict:
    pub = _de_publicacion(publicacion)
    if not fotos and pub.get("fotos"):
        fotos = [Path(f) for f in pub["fotos"] if Path(f).exists()]
    if not fotos:
        raise ValueError("Hace falta al menos una foto de la pieza (--fotos).")
    faltan = [str(f) for f in fotos if not Path(f).exists()]
    if faltan:
        raise ValueError("No existen: " + ", ".join(faltan))
    rotulos = list(rotulos or [])
    if not rotulos and pub:
        rotulos = [t for t in (pub.get("nombre"), pub.get("material"), pub.get("medidas")) if t]
    largos = [r for r in [gancho, *rotulos] if len(r) > MAX_ROTULO]
    if largos:
        raise ValueError(f"Rótulo de más de {MAX_ROTULO} caracteres (no se llega a leer): «{largos[0]}»")
    if not cierre and pub.get("precio"):
        cierre = plata(pub["precio"])
    elif cierre and cierre.replace(".", "").replace(",", "").replace("$", "").strip().isdigit():
        cierre = plata(cierre)
    salida = Path(salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    guion, tramos, tiempos = [], [], []
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        textos = [gancho] + rotulos
        for i, foto in enumerate(fotos):
            texto = textos[i] if i < len(textos) else ""
            png = tmp / f"placa-{i}.png"
            placa(Path(foto), texto).save(png)
            if i == 0:
                placa(Path(foto), texto).save(salida.with_name(salida.stem + "-portada.jpg"), quality=90)
            dur = segundos + (0.6 if i == 0 else 0)          # el gancho necesita un poco más
            mp4 = tmp / f"tramo-{len(tramos)}.mp4"
            tramo_foto(png, mp4, dur, entrando=i % 2 == 0)
            tramos.append(mp4)
            tiempos.append(dur)
            guion.append({"toma": len(guion) + 1, "imagen": str(foto), "texto": texto, "segundos": dur})
            if timelapse and i == 0:
                mp4 = tmp / f"tramo-{len(tramos)}.mp4"
                tramo_video(Path(timelapse), mp4, 3.0, "Así se imprimió", tmp)
                tramos.append(mp4)
                tiempos.append(3.0)
                guion.append({"toma": len(guion) + 1, "imagen": str(timelapse), "texto": "Así se imprimió",
                              "segundos": 3.0})
        if cierre or marca:
            png = tmp / "cierre.png"
            placa_cierre(Path(fotos[0]), cierre, marca).save(png)
            mp4 = tmp / f"tramo-{len(tramos)}.mp4"
            tramo_foto(png, mp4, 2.4, entrando=True)
            tramos.append(mp4)
            tiempos.append(2.4)
            guion.append({"toma": len(guion) + 1, "imagen": "cierre", "texto": " · ".join(x for x in (cierre, marca) if x),
                          "segundos": 2.4})
        unir(tramos, salida, tiempos, Path(musica) if musica else None)
    total = round(sum(tiempos) - 0.35 * (len(tiempos) - 1), 1)
    return {"video": str(salida), "portada": str(salida.with_name(salida.stem + "-portada.jpg")),
            "segundos": total, "formato": f"{ANCHO}x{ALTO} 9:16, {FPS} fps, H.264",
            "musica": str(musica) if musica else None, "guion": guion}


def main(argv=None) -> None:
    a = argparse.ArgumentParser(description="Reel vertical 9:16 de una pieza (Reels, TikTok, Shorts). No publica nada.")
    a.add_argument("--fotos", type=Path, nargs="*", default=[], help="en orden; la primera lleva el gancho")
    a.add_argument("--gancho", default="", help="texto de los primeros segundos (que se entienda sin sonido)")
    a.add_argument("--rotulos", default="", help="un texto por foto siguiente, separados por |")
    a.add_argument("--cierre", default="", help="el precio o una llamada corta para el final")
    a.add_argument("--marca", default="", help="la tienda o la cuenta, para el final (york3d.es, @cuenta)")
    a.add_argument("--segundos", type=float, default=2.6, help="cuánto dura cada foto")
    a.add_argument("--timelapse", type=Path, help="video de la impresión, va después del gancho")
    a.add_argument("--musica", type=Path, help="audio con licencia comercial")
    a.add_argument("--publicacion", type=Path, help="producto/publicacion.json, para completar lo que falte")
    a.add_argument("--salida", type=Path, required=True)
    a.add_argument("--json", type=Path)
    args = a.parse_args(argv)
    rotulos = [r.strip() for r in args.rotulos.split("|") if r.strip()]
    try:
        r = armar(args.fotos, args.salida, args.gancho, rotulos, args.cierre, args.marca, args.segundos,
                  args.timelapse, args.musica, args.publicacion)
    except ValueError as error:
        raise SystemExit(str(error))
    print(f"Video: {r['video']} ({r['segundos']} s, {r['formato']})")
    print(f"Portada: {r['portada']}")
    if not r["musica"]:
        print("Sin música: sumale un audio con licencia, o uno en tendencia desde la app al publicar.")
    if args.json:
        args.json.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
