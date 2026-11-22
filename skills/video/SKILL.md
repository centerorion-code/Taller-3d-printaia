---
name: video
description: Arma un reel vertical (Instagram Reels, TikTok, YouTube Shorts) de una pieza del taller con sus fotos, el timelapse si hay, rótulos y el precio, más el guion, el texto de la publicación y los hashtags. Nunca publica en redes. Se usa cuando el usuario dice "haceme un reel", "un video para TikTok", "un short de la pieza", "video para redes", "promocioná la pieza", o al terminar /publicar si acepta el video.
---

# /video: de la pieza al reel

Cargar antes la skill `impresion-3d` y seguir sus reglas. El video lo arma `<raíz del plugin>/skills/impresion-3d/scripts/reel_pieza.py` (Pillow y ffmpeg, en el espacio de Claude). El oficio de redes viene de las skills que el taller trae de social-media-skills (licencia MIT, `licencias/social-media-skills-MIT.txt`): `reels-script`, `tiktok-script`, `youtube-shorts`, `short-form-video-script`, `hook-writer`, `caption-writer`, `hashtag-strategy`, `captions-and-clipping`, `capcut`, `ai-music-and-sound`, `platform-specs-and-validation`, `cross-platform-repurposing`, `instagram-reels-publishing`, `tiktok-video-publishing` y `brand-profile`. Esas skills hablan de WoopSocial para programar publicaciones: en el taller es opcional, solo si el usuario tiene su cuenta.

## Reglas propias

- **Nunca publica en redes.** Deja el video, la portada y los textos; el usuario los sube desde la app (ahí también elige el audio en tendencia). Programar con WoopSocial u otra herramienta solo si el usuario lo pide y ya tiene la cuenta conectada.
- **Sin claves en archivos.** Nada de claves de API, tokens ni contraseñas en `config.json`, en la carpeta de la pieza ni en el chat: las conexiones (WoopSocial, ElevenLabs, Veo) las configura el usuario en su conector.
- **Lo mismo que la publicación:** los datos del video (medidas, material, peso, aguante, precio) salen de los informes y de `publicacion.json`, nunca inventados. Si la pieza no se imprimió todavía y solo hay fotos renderizadas, el texto de la publicación lo aclara («imagen ilustrativa») y no se muestra como si fuera real.
- **Música con licencia.** Solo audio con licencia comercial (Epidemic Sound si está el conector, o lo que diga `ai-music-and-sound`). Nunca un tema bajado de internet. Si no hay, el video sale sin música y se lo dice.
- **Mismas reglas de modelos ajenos** que `/publicar`: un personaje, un logo o un modelo con licencia no comercial no se promociona para vender.
- **Marca del usuario:** si existe `<trabajo>/taller-3d/marca.md` (perfil de marca hecho con `brand-profile`: a quién le vende, cómo habla, qué no dice), leerlo antes de escribir. Si no existe, ofrecer armarlo una vez; no frenar el video por eso.

## 1. Juntar lo de la pieza

1. Ubicar la carpeta de la pieza en `<trabajo>/impresiones/...`. Traer `producto/publicacion.json` si está (si no, `informe_gcode.json` e `informe_stl.json`), las fotos de `producto/`, `vista.png` y las fotos reales.
2. Preguntar en una sola línea lo que falte: para qué red (Reels, TikTok, Shorts o las tres), si hay timelapse de la impresión o un video de la pieza en uso (pueden mandarlo desde el celular) y si quiere música.
3. Si no hay ninguna foto, ofrecer primero las fotos de producto (`/publicar`, sección 2) o una foto real.

## 2. Guion

Seguir la skill de la red elegida (`reels-script`, `tiktok-script` o `youtube-shorts`) y `hook-writer` para los primeros segundos. Para una pieza del taller sirve casi siempre este orden:

1. **Gancho** (primera foto, 3 s): el problema que resuelve o el resultado, que se entienda sin sonido. «¿Estante flojo? Lo imprimí en casa».
2. **Proceso** (si hay timelapse): «Así se imprimió».
3. **Datos** (una foto por dato, máximo tres): medidas, material y lo que aguanta, de los informes.
4. **Cierre**: precio y la tienda o la cuenta.

Cada rótulo, de 60 caracteres como mucho (se lee en un segundo y medio). Mostrar el guion en una tabla corta (toma, imagen, texto, segundos) y seguir: si el usuario quiere cambiar algo, se rehace en segundos.

## 3. Armar el video

```bash
python3 -I reel_pieza.py --fotos <foto gancho> <foto 2> <foto 3> \
  --gancho "<gancho>" --rotulos "<texto 2>|<texto 3>" --cierre "<precio>" --marca "<tienda o @cuenta>" \
  --publicacion <carpeta>/producto/publicacion.json [--timelapse <video>] [--musica <audio con licencia>] \
  --salida <carpeta>/video/reel.mp4 --json <carpeta>/video/reel.json
```

Deja `reel.mp4` (1080x1920, 30 fps, H.264, entre 10 y 20 s), `reel-portada.jpg` y `reel.json` con el guion. Mirar dos o tres cuadros (`ffmpeg -ss <s> -i reel.mp4 -frames:v 1 cuadro.jpg`) antes de mostrarlo: que los rótulos se lean y no tapen la pieza.

Para algo más trabajado (cortes al ritmo de la música, subtítulos animados, voz en off), entregar el guion y las tomas para CapCut (`capcut`, `captions-and-clipping`) en vez de forzar el script.

## 4. Texto de la publicación

Con `caption-writer` y `hashtag-strategy`, uno por red elegida: primera línea que enganche, dos o tres renglones con el dato fuerte y la llamada («link en la bio», «escribime»), y de 3 a 5 hashtags específicos (#impresion3d, el material, el uso), no 30 genéricos. Guardarlos en `<carpeta>/video/textos.md`, junto con el título para Shorts y lo que hay que elegir en la app (portada, audio).

## 5. Entregar y anotar

1. Copiar `video/` a la carpeta de la pieza en la PC (con `device_commit_files`) y dar el enlace al video y a `textos.md`.
2. Anotar en el panel (skill `panel`): `catalogo.py agregar --carpeta <carpeta de la pieza> --archivos video/reel.mp4 video/reel-portada.jpg video/textos.md` y rehacer el panel.
3. Registrar en `historial.csv`.
4. Terminar con «Te toca: subir el reel desde la app (elegí la portada y el audio ahí)».
