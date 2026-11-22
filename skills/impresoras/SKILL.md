---
name: impresoras
description: Elige la impresora en la que trabajar entre las que el usuario tiene en Orca, investiga sus datos oficiales en internet (también su consumo, para el costo de la luz), la configura óptima (perfiles AUTO) y muestra las que ya están preparadas. Se usa cuando el usuario dice "agregar impresora", "tengo otra impresora", "quiero trabajar con la otra impresora", "configurá mi impresora", "cambié la cama", "cuánto consume mi impresora" o "qué impresoras tengo cargadas".
---

# /impresoras: impresoras del taller

Cargar antes la skill `impresion-3d` y seguir sus reglas. Guía completa: `references/impresoras.md` de esa skill. Scripts: `<raíz del plugin>/skills/impresion-3d/scripts/`.

El plugin no trae impresoras: los datos de cada una se arman cuando el usuario elige trabajar en ella, investigando en internet, y quedan en su carpeta de trabajo (`taller-3d/impresoras/<id>.json`). No se preparan todas las de Orca de entrada: solo la que va a usar.

Carpetas: la de trabajo y la de perfiles de usuario de Orca (`user/<id>`, que tiene `process`, `filament` y `machine`), en un solo pedido (`/instalar`, sección 3).

## Ver las impresoras

1. `impresora.py detectar` (`references/impresoras.md`, sección 1): las copias de usuario, las impresoras que nombran sus perfiles y, si hay terminal en la PC, la lista de Orca. `list_profiles` solo muestra las que tienen copia de usuario.
2. Traer `taller-3d/config.json` y marcar cuáles ya están preparadas en el taller (con datos que pasan `impresora.py validar`), cuál se usó por última vez (`impresora_por_defecto`) y el consumo de cada una con su origen (`costos.py estado`). Si a una preparada le falta el consumo, buscarlo y guardarlo sin preguntar (`references/costos.md`, «El consumo de la impresora»).
3. Revisar lo que sobra: traer las carpetas `process` y `filament` y correr `novedades_orca.py perfiles <process> <filament> --config <config.json> --maquinas <machine>` (skill `impresion-3d`, sección 7). Mostrar claves viejas, perfiles `TEST` viejos y `AUTO` de impresoras que ya no están, y ofrecer ordenarlos con `/restaurar`.

## Elegir y preparar una impresora

1. **En cuál trabajar** (`references/impresoras.md`, sección 1): si hay varias en Orca y no dijo cuál, preguntar en cuál, con la recomendada primero (sección 1, paso 2), avisando que elegirla en la ventana de Orca no le llega a Claude. Si la elegida no tiene copia de usuario, ofrecer crearla (sección 1, paso 4: lo más seguro es guardarla desde Orca). Si ya está preparada, usar sus datos (si le falta el consumo, buscarlo) y terminar acá.
2. **Investigarla** (sección 2): fabricante y perfiles de OrcaSlicer de ese modelo. Lo que falte se pregunta: no inventar límites. `python3 -I impresora.py validar <json>`. Buscar también su **consumo** para el costo de la luz, sin preguntarlo (`references/costos.md`, «El consumo de la impresora»): el promedio oficial o de una prueba publicada; si la ficha solo da la potencia nominal (el máximo, no el promedio), se estima por el tamaño de la cama. Preguntar solo si no aparece nada.
3. **Configurarla óptima** (sección 3): cama que usa, perfiles `AUTO proceso` y `AUTO filamento` con `perfil_orca.py crear --impresora <json>`, y sus perfiles propios si los tiene.
4. **Probar y guardar** (sección 4): cubo de 20 mm, `impresora.py comparar` y `revisar_gcode.py` en APROBADO; el JSON en `taller-3d/impresoras/<id>.json` y la entrada en `config.json` (procedimiento de escritura con respaldo), como `impresora_por_defecto`.
   En la entrada, `costo` (`references/costos.md`): el consumo, con `costos.py consumo --impresora <id> … --salida` sobre la copia de `config.json` antes de escribirla, y contarle al usuario en una línea qué se encontró y de dónde (con el enlace); y, si el usuario lo dice, cuánto la pagó (`precio`). Si no sabe el precio, dejarlo para después: el costo lo pide cuando hace falta.
5. Sugerir `/calibrar` para el filamento que más use en esa impresora.

## Cambiar algo

- Cama distinta: actualizar `cama` en la configuración. Desde la próxima pieza, el `AUTO filamento` toma las temperaturas de esa cama.
- Boquilla distinta: es otro perfil de máquina en Orca; prepararlo como otra impresora.
- Consumo medido: si el usuario lo midió con un medidor de enchufe (kWh de una impresión entera / sus horas), `costos.py consumo --impresora <id> --promedio <W> --origen medido --salida config.json`. Un medido no se pisa después con un estimado.
- Datos viejos: si `datos` en la configuración no es la ruta a un JSON que exista y pase `impresora.py validar` (por ejemplo, configuraciones de antes de la 0.1.7, cuando el plugin traía la Ender-3 V3 Plus), volver a preparar esa impresora.
