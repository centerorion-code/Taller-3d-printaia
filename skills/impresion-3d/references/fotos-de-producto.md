# Fotos de producto para la publicación

Lo usa la skill `publicar` (sección 2). Scripts: `render_producto.py` y `vista_previa.py`.

1. **Fotos reales**, si las hay: son la imagen principal.
2. **Fotos de producto renderizadas** (antes de imprimir, o para sumar vistas): con Blender, **en la PC si está el conector de Blender** (herramienta `execute_blender_code_for_cli`: unas 3 veces más rápido y sin instalar nada) o, si no, en el espacio de Claude.

   **En la PC.** Por ese conector solo se corre `render_producto.py`, siempre con Blender en segundo plano: nunca en la ventana abierta (el script arranca con una escena vacía y borraría lo que haya), ni otro código, ni programas.
   1. Escribir en `<trabajo>/taller-3d/blender/` el `render_producto.py` del plugin y `datos/vacio.blend` (procedimiento de escritura; se pisan en cada publicación).
   2. Una llamada por vista, porque el conector espera 80 s: `blend_file` = `<trabajo>/taller-3d/blender/vacio.blend` y `code`:
      ```python
      import sys; sys.path.insert(0, "<trabajo>/taller-3d/blender")
      import render_producto as rp
      result = rp.renderizar_crudos("<STL de la pieza en la PC>", "<trabajo>/taller-3d/blender/crudos",
          ["<vista>"], color="<color>", material="<m>", capa_mm=<capa>, gpu=True)
      ```
      Vistas: `tres_cuartos` (para `principal` y `tienda`), `atras`, `frente`, `arriba`. Si una llamada no contesta a tiempo, el render sigue en la PC: esperar y mirar `crudos/` con `device_list_dir`; no repetirla.
   3. Traer `crudos/` (`device_stage_files`, los `<vista>.png` y `<vista>-mascara.png`) y armar acá las fotos (solo Pillow): `python3 -I render_producto.py --desde-crudos <crudos traídos> --salida <carpeta>/producto --tomas principal,atras,frente,arriba`.
   Si el conector falla (por ejemplo, un Blender viejo que no abre `vacio.blend`, guardado con la 5.3), hacerlas en el espacio de Claude.

   **En el espacio de Claude:**
   ```bash
   pip install --break-system-packages bpy pillow          # unos 400 MB, una vez por conversación
   python3 -I render_producto.py --stl pieza.stl --salida <carpeta>/producto --color "<color>" \
     --material <m> --capa <altura de capa del G-code> [--tomas principal,atras,frente,arriba,tienda]
   ```
   Por defecto salen **cuatro fotos desde ángulos distintos**, cuadradas, sin texto, con la pieza en el 80 % del cuadro y numeradas en el orden de la galería: `producto-1-principal.jpg` (a tres cuartos, fondo blanco puro, sin sombra: la primera foto de Mercado Libre), `producto-2-atras.jpg` (el otro lado: la pieza girada 180°), `producto-3-frente.jpg` y `producto-4-arriba.jpg` (fondo blanco con sombra suave). La toma `tienda` suma `producto-5-tienda.jpg` (el ángulo de la principal con fondo claro cálido, para redes). Si un ángulo repite otro (una pieza igual de los dos lados) o no muestra nada (una placa vista de frente), sacarlo de `--tomas`. Tardan unos 7 minutos las cuatro (1200 px, 16 muestras): avisar antes, lanzarlas en segundo plano y, mientras tanto, seguir con el texto (sección 3). Mirarlas antes de mostrarlas. Los archivos se hacen en el espacio de Claude y se escriben en la carpeta `producto/` de la pieza en la PC (procedimiento de escritura).
3. **Si no se puede instalar Blender:** `vista_previa.py pieza.stl <carpeta>/producto/foto_producto.png --producto --color "<color>"` (más simple, también sin texto; `--leyenda` agrega "Imagen ilustrativa" abajo, solo para tiendas propias).
4. Reglas de Mercado Libre para la primera foto: fondo blanco puro, sin textos, logos ni marcas de agua, el producto ocupando la mayor parte del cuadro, cuadrada y de 1200 px o más. Las renderizadas ya cumplen.
