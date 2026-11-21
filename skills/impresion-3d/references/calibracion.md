# Calibración de filamentos en OrcaSlicer 2.5.1

Las calibraciones se lanzan desde la ventana de Orca (menú **Calibración**), en la PC: el plugin no puede generarlas por línea de comandos. Antes de cada una: elegir en Orca la impresora, el filamento que se calibra y la cama.

## Orden (wiki de OrcaSlicer)

| # | Menú de Orca | Qué se elige | Cómo leerlo | Dónde va el resultado |
|---|---|---|---|---|
| 1 | Calibración → Temperatura (torre) | rango del material, paso 5 °C | el tramo con mejores puentes, menos hilos y buena unión; usar el medio del rango bueno | `nozzle_temperature` (+5 °C en `nozzle_temperature_initial_layer`) |
| 2 | Calibración → Test de Flujo Máximo | inicio y fin (PETG 5→20, PLA 5→25), paso 0,5 | buscar la altura donde la superficie se deforma o pierde brillo; valor = inicio + altura(mm) × paso; usar 10-20 % menos | `filament_max_volumetric_speed` |
| 3 | Calibración → Pressure Advance → Torre PA (extrusor directo: 0 → 0,1, paso 0,002) | | la altura con esquinas más nítidas; PA = inicio + altura(mm) × paso | `enable_pressure_advance`=1 y `pressure_advance` |
| 4 | Calibración → Test de Flujo → YOLO (recomendado) | | el cuadrado con la superficie superior más lisa, sin huecos ni rebabas; nuevo = actual × (1 + modificador/100) o actual + modificador según indique Orca | `filament_flow_ratio` |
| 5 | Calibración → Retracción | 0 → 2 mm, paso 0,1 | la primera altura sin hilos; longitud = altura(mm) × paso | `filament_retraction_length` |
| 6 (opcional) | Calibración → Tolerancia | | qué pernos entran y cuáles giran | holguras para `cad.py` y `xy_hole_compensation` |

Si el flujo cambió mucho, repetir el pressure advance. Esquinado (cornering), VFA y PA adaptativo son opcionales y van al final. El input shaping se calibra con la rutina propia de la impresora si la tiene (muchas impresoras con Klipper traen acelerómetro y autochequeo: ver el manual del fabricante).

## Leer resultados con fotos

- Pedir una foto de frente, con buena luz, regla o calibre al lado, y la altura donde se ve el cambio.
- Si no se puede leer con seguridad, pedir la medición con calibre: altura en mm desde la base.
- Anotar en `calibraciones/<filamento>.md`: fecha, test, parámetros del test, lectura, valor final, foto (nombre del archivo).

## Guardar el resultado

1. Traer el perfil del filamento con `device_stage_files`.
2. `perfil_orca.py crear --tipo filamento --nombre "<mismo nombre>" --hereda "<su inherits>" --base <perfil traído> --set <clave>=<valor> --anterior <perfil traído> --salida ...`
3. Mostrar los cambios, pedir OK (es un perfil del usuario), respaldar y escribir (procedimiento de escritura de la skill impresion-3d).
4. Laminar una pieza chica de prueba y verificar en la cabecera del G-code que tomó el valor.

## Puntos de partida (antes de calibrar)

| Material | Boquilla | Cama | Ventilador | MVS | Retracción (directo) | PA (directo, Klipper) |
|---|---|---|---|---|---|---|
| PLA | 205-220 °C | 55-60 °C | 80-100 % | 15-20 (Hyper ~23) | 0,5-0,8 mm | 0,02-0,05 |
| PETG | 235-245 °C | 70-80 °C | 30-50 % | 9-12 (Hyper ~20) | 0,6-1,0 mm | 0,03-0,07 |
| TPU 95A | 220-230 °C | 40-50 °C | 50 % | 3-5 | 0,4-0,8 mm lenta | 0,05-0,1 |
