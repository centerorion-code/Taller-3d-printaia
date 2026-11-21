# Perfiles de usuario de OrcaSlicer 2.5.1

Crear y modificar siempre con `perfil_orca.py` (valida y escribe el `.info`). Esto es solo para entender el formato.

## Formato

- **Proceso** (`.../process/<nombre>.json`):
  `{"from":"User","inherits":"<perfil de SISTEMA>","is_custom_defined":"0","name":"<nombre>","print_settings_id":"<nombre>","version":"2.5.1.0", ...anulaciones}`. Valores como texto: `"60"`, `"50%"`, `"1"`, `"gyroid"`.
- **Filamento** (`.../filament/`): igual, con `"filament_settings_id":["<nombre>"]` y valores como listas: `"nozzle_temperature":["240"]`.
- **Máquina** (`.../machine/`): `printer_settings_id`; los valores por extrusor van como listas.
- **Herencia:** `inherits` tiene que ser un perfil **de sistema** (si se hereda de uno de usuario, Orca lo ignora). Un perfil derivado repite todas las anulaciones del perfil de usuario base.
- **`.info`** opcional al lado del `.json`:
  ```
  sync_info = create
  user_id = 
  setting_id = 
  base_id = <setting_id del padre de sistema>
  updated_time = <epoch>
  ```

## Perfiles de trabajo

- `AUTO proceso @<impresora>` y `AUTO filamento @<impresora>`: los rehace el taller en cada pieza; se pueden sobrescribir sin preguntar (con respaldo).
- `TEST ...`: perfiles de pruebas; se pueden borrar cuando terminan los tests.
- Cualquier otro perfil del usuario: solo con su permiso.

## Laminar con perfiles por nombre (orca-mcp)

`slice_model(model_path, machine_profile, process_profile, filament_profile, output_dir)` con los nombres de usuario (por ejemplo `Mi Ender-3 V3 Plus 0.4 nozzle`, `AUTO proceso @Ender-3 V3 Plus`, el filamento del usuario). `output_dir` dentro de la carpeta de trabajo (ruta absoluta).

## Tipo de cama

En la ventana de Orca, la temperatura de cama sale del tipo de cama elegido (`curr_bed_type`): Cool Plate → `cool_plate_temp*`, High Temp Plate → `hot_plate_temp*`, Textured PEI Plate → `textured_plate_temp*`, Engineering Plate → `eng_plate_temp*`.

**Por línea de comandos (orca-mcp) Orca ignora `curr_bed_type` aunque esté en el proceso y usa siempre Cool Plate** (comprobado con Orca 2.5.1: la cabecera dice `curr_bed_type = Cool Plate`). Consecuencia: un PLA genérico puede salir con la cama a 35 °C. Solución del taller: laminar siempre con `AUTO filamento`, creado con `perfil_orca.py crear --tipo filamento --cama "<cama real>"`, que copia las temperaturas de esa cama a `cool_plate_temp` y `cool_plate_temp_initial_layer` (las toma del perfil del usuario o, si no las define, de `cama_sistema` en los datos de la impresora). Verificar con `revisar_gcode.py --cama-primera-capa` (`START_PRINT ... BED_TEMP=`).

## Perfiles de sistema de la Ender-3 V3 Plus (boquilla 0.4)

- Máquina: `Creality Ender-3 V3 Plus 0.4 nozzle` (setting_id `HGz252Lczho2ktAf`).
- Procesos: `0.12mm Fine`, `0.16mm Optimal`, `0.20mm Standard`, `0.24mm Draft` + ` @Creality Ender-3 V3 Plus` (ids en `datos/impresoras/ender-3-v3-plus.json`).
- Filamentos: `Generic PLA/PETG/ABS/ASA/TPU/PA/PC/PLA-CF/PETG-CF @Ender-3 V3 Plus-all`, `Hyper PLA/PETG @Ender-3 V3 Plus-all`, `CR-PLA/CR-PETG/... @Ender-3 V3 Plus-all`.
- Valores de sistema del 0.20 (muy rápidos para calidad): pared externa 200 mm/s a 5000 mm/s², relleno 300, 3 paredes, 3 capas arriba y abajo, 15 % crosshatch.

## Verificar un perfil

1. `perfil_orca.py validar <archivo>`.
2. `list_profiles` para ver que Orca lo encuentra.
3. Laminado de prueba y revisar la cabecera del G-code (`; clave = valor` al final del archivo) con `device_stage_files` + `grep`.
