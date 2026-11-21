# Parámetros que más pesan (OrcaSlicer 2.5.1)

Para cualquier otro, buscar en el catálogo (`references/catalogo-orca-2.5.1/parametros-*.json`, un parámetro por línea) (tiene nombre en español, explicación, tipo, rango, valores posibles y en qué perfil va).

## Calidad visible
- `layer_height`; anchos `*_line_width` (externo 0.42, interno 0.45 para boquilla 0.4).
- Costura: `seam_position` (aligned, back, nearest, random), `seam_gap` (0-15 % si PA y flujo están calibrados), `seam_slope_type` + `seam_slope_conditional` + `seam_slope_start_height` + `seam_slope_steps` (costura en bisel), `wipe_on_loops`.
- `precise_outer_wall`; `wall_sequence` (inner/outer = mejores voladizos; outer/inner o inner-outer-inner = más precisión de medidas); `wall_generator` (arachne en piezas finas o con detalle).
- Planchado: `ironing_type`, `ironing_speed` (≈30), `ironing_flow` (≈10 %), `ironing_spacing` (≈0.1).
- Cara superior: `top_surface_pattern`, `top_shell_layers`, `top_shell_thickness`, `top_surface_speed`, `top_surface_acceleration`.

## Velocidad y movimiento
- `*_speed` (paredes externa/interna, relleno, sólido interno, superior, puentes, huecos).
- `*_acceleration` y `*_jerk`. En Klipper el jerk de Orca se traduce a `square_corner_velocity`.
- `filament_max_volumetric_speed` (MVS): techo real de caudal; Orca baja la velocidad para respetarlo.
- `max_volumetric_extrusion_rate_slope`: suaviza cambios bruscos de caudal (probar 300 si hay bultos en las costuras).

## Enfriamiento (perfil de filamento)
- `fan_min_speed` / `fan_max_speed` con los umbrales `fan_cooling_layer_time` y `slow_down_layer_time`.
- `close_fan_the_first_x_layers`, `full_fan_speed_layer`.
- `overhang_fan_speed` y `overhang_fan_threshold` (voladizos y puentes).
- `additional_cooling_fan_speed` (ventilador auxiliar, si la impresora lo tiene).
- Un ventilador parejo (mín ≈ máx) evita bandas.

## Resistencia
- `wall_loops`, `top_shell_layers`, `bottom_shell_layers`, `sparse_infill_density`, `sparse_infill_pattern` (gyroid, cubic, adaptivecubic, lightning…).
- Más temperatura y menos ventilador = mejor unión entre capas.

## Hilos y gotas
- Retracción del filamento: `filament_retraction_length`, `filament_retraction_speed`, `filament_z_hop`, `z_hop_types`.
- `reduce_crossing_wall` (evita cruzar paredes), `wipe`.
- Pressure advance: `enable_pressure_advance` + `pressure_advance` (filamento).
- Temperatura más baja y filamento seco.

## Adhesión y primera capa
- `initial_layer_print_height` (0.2), `initial_layer_speed` (30-40), `initial_layer_acceleration` (500).
- Temperaturas `*_initial_layer` del filamento.
- `brim_type`, `brim_width`, `brim_object_gap`.
- `elefant_foot_compensation` (0.1-0.2).
- `curr_bed_type`: en la ventana de Orca decide qué temperatura de cama se usa; por línea de comandos se ignora y vale Cool Plate (ver perfiles-orca.md).

## Voladizos y puentes
- `enable_overhang_speed` + `overhang_1_4_speed` … `overhang_4_4_speed`.
- `slowdown_for_curled_perimeters`, `bridge_speed`, `bridge_flow`, `thick_bridges`.
- `make_overhang_printable` (cambia la geometría para que no necesite soporte).
- `support_*` (ver recetas).

## Precisión de medidas
- `xy_hole_compensation`, `xy_contour_compensation`, `hole_to_polyhole`, `precise_outer_wall`, `elefant_foot_compensation`.
- Flujo calibrado (`filament_flow_ratio`) antes de tocar compensaciones.
