# Avisos de terceros

taller-3d se distribuye bajo la GNU Affero General Public License, versión 3 ([LICENSE](LICENSE)). Copyright (C) 2026 Leo y colaboradores de taller-3d.

## Contenido que sale de OrcaSlicer

OrcaSlicer es Copyright (C) sus autores, entre ellos SoftFever y los colaboradores de OrcaSlicer, Bambu Lab (Bambu Studio), Prusa Research (PrusaSlicer) y Alessandro Ranellucci (Slic3r). Se distribuye bajo la GNU AGPL versión 3: https://github.com/OrcaSlicer/OrcaSlicer

Estos archivos de taller-3d contienen material de OrcaSlicer 2.5.1, modificado para taller-3d (última modificación: 2026-11-21), y se distribuyen con la misma licencia. Cada uno lleva el aviso en su campo `aviso`:

| Archivo | Qué tiene de OrcaSlicer | Cambios hechos para taller-3d |
|---|---|---|
| `skills/impresion-3d/references/catalogo-orca-2.5.1/parametros-*.json` | Nombres, explicaciones, tipos, rangos, valores posibles y organización en páginas y grupos de los 1015 parámetros, tomados del código fuente | Pasado a JSON, en partes; agregados categoría y modo en español. Las explicaciones en español salen de la traducción de OrcaSlicer o se tradujeron del inglés para taller-3d. |
| `skills/impresion-3d/datos/claves-gcode-2.5.1.json` | Nombres de las 750 claves que OrcaSlicer 2.5.1 escribe en el G-code | Solo la lista de nombres |
| `skills/impresion-3d/datos/proyecto-3mf-2.5.1.json` | Formato del proyecto `.3mf` que exporta OrcaSlicer 2.5.1 (`--export-3mf`): tipo de cada ajuste, valores que el G-code no trae y versiones | Sacado de un proyecto exportado por Orca y pasado a JSON |

## Skills de redes de social-media-skills

Estas skills vienen de social-media-skills 1.0.1, Copyright (c) 2026 Frank Heijdenrijk, con licencia MIT (texto completo en [licencias/social-media-skills-MIT.txt](licencias/social-media-skills-MIT.txt)). Se copiaron sin cambios, sin sus pruebas (`evals/`):

`skills/brand-profile`, `skills/hook-writer`, `skills/short-form-video-script`, `skills/reels-script`, `skills/tiktok-script`, `skills/youtube-shorts`, `skills/caption-writer`, `skills/hashtag-strategy`, `skills/captions-and-clipping`, `skills/capcut`, `skills/ai-music-and-sound`, `skills/instagram-reels-publishing`, `skills/tiktok-video-publishing`, `skills/platform-specs-and-validation`, `skills/cross-platform-repurposing` y `tools/integrations/{ai-music-and-sound,capcut,clipping,elevenlabs,veo,woopsocial}.md`.

No traen claves ni cuentas: si usás WoopSocial, ElevenLabs o Veo, la conexión la configurás vos en tu conector.

## Programas que el taller usa o instala

No vienen dentro del plugin: el instalador los baja de su fuente oficial o se instalan cuando hacen falta.

| Programa | Para qué | Licencia |
|---|---|---|
| OrcaSlicer 2.5.1 | laminador | AGPL-3.0 |
| orca-mcp 0.1.0 | conexión entre Claude y Orca | MIT |
| uv 0.13.9 (solo Windows, si no está) | instala orca-mcp aislado | MIT o Apache-2.0 |
| Python | corre orca-mcp y los scripts | Python Software Foundation License |
| manifold3d | CAD por código | Apache-2.0 |
| numpy | cálculo de mallas | BSD-3-Clause |
| matplotlib | vistas previas e imágenes de producto | licencia de Matplotlib (basada en la de la PSF) |
| ffmpeg | armar los reels (`reel_pieza.py`) | LGPL-2.1 o posterior (GPL según cómo se compiló) |
| Pillow | encuadre de las imágenes y fotos de producto | MIT-CMU |
| Blender (opcional) | modelado orgánico | GPL |
| bpy, el módulo de Blender para Python (opcional) | fotos de producto (`render_producto.py`) y engrosar cáscaras (`engrosar_stl.py`); se instala con pip en el espacio de Claude cuando hace falta | GPL-3.0 o posterior |
| OpenCV (opcional) | retocar una foto antes de generar el modelo (sacar una soga, el fondo); se instala con pip cuando hace falta | Apache-2.0 |

## Servicios que el taller usa con tu cuenta

No vienen con el plugin ni los paga el taller: Claude los usa en tu Chrome, con tu sesión, solo si los tenés y lo pedís. Cada uno tiene sus propios términos de uso, que valen también para lo que generan.

| Servicio | Para qué |
|---|---|
| Hunyuan 3D (Tencent), https://3d.hunyuan.tencent.com | generar el modelo 3D de una pieza desde una o varias fotos (`references/foto-a-3d.md`) |
| Gemini o Flow (Google), con Nano Banana | generar una imagen para aprobar antes del 3D, o las vistas que faltan de un objeto |
| Gemini (Google), plan gratis | escribir el texto de venta de una publicación, que Claude revisa antes de usar (`references/textos-con-gemini.md`) |

## Marcas

OrcaSlicer, Creality, Ender, Blender, Claude, Instagram, TikTok, YouTube, CapCut, WoopSocial, WooCommerce, Tiendanube, Shopify, Mercado Libre, Tencent, Hunyuan, Google, Gemini, Flow y Nano Banana son marcas de sus dueños. taller-3d no está afiliado a ellos ni avalado por ellos.
