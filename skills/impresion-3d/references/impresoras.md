# Impresoras: elegir, investigar y configurar

El plugin no trae impresoras cargadas: hay demasiados modelos y cada persona tiene las suyas, muchas veces varias en el mismo Orca. Los datos de una impresora se arman cuando el usuario elige trabajar en ella y quedan en su carpeta de trabajo (`taller-3d/impresoras/<id>.json`) para la próxima vez. No se preparan todas de entrada: solo la que va a usar.

## 1. En qué impresora trabajar

orca-mcp solo ve las impresoras que tienen **copia de usuario** (un perfil de máquina guardado en `user/<id>/machine/`) y no sabe cuál está elegida en la ventana de Orca. Muchas personas tienen varias impresoras en Orca y solo una con copia, así que no alcanza con `list_profiles`.

1. **Juntar las impresoras** con `python3 -I impresora.py detectar`:
   - `--maquinas <carpeta machine traída>`: las copias de usuario (las mismas que muestra `list_profiles` con `machine`).
   - `--perfiles <process> <filament>` (carpetas traídas): las impresoras que nombran los perfiles del usuario en `compatible_printers`. Para saber el modelo usar `compatible_printers`, no `inherits`: `inherits` puede traer nombres viejos que Orca resuelve con `renamed_from`.
   - `--orca <json>`, solo si hay terminal en la PC (`device_bash`): las impresoras instaladas en Orca y la elegida, sacadas de `OrcaSlicer.conf` **en la PC** con el comando de abajo, tal cual y con la ruta absoluta. Ese archivo guarda la IP y el código de acceso de las impresoras en red: nunca traerlo con `device_stage_files` ni leerlo entero (el bloqueo automático lo impide). Sin terminal, no tocarlo y preguntarle al usuario qué impresoras tiene.
2. Si el usuario ya dijo en cuál, usar esa. Si hay una sola, o si para lo que pide sirve una sola (no entra en las otras, o el material pide cerramiento y es la única cerrada), usarla y decir en una línea cuál y por qué. Si no, **preguntar en cuál quiere trabajar antes de calcular nada** (`AskUserQuestion`; en `/pieza`, junto con el cuestionario): una opción por impresora, primero la recomendada con "(Recomendada)" (la que mejor encaja por tamaño y material; si da igual, la última usada, `impresora_por_defecto`, o la elegida en Orca), y en cada una el tamaño de la cama, si es cerrada y si ya está preparada o hay que prepararla (unos minutos, solo la primera vez). Marcar cuáles no tienen copia de usuario.
3. Avisar en una línea: elegir una impresora en la ventana de Orca no le llega a Claude; Claude trabaja con las copias de usuario guardadas.
4. **Si la elegida no tiene copia de usuario, ofrecer crearla.** Lo más seguro es que la guarde el usuario en Orca: elegir la impresora y, en su configuración, guardar una copia con el ícono de guardar, con el nombre `Mi <modelo> <boquilla> nozzle`. Eso crea también la carpeta `machine` si no existía (pasa cuando nunca guardó una impresora propia); después hay que conectarla. Si la impresora no está ni en Orca, agregarla antes con el asistente de impresoras de Orca (marca y modelo).
   Si la carpeta `machine` ya está conectada, la puede crear Claude:
   1. Buscar el perfil de sistema de máquina en la versión de Orca del usuario: nombre y `setting_id` (sección 2). Usar el nombre de esa versión, no uno viejo.
   2. `perfil_orca.py crear --tipo maquina --nombre "Mi <modelo> <boquilla> nozzle" --hereda "<perfil de sistema de máquina>" --base-id <setting_id> --salida <carpeta>`: arma el mismo JSON mínimo que guarda Orca y el `.info` con el `base_id`. No hace falta `--impresora`: los datos de la impresora se arman después, laminando con esta copia.
   3. Escribirlo con `device_commit_files` en `user/<id>/machine/` (la misma `<id>` que `process` y `filament`).
   4. Pedirle que cierre y abra Orca, y verificar con `list_profiles` (`machine`).
5. Si esa impresora ya está preparada en el taller (en `config.json`, con `datos` apuntando a un JSON que pasa `impresora.py validar`), usar esos datos. Si no, seguir con la sección 2.

