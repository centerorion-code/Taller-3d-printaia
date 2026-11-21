# Impresoras: elegir, investigar y configurar

El plugin no trae impresoras cargadas: hay demasiados modelos y cada persona tiene las suyas, muchas veces varias en el mismo Orca. Los datos de una impresora se arman cuando el usuario elige trabajar en ella y quedan en su carpeta de trabajo (`taller-3d/impresoras/<id>.json`) para la próxima vez. No se preparan todas de entrada: solo la que va a usar.

## 1. En qué impresora trabajar

1. `list_profiles` de orca-mcp con `machine`: los perfiles de máquina de usuario de Orca, cada uno con su `inherits` (el perfil de sistema: marca, modelo y boquilla).
2. Si el usuario ya dijo en cuál, usar esa. Si hay una sola, usarla y decirlo. Si hay varias, **preguntar en cuál quiere trabajar** (`AskUserQuestion` con los nombres de Orca; primero la última usada, `impresora_por_defecto` en `config.json`).
3. Si la que quiere no aparece, puede estar en Orca solo como impresora del sistema, sin copia de usuario, y orca-mcp lamina con perfiles de usuario. Darle los pasos: en Orca, elegir esa impresora y en su configuración guardar una copia (ícono de guardar) como `Mi <modelo> <boquilla> nozzle`. Si no está en Orca, agregarla con el asistente de impresoras (marca y modelo). Verificar con `list_profiles`.
4. Si esa impresora ya está preparada en el taller (en `config.json`, con `datos` apuntando a un JSON que pasa `impresora.py validar`), usar esos datos. Si no, seguir con la sección 2.

## 2. Investigar la impresora

Con el modelo exacto (el `inherits` del perfil de máquina, por ejemplo `<Marca> <Modelo> 0.4 nozzle`), buscar en internet:

1. **El fabricante** (página del producto, manual o ficha técnica oficial): temperatura máxima de boquilla y de cama, volumen de impresión, firmware, cerramiento, hotend, cinemática y velocidades máximas.
2. **Los perfiles de OrcaSlicer de ese modelo** (repositorio de OrcaSlicer, `resources/profiles/<Marca>/`, de la versión que usa el usuario): nombres y `setting_id` de los perfiles de sistema de máquina, procesos por altura de capa y filamentos por material, y las temperaturas de cama de esos filamentos (`cama_sistema`).
3. Lo que no aparezca en fuentes oficiales se pregunta. **No inventar límites**: sin `boquilla_max_c` y `cama_max_c` del fabricante, el taller no lamina para esa impresora. Los foros, tiendas y videos no cuentan como fuente de límites.
4. Armar el JSON (formato abajo), con cada enlace en `fuentes`, y correr `python3 -I impresora.py validar <json>`: tiene que salir APROBADO, o con advertencias que se explican al usuario.

## 3. Configurarla óptima

1. Preguntar qué cama usa en esa impresora, si no está en la configuración ("Textured PEI Plate", "High Temp Plate", "Cool Plate", "Engineering Plate"...).
2. Perfiles de trabajo: `AUTO proceso @<modelo corto>` y `AUTO filamento @<modelo corto>`, heredando de los perfiles de sistema investigados, con `perfil_orca.py crear --impresora <json>` y los criterios de `recetas.md` (calidad, resistencia, velocidad), siempre dentro de los límites de la impresora. El de filamento, con `--cama "<cama real>"`.
3. Si el usuario ya tiene perfiles propios de proceso y filamento para esa impresora, anotarlos en `config.json` (`procesos`, `filamentos`) y usarlos de base.

## 4. Probar y guardar

1. Cubo de 20 mm con `cad.py`, laminado con orca-mcp con el perfil de máquina del usuario y los AUTO. Traer el G-code.
2. `python3 -I impresora.py comparar <json> <gcode>`: los datos tienen que coincidir con lo que usa Orca (modelo, perfil, área, altura, firmware y boquilla). Si no coinciden, mostrarle las dos cosas al usuario. Lo que usa Orca es lo real, salvo que su área sea más grande que la oficial: ahí manda la oficial y conviene revisar el perfil en Orca. Corregir el JSON y repetir.
3. `revisar_gcode.py <gcode> --impresora <json> --cama-primera-capa <temperatura>`: tiene que salir APROBADO.
4. Guardar el JSON en `<trabajo>/taller-3d/impresoras/<id>.json` y la entrada en `config.json` (`impresoras`, y `impresora_por_defecto` = esta), con el procedimiento de escritura. `datos` es la ruta al JSON, relativa a la carpeta de trabajo.

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
| `patron_perfiles` | El modelo como aparece en los nombres de los perfiles (`... @Modelo`); lo usa la revisión automática para reconocer la impresora |
| `limites.boquilla_max_c`, `limites.cama_max_c` | Fabricante. Obligatorios |
| `cerramiento`, `cinematica`, `boquilla_tipo`, `limites.velocidad_max_mm_s`, `limites.aceleracion_max_mm_s2` | Fabricante (o el perfil de Orca para las velocidades) |
| `sistema`, `cama_sistema` | Perfiles de OrcaSlicer de ese modelo. `cama_sistema`: [otras capas, primera capa] para la cama por defecto |
| `margen_mm` | 5 por defecto: tolerancia del control de área (purgas y limpieza de boquilla al borde de la cama) |
| `fuentes` | Los enlaces de donde salió cada dato. Al menos uno oficial |
