# Diagnóstico rápido

Pedir una foto con buena luz y, si se puede, de cerca y de costado. Preguntar material, perfil usado y si el filamento estaba seco.

| Problema | Primero tocar |
|---|---|
| Hilos | secar el filamento; −5 °C; retracción +0,2 mm; activar y calibrar PA; `reduce_crossing_wall`=1 |
| Gotas o costura marcada | PA; flujo; `seam_gap`; costura en bisel condicional; `wipe_on_loops` |
| Paredes rugosas | flujo (primero); bajar `outer_wall_speed`; revisar MVS |
| Cara superior con surcos o rugosa | flujo; `top_surface_acceleration` 2000; más capas superiores; planchado |
| Huecos en la cara superior | más `top_shell_layers`; flujo; relleno más denso debajo |
| No pega o se despega | limpiar la cama (agua y detergente, alcohol); +5 °C de cama en la primera capa; primera capa a 30 mm/s; brim; revisar nivelado y offset Z |
| Se pega demasiado (PETG en PEI liso) | pegamento en barra como separador; bajar la cama 5 °C |
| Capas que se separan | +5-10 °C; menos ventilador; menos velocidad; orientar distinto |
| Voladizos caídos | más ventilador en voladizos; velocidades de voladizo más bajas; soportes desde el ángulo límite |
| Bandas horizontales | ventilador más parejo (mín ≈ máx); revisar el tiempo mínimo de capa; temperatura estable |
| Pata de elefante (base más ancha) | `elefant_foot_compensation` 0,15-0,2; cama −5 °C; chaflán de 0,4 mm en el modelo |
| Alabeo (esquinas levantadas) | brim 5-8 mm; cama +5 °C; sin ventilador las primeras capas; evitar corrientes de aire |
| Agujeros chicos | `xy_hole_compensation` +0,05 a +0,1; `hole_to_polyhole`=1; o agrandar en el modelo |
| Piezas más grandes de lo diseñado | flujo; `xy_contour_compensation` −0,05 a −0,1 |
| Subextrusión intermitente | filamento húmedo o enredado; MVS demasiado alto para la velocidad; boquilla parcialmente tapada |
| Fantasmas (ringing) en las paredes | input shaping de la impresora; bajar aceleración de pared externa |
| Burbujas, chasquidos, superficie opaca | filamento húmedo: secarlo |
