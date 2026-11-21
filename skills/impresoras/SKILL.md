---
name: impresoras
description: Registra y configura las impresoras del usuario en el taller (modelo, límites, perfiles de Orca, tipo de cama) y muestra las que ya están cargadas. Se usa cuando el usuario dice "agregar impresora", "tengo otra impresora", "configurá mi impresora", "cambié la cama" o "qué impresoras tengo cargadas".
---

# /impresoras: impresoras del taller

Cargar antes la skill `impresion-3d` y seguir sus reglas. Scripts y datos: `<raíz del plugin>/skills/impresion-3d/`.

## Ver las impresoras

1. Traer `taller-3d/config.json` y listar `impresoras` (nombre, perfiles, cama) y cuál es la predeterminada.
2. Contrastar con `list_profiles` de `orca-mcp`: avisar si un perfil de la configuración no existe en Orca.
3. Revisar lo que sobra: traer las carpetas `process` y `filament` y correr `novedades_orca.py perfiles <process> <filament> --config <config.json>` (skill `impresion-3d`, sección 7). Mostrar claves viejas, perfiles `TEST` viejos y `AUTO` de impresoras que ya no están, y ofrecer ordenarlos con `/restaurar`.

## Agregar una impresora

1. Preguntar marca, modelo, boquilla y tipo de cama que usa.
2. Buscar datos:
   - Si el plugin la trae (`datos/impresoras/*.json`), usarlos.
   - Si no, buscar las especificaciones oficiales del fabricante en la web (área, temperatura máxima de boquilla y cama, firmware, cerramiento) y armar un JSON con el mismo formato que `datos/impresoras/ender-3-v3-plus.json`. Poner `fuentes` con los enlaces. Guardarlo en `<trabajo>/taller-3d/impresoras/<id>.json` y usar esa ruta en `datos`. Si un dato no aparece en fuentes oficiales, preguntarlo; no inventar límites.
3. Perfil de máquina en Orca:
   - Lo ideal es que el usuario la agregue desde Orca (asistente de impresoras, elegir marca y modelo) y guarde una copia de usuario llamada `Mi <modelo> <boquilla> nozzle`. Darle los pasos.
   - Verificar con `list_profiles` que exista y anotar su nombre exacto.
4. Perfiles de trabajo: definir `proceso_auto` y `filamento_auto` (`AUTO proceso @<modelo corto>`, `AUTO filamento @<modelo corto>`) y los perfiles de proceso y filamento propios que ya tenga.
5. Agregar la entrada a `impresoras` en `config.json` (procedimiento de escritura con respaldo) y preguntar si pasa a ser la predeterminada.
6. Prueba: generar un cubo de 20 mm con `cad.py`, laminarlo con los perfiles nuevos (AUTO filamento con `--cama`) y revisarlo con `revisar_gcode.py --impresora <datos> --cama-primera-capa <temperatura>`. Debe salir APROBADO.
7. Sugerir `/calibrar` para el filamento que más use en esa impresora.

## Cambiar algo

- Cama distinta: actualizar `cama` en la configuración. Desde la próxima pieza, el `AUTO filamento` toma las temperaturas de esa cama.
- Boquilla distinta: es otro perfil de máquina y otros procesos; tratarla como una impresora nueva o agregar los perfiles correspondientes.
