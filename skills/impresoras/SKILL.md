---
name: impresoras
description: Elige la impresora en la que trabajar entre las que el usuario tiene en Orca, investiga sus datos oficiales en internet, la configura óptima (perfiles AUTO) y muestra las que ya están preparadas. Se usa cuando el usuario dice "agregar impresora", "tengo otra impresora", "quiero trabajar con la otra impresora", "configurá mi impresora", "cambié la cama" o "qué impresoras tengo cargadas".
---

# /impresoras: impresoras del taller

Cargar antes la skill `impresion-3d` y seguir sus reglas. Guía completa: `references/impresoras.md` de esa skill. Scripts: `<raíz del plugin>/skills/impresion-3d/scripts/`.

El plugin no trae impresoras: los datos de cada una se arman cuando el usuario elige trabajar en ella, investigando en internet, y quedan en su carpeta de trabajo (`taller-3d/impresoras/<id>.json`). No se preparan todas las de Orca de entrada: solo la que va a usar.

## Ver las impresoras

1. `list_profiles` de `orca-mcp` con `machine`: las impresoras del usuario en Orca.
2. Traer `taller-3d/config.json` y marcar cuáles ya están preparadas en el taller (con datos que pasan `impresora.py validar`) y cuál se usó por última vez (`impresora_por_defecto`).
3. Revisar lo que sobra: traer las carpetas `process` y `filament` y correr `novedades_orca.py perfiles <process> <filament> --config <config.json>` (skill `impresion-3d`, sección 7). Mostrar claves viejas, perfiles `TEST` viejos y `AUTO` de impresoras que ya no están, y ofrecer ordenarlos con `/restaurar`.

## Elegir y preparar una impresora

1. **En cuál trabajar** (`references/impresoras.md`, sección 1): si hay varias en Orca, preguntar en cuál; si la que quiere no está, darle los pasos en Orca. Si ya está preparada, usar sus datos y terminar acá.
2. **Investigarla** (sección 2): fabricante y perfiles de OrcaSlicer de ese modelo. Lo que falte se pregunta: no inventar límites. `python3 -I impresora.py validar <json>`.
3. **Configurarla óptima** (sección 3): cama que usa, perfiles `AUTO proceso` y `AUTO filamento` con `perfil_orca.py crear --impresora <json>`, y sus perfiles propios si los tiene.
4. **Probar y guardar** (sección 4): cubo de 20 mm, `impresora.py comparar` y `revisar_gcode.py` en APROBADO; el JSON en `taller-3d/impresoras/<id>.json` y la entrada en `config.json` (procedimiento de escritura con respaldo), como `impresora_por_defecto`.
5. Sugerir `/calibrar` para el filamento que más use en esa impresora.

## Cambiar algo

- Cama distinta: actualizar `cama` en la configuración. Desde la próxima pieza, el `AUTO filamento` toma las temperaturas de esa cama.
- Boquilla distinta: es otro perfil de máquina en Orca; prepararlo como otra impresora.
- Datos viejos: si `datos` en la configuración no es la ruta a un JSON que exista y pase `impresora.py validar` (por ejemplo, configuraciones de antes de la 0.1.7, cuando el plugin traía la Ender-3 V3 Plus), volver a preparar esa impresora.