**Leer la lista de Orca en la PC** (solo con `device_bash`): estos comandos no copian el archivo y sacan solo `models` y `presets.machine`. Escribirlos tal cual, cambiando solo `<carpeta de datos de Orca>` por la ruta **absoluta** (sin `~` ni variables, entre las comillas que ya tiene): el bloqueo automático no deja pasar otra forma de leer ese archivo. Ignoran la línea de control (`# MD5 checksum`) que Orca agrega al final en Windows. Guardar la salida como `orca.json` en el espacio de Claude y pasarla con `--orca`.

- Linux o macOS: `python3 -c 'import json,sys; t="".join(l for l in open(sys.argv[1], encoding="utf-8-sig") if not l.lstrip().startswith("#")); c=json.loads(t); print(json.dumps({"models": c.get("models", []), "machine": (c.get("presets") or {}).get("machine")}, ensure_ascii=False))' "<carpeta de datos de Orca>/OrcaSlicer.conf"`
- Windows (PowerShell): `$c = (Get-Content -Encoding UTF8 "<carpeta de datos de Orca>\OrcaSlicer.conf" | Where-Object { $_ -notmatch '^\s*#' } | Out-String) | ConvertFrom-Json; @{models = $c.models; machine = $c.presets.machine} | ConvertTo-Json -Depth 5 -Compress`

La carpeta de datos de Orca es la que contiene `user/`: Linux `/home/<usuario>/.config/OrcaSlicer` (Flatpak: `/home/<usuario>/.var/app/com.orcaslicer.OrcaSlicer/config/OrcaSlicer`), Windows `C:\Users\<usuario>\OrcaSlicer` después del instalador (antes, `C:\Users\<usuario>\AppData\Roaming\OrcaSlicer`), macOS `/Users/<usuario>/Library/Application Support/OrcaSlicer`. La carpeta personal sale de `get_device_info`. No traer ni copiar esa carpeta entera: de ahí solo se traen los perfiles (`user/` y `system/`).

## 2. Investigar la impresora

Con el modelo exacto (el `inherits` del perfil de máquina, por ejemplo `<Marca> <Modelo> 0.4 nozzle`), buscar en internet:

1. **El fabricante** (página del producto, manual o ficha técnica oficial): temperatura máxima de boquilla y de cama, volumen de impresión, firmware, cerramiento, hotend, cinemática y velocidades máximas.
2. **Los perfiles de OrcaSlicer de ese modelo** (repositorio de OrcaSlicer, `resources/profiles/<Marca>/`, de la versión que usa el usuario): nombres y `setting_id` de los perfiles de sistema de máquina, procesos por altura de capa y filamentos por material, y las temperaturas de cama de esos filamentos (`cama_sistema`).
3. Lo que no aparezca en fuentes oficiales se pregunta. **No inventar límites**: sin `boquilla_max_c` y `cama_max_c` del fabricante, el taller no lamina para esa impresora. Los foros, tiendas y videos no cuentan como fuente de límites.
4. Armar el JSON (formato abajo), con cada enlace en `fuentes`, y correr `python3 -I impresora.py validar <json>`: tiene que salir APROBADO, o con advertencias que se explican al usuario.
5. **El consumo**, en la misma búsqueda (para el costo de la luz, `costos.md`, «El consumo de la impresora»): el promedio oficial o de una prueba publicada si aparece; si no, la potencia nominal de la ficha, para estimarlo por la cama. No preguntarlo. Se guarda en la sección 4.

## 3. Configurarla óptima

1. Preguntar qué cama usa en esa impresora, si no está en la configuración ("Textured PEI Plate", "High Temp Plate", "Cool Plate", "Engineering Plate"...).
2. Perfiles de trabajo: `AUTO proceso @<patron_perfiles>` y `AUTO filamento @<patron_perfiles>`, heredando de los perfiles de sistema investigados, con `perfil_orca.py crear --impresora <json>` y los criterios de `recetas.md` (calidad, resistencia, velocidad), siempre dentro de los límites de la impresora. El de filamento, con `--cama "<cama real>"`.
3. Si el usuario ya tiene perfiles propios de proceso y filamento para esa impresora, anotarlos en `config.json` (`procesos`, `filamentos`) y usarlos de base.

## 4. Probar y guardar

