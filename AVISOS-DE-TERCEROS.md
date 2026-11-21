# Avisos de terceros

taller-3d se distribuye bajo la GNU Affero General Public License, versión 3 ([LICENSE](LICENSE)). Copyright (C) 2026 Leo y colaboradores de taller-3d.

## Contenido que sale de OrcaSlicer

OrcaSlicer es Copyright (C) sus autores, entre ellos SoftFever y los colaboradores de OrcaSlicer, Bambu Lab (Bambu Studio), Prusa Research (PrusaSlicer) y Alessandro Ranellucci (Slic3r). Se distribuye bajo la GNU AGPL versión 3: https://github.com/OrcaSlicer/OrcaSlicer

Estos archivos de taller-3d contienen material de OrcaSlicer 2.5.1, modificado para taller-3d (última modificación: 2026-11-21), y se distribuyen con la misma licencia. Cada uno lleva el aviso en su campo `aviso`:

| Archivo | Qué tiene de OrcaSlicer | Cambios hechos para taller-3d |
|---|---|---|
| `skills/impresion-3d/references/catalogo-orca-2.5.1/parametros-*.json` | Nombres, explicaciones, tipos, rangos, valores posibles y organización en páginas y grupos de los 1015 parámetros, tomados del código fuente | Pasado a JSON, en partes; agregados categoría y modo en español. Las explicaciones en español salen de la traducción de OrcaSlicer o se tradujeron del inglés para taller-3d. |
| `skills/impresion-3d/datos/claves-gcode-2.5.1.json` | Nombres de las 750 claves que OrcaSlicer 2.5.1 escribe en el G-code | Solo la lista de nombres |

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
| Pillow | encuadre de las imágenes de producto | MIT-CMU |
| Blender (opcional) | modelado orgánico | GPL |

## Marcas

OrcaSlicer, Creality, Ender, Blender, Claude, WooCommerce, Tiendanube, Shopify y Mercado Libre son marcas de sus dueños. taller-3d no está afiliado a ellos ni avalado por ellos.
