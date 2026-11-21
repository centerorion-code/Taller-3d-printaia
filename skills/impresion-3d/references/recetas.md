# Recetas por tipo de pieza

Anulaciones sobre el perfil base (proceso de usuario o de sistema). Valores para boquilla 0,4 mm en una impresora rápida tipo Klipper; en máquinas más lentas, bajar velocidades y aceleraciones en proporción.

## Elegir la base

| Prioridad | Proceso base | Notas |
|---|---|---|
| Detalle fino | 0.12 (o 0.08) | más tiempo; ideal miniaturas y texto chico |
| Calidad visible | 0.16 | buen equilibrio para piezas que se ven |
| General / funcional | 0.20 | la mayoría de las piezas |
| Rápido / prototipo | 0.24 | capas visibles |

## Recetas

| Caso | Claves (clave = valor) |
|---|---|
| **Estético / vitrina** | capa 0.16 (0.12 en detalle); `outer_wall_speed`=50-60; `outer_wall_acceleration`=2000; `top_surface_speed`=60; `top_surface_acceleration`=2000; `top_shell_layers`=6; `seam_position`=aligned o back; `seam_slope_type`=external + `seam_slope_conditional`=1; `precise_outer_wall`=1; `ironing_type`=top si hay tapas planas visibles |
| **Funcional / resistente** | capa 0.20; `wall_loops`=4-6 (las paredes dan más resistencia que el relleno); `top_shell_layers`=5; `bottom_shell_layers`=5; `sparse_infill_density`=30-50% con `gyroid` o `cubic`; temperatura en la parte alta del rango; ventilador máx. 30-40 % en PETG; orientar para que la carga no separe capas |
| **Prototipo rápido** | base 0.24; `wall_loops`=2; `sparse_infill_density`=10-15% (`lightning` o `adaptivecubic` si no es estructural); `seam_position`=nearest; sin planchado |
| **Miniatura / detalle** | base 0.12 (0.08 si hace falta); `outer_wall_speed`=40; `outer_wall_acceleration`=1500; `small_perimeter_speed`=50%; filamento `slow_down_layer_time`=12-15; `wall_generator`=arachne; soportes `tree(auto)` con interfaz |
| **Pieza grande o plana (alabeo)** | `brim_type`=outer_only, `brim_width`=5-8; cama +5 °C en la primera capa; `close_fan_the_first_x_layers`=3-5; `full_fan_speed_layer`=8; `gyroid`; `elefant_foot_compensation`=0.15-0.2 |
| **Encastres / tolerancias** | capa ≤0.20; `precise_outer_wall`=1; `wall_sequence`=inner-outer-inner wall; `hole_to_polyhole`=1; `xy_hole_compensation`=+0.05 a +0.10 si los agujeros salen chicos; `xy_contour_compensation` negativo si las piezas salen grandes; correr una vez el test de tolerancia de Orca (ver calibracion.md) |
| **Exterior / sol / calor** | PETG o ASA (nunca PLA); `wall_loops`=4; relleno ≥30%; temperatura alta del rango |
| **Muchos voladizos / puentes** | filamento `overhang_fan_speed`=100 (o el ganador del test de puentes); `enable_overhang_speed`=1 con `overhang_2_4_speed`=40, `overhang_3_4_speed`=25, `overhang_4_4_speed`=10; `bridge_speed`=25-30; soportes desde el ángulo límite medido: `support_threshold_angle` = 90 − (ángulo límite desde la vertical) |
| **Texto o relieve arriba** | `ironing_type`=topmost; `top_surface_pattern`=monotonicline (concentric en piezas redondas); capa ≤0.16 |
| **Jarrón / vaso decorativo** | `spiral_mode`=1; `spiral_mode_smooth`=1; `bottom_shell_layers`=4; `outer_wall_line_width`=0.6 |
| **PETG transparente** | temperatura alta del rango; 20-40 mm/s; ventilador bajo; capa 0.25-0.3; ancho 0.5-0.6; relleno 100 % `alignedrectilinear` o `concentric`; flujo +2-3 % |
| **TPU / flexible** | filamento TPU del sistema; 20-35 mm/s; MVS 3-5; retracción 0.4-0.8 mm lenta; sin z-hop |
| **Pieza alta y fina** | `outer_wall_acceleration`≤2000 y `default_acceleration`≤4000; `brim_width`=5; lado largo de la base sobre el eje en que se mueve la cama; si es muy fina, imprimir dos o tres juntas o con una pared de sacrificio |

## Soportes

- Activar (`enable_support`=1) solo si `revisar_stl.py` marca voladizos que no son puentes cortos.
- `support_type`=tree(auto) para piezas orgánicas y pocas zonas; normal(auto) para techos planos grandes.
- `support_threshold_angle`: ver receta de voladizos. Con 30 casi todo lo que pase de 60° desde la vertical lleva soporte.
- Para despegar fácil en PETG: `support_top_z_distance`=0.2-0.25 e interfaz (`support_interface_top_layers`=2-3).

## Orientación (antes de laminar)

- La pieza resiste mucho menos entre capas: que la carga quede en el plano de las capas.
- Cara visible arriba (mejor terminación) o vertical (sin escalonado).
- Base ancha y plana sobre la cama; agujeros verticales salen más redondos que horizontales.
- Minimizar soportes y superficies de apoyo marcadas.
