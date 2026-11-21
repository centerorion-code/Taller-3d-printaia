---
name: restaurar
description: Vuelve un perfil de Orca o la configuración del taller a una versión anterior desde los respaldos, ordena los perfiles de prueba y explica cómo desinstalar el taller. Se usa cuando el usuario dice "volvé atrás el perfil", "restaurar", "deshacer el cambio", "limpiar los perfiles TEST o AUTO" o "desinstalar".
---

# /restaurar: respaldos, limpieza y desinstalación

Cargar antes la skill `impresion-3d` y seguir sus reglas. Script: `<raíz del plugin>/skills/impresion-3d/scripts/perfil_orca.py`.

## Restaurar un archivo

1. Listar `<trabajo>/respaldos/` (más reciente primero) y, si el usuario no dijo cuál, mostrar las últimas versiones del archivo pedido con fecha y qué cambió (`perfil_orca.py diff <respaldo> <actual>`).
2. Confirmar cuál restaurar.
3. Respaldar primero el archivo actual (así se puede deshacer la restauración).
4. Escribir el respaldo elegido en su ruta original con `device_commit_files`, `stagedPath` y `expectedMtimeMs`. El bloqueo automático lo revisa como a cualquier perfil: si el respaldo trae scripts o plugins de Orca, o no pasa la validación, no lo deja escribir. En ese caso, explicar el motivo y decirle al usuario que, si lo quiere igual, lo copie él desde `respaldos/` con el explorador de archivos.
5. Registrar en `historial.csv` y recordar reiniciar Orca si estaba abierto.

## Ordenar perfiles de prueba

La conexión con la PC no puede borrar archivos. Para limpiar:
1. Listar los perfiles `TEST ...` y, si el usuario quiere, los `AUTO ...` (`list_profiles`). Para saber cuáles sobran, traer las carpetas de perfiles y correr `novedades_orca.py perfiles <process> <filament> --config <config.json> --maquinas <machine>`: marca los `TEST` de más de 30 días, los `AUTO` de impresoras que ya no están y las claves que Orca ya no usa.
2. Indicar cómo borrarlos: en Orca, elegir el perfil y usar el ícono de borrar, o desde el explorador de archivos, borrando el `.json` y el `.info` de cada uno en la carpeta de perfiles de usuario.
3. No borrar nunca perfiles que no sean `TEST` o `AUTO` sin que el usuario lo pida explícitamente.

## Desinstalar

1. **El plugin:** se quita desde la configuración de plugins de la app de Claude.
2. **Lo que queda en la PC** (no se borra solo; el usuario decide):
   - la carpeta de trabajo (piezas, respaldos, calibraciones, configuración);
   - los perfiles `AUTO ...` y los que se crearon con el taller en Orca;
   - lo que haya instalado el instalador (Orca, `orca-mcp`, el acceso directo y la entrada del MCP en la app; en Windows, también la unión de la carpeta de datos de Orca). Para eso está el desinstalador en `instalador/`: `desinstalar.sh` en Linux y `desinstalar-windows.bat` en Windows. Muestra qué quitaría y pide confirmación; manda a la papelera en lugar de borrar. En Windows devuelve los datos de Orca a `AppData`.
3. Ofrecer dejar la guía de desinstalación en la carpeta de trabajo de la PC.