1. Cubo de 20 mm con `cad.py`, laminado con orca-mcp con el perfil de máquina del usuario y los AUTO. Traer el G-code.
2. `python3 -I impresora.py comparar <json> <gcode>`: los datos tienen que coincidir con lo que usa Orca (modelo, perfil, área, altura, firmware y boquilla). Si no coinciden, mostrarle las dos cosas al usuario. Lo que usa Orca es lo real, salvo que su área sea más grande que la oficial: ahí manda la oficial y conviene revisar el perfil en Orca. Corregir el JSON y repetir.
3. `revisar_gcode.py <gcode> --impresora <json> --cama-primera-capa <temperatura>`: tiene que salir APROBADO.
4. Guardar el JSON en `<trabajo>/taller-3d/impresoras/<id>.json` y la entrada en `config.json` (`impresoras`, y `impresora_por_defecto` = esta), con el procedimiento de escritura. `datos` es la ruta al JSON, relativa a la carpeta de trabajo. Antes de escribir `config.json`, sumarle el consumo (sección 2, punto 5) con `costos.py consumo --impresora <id> … --salida <config.json>` sobre esa misma copia, y escribirla una sola vez.

`impresora.py desde-gcode <gcode> --id <id>` arma un borrador con lo que usa Orca (modelo, perfil, área, altura, firmware, boquilla, velocidades): sirve para empezar el JSON o para chequear lo investigado. Los límites de temperatura, el cerramiento y las fuentes quedan pendientes: salen del fabricante.

## 5. Si la pieza no entra

Si una pieza no entra en la impresora elegida, ver en cuál de las otras del usuario entra: para las preparadas, `revisar_stl.py --impresora <json> --otras <carpeta taller-3d/impresoras>` (dice en cuáles entra, tal cual o girándola); para las que están en Orca sin preparar, buscar su volumen de impresión oficial. Sugerir la que entra; si la elige y no está preparada, prepararla (secciones 2 a 4). Si no entra en ninguna, ofrecer partirla con encastres o escalarla.

## Formato del JSON

```json
{
  "id": "marca-modelo",
  "nombre": "Marca Modelo",
  "perfiles_maquina": ["Mi Modelo 0.4 nozzle"],
  "patron_perfiles": "Modelo",
  "boquilla_mm": 0.4,
  "firmware": "klipper",
  "cinematica": "corexy",
  "boquilla_tipo": "acero endurecido",
  "area": {"x_min": 0, "x_max": 256, "y_min": 0, "y_max": 256, "z_max": 256},
  "margen_mm": 5,
  "limites": {"boquilla_max_c": 300, "cama_max_c": 100, "velocidad_max_mm_s": 500, "aceleracion_max_mm_s2": 20000},
  "cerramiento": false,
  "sistema": {
    "maquina": {"nombre": "Marca Modelo 0.4 nozzle", "setting_id": "..."},
    "procesos": {"0.20": {"nombre": "0.20mm Standard @Marca Modelo", "setting_id": "..."}},
    "filamentos": {"PETG": {"nombre": "Generic PETG @Marca Modelo", "setting_id": "..."}}
  },
  "cama_sistema": {"PLA": [60, 60], "PETG": [70, 70]},
  "fuentes": ["https://<sitio del fabricante>/...", "https://github.com/OrcaSlicer/OrcaSlicer/..."]
}
```

Los números del ejemplo son de muestra: cada valor sale de la impresora real.

| Campo | De dónde sale |
|---|---|
| `nombre` (el `printer_model` de Orca), `perfiles_maquina`, `area`, `firmware`, `boquilla_mm` | Orca: el perfil de máquina del usuario (`impresora.py desde-gcode`) |
| `patron_perfiles` | Cómo aparece la impresora al final de los nombres de perfiles (`... @Modelo`, `... @Modelo-all`, `Modelo 0.4 nozzle`); lo usa la revisión automática para reconocerla cuando el G-code no trae `printer_model`. Por defecto el modelo completo (`Creality Hi`, `Bambu Lab A1 mini`), como lo arma `desde-gcode`; acortarlo solo si los perfiles de sistema lo nombran así y no se confunde con otro modelo. Los perfiles AUTO se llaman `AUTO proceso @<patron_perfiles>` |
| `limites.boquilla_max_c`, `limites.cama_max_c` | Fabricante. Obligatorios |
| `cerramiento`, `cinematica`, `boquilla_tipo`, `limites.velocidad_max_mm_s`, `limites.aceleracion_max_mm_s2` | Fabricante (o el perfil de Orca para las velocidades) |
| `sistema`, `cama_sistema` | Perfiles de OrcaSlicer de ese modelo. `cama_sistema`: [otras capas, primera capa] para la cama por defecto |
| `margen_mm` | 5 por defecto: tolerancia del control de área (purgas y limpieza de boquilla al borde de la cama) |
| `fuentes` | Los enlaces de donde salió cada dato. Al menos uno oficial |
