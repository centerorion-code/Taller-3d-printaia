---
name: publicar
description: Arma el producto de una pieza impresa (fotos, medidas, material, cuidados y precio según costo y margen) y lo carga como borrador en la tienda del usuario (WooCommerce, otra plataforma por CSV, o ficha lista para copiar). Se usa cuando el usuario dice "publicá la pieza", "subila a la tienda", "cargala como producto", "armá la publicación" o "cuánto la vendo".
---

# /publicar: de la pieza al producto en la tienda

Cargar antes la skill `impresion-3d` y seguir sus reglas. Script: `<raíz del plugin>/skills/impresion-3d/scripts/producto_tienda.py`.

## Reglas propias

- **Siempre como borrador.** Nunca dejar el producto visible al público: lo publica el usuario después de revisarlo.
- **Fotos reales para publicar.** Antes de imprimir, el borrador se puede armar con una imagen ilustrativa: `vista_previa.py pieza.stl foto_producto.png --producto --color "<color>"` (lleva la leyenda "Imagen ilustrativa (render 3D)"; si Blender está conectado y el usuario quiere algo más vistoso, un render de Blender con la misma leyenda). En la descripción, aclarar que la imagen es ilustrativa. Antes de que el usuario lo publique, recordarle sumar fotos reales de la pieza impresa como imagen principal.
- **Nada que no se pueda sostener:** no afirmar aptitud para alimentos, uso médico, certificaciones ni resistencias que no se midieron. Los cuidados salen del material.
- **Sin claves en archivos.** No pedir ni guardar contraseñas en `config.json`; si la tienda necesita iniciar sesión, la inicia el usuario en el navegador.
- No subir el modelo (STL, 3MF) ni el G-code a la tienda.
- **Modelos ajenos:** si la pieza sale de un modelo bajado de internet, preguntar de dónde y revisar su licencia antes de publicar. Si es de uso no comercial (por ejemplo, CC BY-NC) o no tiene licencia clara, avisar que no se puede vender sin permiso del autor y no cargarla.

## 1. Datos de la pieza

1. Ubicar la carpeta de la pieza en `<trabajo>/impresiones/...` y traer `informe_gcode.json`, `pieza.stl` (o su informe) y `vista.png`. Si no hay G-code laminado, ofrecer `/pieza` primero: sin tiempo y gramos no hay costo.
2. Si no hay `informe_stl.json`, generarlo: `revisar_stl.py pieza.stl --material <m> --json informe_stl.json`.
3. Pedir lo que falte: nombre comercial, para qué sirve (una frase), color, categoría, y las fotos reales si ya está impresa (pueden mandarlas desde el celular). Si todavía no está impresa, generar la imagen ilustrativa (reglas de arriba).
4. Mostrar la publicación armada (título, precio, imagen, descripción) y esperar la aprobación del usuario antes de cargarla. Puede aprobar desde la app de Claude en el celular.

## 2. Precio

1. Traer `taller-3d/config.json`. Si faltan `costos.precio_kwh`, el precio por kg del filamento, `tienda.margen_pct`, `costo_hora_maquina` o `embalaje`, preguntarlos una vez y guardarlos (con respaldo).
2. Correr:
   ```bash
   python3 -I producto_tienda.py --nombre "<nombre>" --material <m> --color "<color>" --uso "<frase>" \
     --categoria "<categoría>" --etiquetas "<a,b>" --informe-gcode informe_gcode.json \
     --informe-stl informe_stl.json --config config.json --salida <carpeta>/producto \
     [--plantilla <csv exportado de su plataforma>] [--precio <precio elegido>]
   ```
3. Mostrar el cálculo (material, luz, horas de máquina, embalaje, margen) y el precio sugerido redondeado. El precio final lo decide el usuario.

## 3. Cargar según la plataforma (`tienda.plataforma`)

- **WooCommerce:**
  1. Si hay herramientas de WordPress/WooCommerce conectadas (por ejemplo, el plugin del adaptador MCP de WordPress), crear el producto con los datos de `producto.json` y estado **borrador**; subir las fotos a la biblioteca de medios y asignarlas.
  2. Si no, usar el navegador: abrir `<url>/wp-admin/post-new.php?post_type=product`, completar nombre, descripción, descripción corta, precio, SKU, peso, medidas, categoría y etiquetas, subir las fotos y **Guardar borrador** (no "Publicar"). Si pide iniciar sesión, que la inicie el usuario.
  3. Si no hay navegador ni conexión, dejar `producto_woocommerce.csv` (ya viene con Publicado = -1, borrador) y explicar: Productos → Importar → elegir el archivo → mapear columnas → Ejecutar; después subir las fotos al producto.
- **Tiendanube, Shopify u otra con importación por CSV:** pedir que exporte su plantilla de productos (en Tiendanube: Productos → Lista de productos → Exportar e importar) y pasarla con `--plantilla`. El script completa una fila respetando los encabezados y deja el producto oculto (Tiendanube: "Mostrar en tienda" = NO). Las fotos se suben aparte. Si el usuario prefiere, cargarlo por el navegador como borrador u oculto.
- **Mercado Libre, Instagram, Facebook u otra:** entregar `ficha.md` con título, descripción, precio, medidas y fotos, lista para copiar. Si quiere, completar el formulario en el navegador hasta antes de publicar y dejar que él confirme.

## 4. Cerrar

1. Dejar en `<carpeta de la pieza>/producto/`: `producto.json`, `producto_woocommerce.csv`, `ficha.md` (y `plantilla_completa.csv` si corresponde), más las fotos.
2. Decir dónde quedó el borrador (enlace al producto en el administrador si se creó) y qué falta revisar antes de publicarlo.
3. Actualizar el panel (skill `panel`) con `--producto <carpeta>/producto/producto.json` y, si hay, el enlace público del producto en `--url-tienda`.
3. Registrar en `historial.csv`.
