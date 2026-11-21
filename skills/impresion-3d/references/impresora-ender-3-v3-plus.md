# Creality Ender-3 V3 Plus: capacidades y límites

- **Mecánica y área:** CoreXZ con cama que se mueve en Y (cama pesada de 300×300). Volumen 300×300×330 mm.
- **Velocidad:** hasta 600 mm/s y 20 000 mm/s² según el fabricante; lo típico es ~300 mm/s y, para calidad, mucho menos en la pared externa.
- **Firmware:** basado en Klipper (en Orca, flavor `klipper`; macros `START_PRINT EXTRUDER_TEMP=.. BED_TEMP=..` y `END_PRINT`). El jerk de Orca equivale a `square_corner_velocity`.
- **Input shaping:** con sensor incorporado; calibrar con el autochequeo de la impresora, no con el test de Orca.
- **Hotend:** 60 W, hasta 300 °C, boquilla de acero endurecido de cambio rápido. Extrusor directo.
- **Cama:** hasta 100 °C, nivelado automático.
- **Ventiladores:** dos de pieza; el auxiliar se maneja con `additional_cooling_fan_speed` (en PETG, 0).
- **Abierta:** sin cerramiento; ABS, ASA, PC y nylon se complican (alabeo, grietas, vapores).

## Límites prácticos para calidad

- Aceleración de pared externa 2000-3000 y de cara superior 2000-3000; primera capa 500.
- Jerk/SCV 5-7 en paredes externas.
- Piezas altas y finas: bajar aceleraciones y poner el lado largo de la base sobre Y (la cama).
- Caudal (MVS): PETG genérico 9 mm³/s hasta medirlo; filamentos "Hyper/HS" llegan a ~20+.

## Enviar trabajos

El taller no envía nada a la impresora: entrega el G-code. La persona lo pasa por USB o por la app de la marca y arranca la impresión desde la impresora.
