---
name: publicar
description: Arma el producto de una pieza impresa (fotos, medidas, material, cuidados y precio según costo y margen) y lo carga como borrador en la tienda del usuario (WooCommerce, otra plataforma por CSV, o ficha lista para copiar). Se usa cuando el usuario dice "publicá la pieza", "subila a la tienda", "cargala como producto", "armá la publicación" o "cuánto la vendo".
---

# /publicar: de la pieza al producto en la tienda

Cargar antes la skill `impresion-3d` y seguir sus reglas. Scripts en `<raíz del plugin>/skills/impresion-3d/scripts/`: `producto_tienda.py`, `costos.py` y `render_producto.py`. Cómo se calculan el costo y el precio: `references/costos.md`.

## Reglas propias

- **Siempre como borrador.** Nunca dejar el producto visible al público: lo publica el usuario después de revisarlo.
- **Fotos reales para publicar.** Si la pieza todavía no está impresa, el borrador lleva fotos de producto renderizadas (sección 2) y la descripción aclara que son ilustrativas. Antes de que el usuario lo publique, recordarle sumar fotos reales de la pieza impresa como imagen principal.
- **Nada que no se pueda sostener:** no afirmar aptitud para alimentos, uso médico, certificaciones ni resistencias que no se midieron. Los cuidados salen del material.
- **Sin claves en archivos.** No pedir ni guardar contraseñas en `config.json`; si la tienda necesita iniciar sesión, la inicia el usuario en el navegador.
- No subir el modelo (STL, 3MF) ni el G-code a la tienda.
- **Modelos ajenos:** si la pieza sale de un modelo bajado de internet, preguntar de dónde y revisar su licencia antes de publicar. Si es de uso no comercial (por ejemplo, CC BY-NC) o no tiene licencia clara, avisar que no se puede vender sin permiso del autor y no cargarla.
- **El margen lo elige el usuario en cada producto** (sección 3). No publicar con el margen habitual sin preguntarle.

## 1. Datos de la pieza

1. Ubicar la carpeta de la pieza en `<trabajo>/impresiones/...` y traer `informe_gcode.json`, `pieza.stl` (o su informe) y `vista.png`. Si no hay G-code laminado, ofrecer `/pieza` primero: sin tiempo y gramos no hay costo.
2. Si no hay `informe_stl.json`, generarlo: `revisar_stl.py pieza.stl --material <m> --json informe_stl.json`.
3. Pedir lo que falte: nombre comercial, para qué sirve (una frase), color, categoría, y las fotos reales si ya está impresa (pueden mandarlas desde el celular).

## 2. Fotos

1. **Fotos reales**, si las hay: son la imagen principal.
2. **Fotos de producto renderizadas** (antes de imprimir, o para sumar vistas): con Blender, en el espacio de Claude.
   ```bash
   pip install --break-system-packages bpy pillow          # unos 400 MB, una vez por conversación
   python3 -I render_producto.py --stl pieza.stl --salida <carpeta>/producto --color "<color>" \
     --material <m> --capa <altura de capa del G-code> [--tomas principal,tienda,frente,arriba]
   ```
   Salen cuadradas, sin texto, con la pieza en el 80 % del cuadro: `producto-1-principal.jpg` (fondo blanco puro, sin sombra: la primera foto de Mercado Libre), `producto-2-tienda.jpg` (fondo claro con sombra suave), y si se piden, `producto-3-frente.jpg` y `producto-4-arriba.jpg`. Tardan unos 3 minutos las dos primeras y 7 las cuatro: avisar antes. Los archivos se hacen en el espacio de Claude y se escriben en la carpeta `producto/` de la pieza en la PC (procedimiento de escritura).
3. **Si no se puede instalar Blender:** `vista_previa.py pieza.stl <carpeta>/producto/foto_producto.png --producto --color "<color>"` (más simple, también sin texto; `--leyenda` agrega "Imagen ilustrativa" abajo, solo para tiendas propias).
4. Reglas de Mercado Libre para la primera foto: fondo blanco puro, sin textos, logos ni marcas de agua, el producto ocupando la mayor parte del cuadro, cuadrada y de 1200 px o más. Las renderizadas ya cumplen.

## 3. Precio

1. Traer `taller-3d/config.json` y correr `costos.py estado --config config.json`. Si falta algo para el costo, pedirlo de a un dato con su frase (la boleta de luz, el consumo, el precio de la impresora, el precio del filamento, tu hora, las comisiones del canal) y guardarlo con respaldo. Si el usuario prefiere seguir sin eso, seguir: el precio sale con la lista de lo que falta.
2. Opciones de margen:
   ```bash
   python3 -I costos.py pieza --config config.json --informe-gcode informe_gcode.json \
     --impresora "<impresora>" --margenes --json costo.json
   ```
3. **Preguntarle al usuario qué margen quiere en este producto**, con AskUserQuestion: una opción por margen (el más bajo, su habitual marcado "(tu margen habitual)", el más alto), cada una con el precio y la ganancia en su canal principal; con la opción de escribir un precio exacto. Si no hay AskUserQuestion, preguntarlo en una línea con las tres opciones.
4. Si eligió un precio exacto, mostrar el margen real que le deja en cada canal (`costos.py pieza … --precio <precio>`). Si en algún canal la ganancia da negativa, decirlo claro antes de seguir.
5. Armar la ficha con lo elegido:
   ```bash
   python3 -I producto_tienda.py --nombre "<nombre>" --material <m> --color "<color>" --uso "<frase>" \
     --categoria "<categoría>" --etiquetas "<a,b>" --informe-gcode informe_gcode.json \
     --informe-stl informe_stl.json --config config.json --salida <carpeta>/producto \
     (--margen <margen elegido> | --precio <precio elegido>) [--canal mercadolibre] \
     [--plantilla <csv exportado de su plataforma>]
   ```
6. Mostrar la publicación armada (título, precio, fotos, descripción, y el costo con sus partes y el precio por canal) y esperar la aprobación del usuario antes de cargarla. Puede aprobar desde la app de Claude en el celular.

## 4. Cargar según la plataforma (`tienda.plataforma`)

- **WooCommerce:**
  1. Si hay herramientas de WordPress/WooCommerce conectadas (por ejemplo, el plugin del adaptador MCP de WordPress), crear el producto con los datos de `producto.json` y estado **borrador**; subir las fotos a la biblioteca de medios y asignarlas.
  2. Si no, usar el navegador: abrir `<url>/wp-admin/post-new.php?post_type=product`, completar nombre, descripción, descripción corta, precio, SKU, peso, medidas, categoría y etiquetas, subir las fotos y **Guardar borrador** (no "Publicar"). Si pide iniciar sesión, que la inicie el usuario.
  3. Si no hay navegador ni conexión, dejar `producto_woocommerce.csv` (ya viene con Publicado = -1, borrador) y explicar: Productos → Importar → elegir el archivo → mapear columnas → Ejecutar; después subir las fotos al producto.
- **Tiendanube, Shopify u otra con importación por CSV:** pedir que exporte su plantilla de productos (en Tiendanube: Productos → Lista de productos → Exportar e importar) y pasarla con `--plantilla`. El script completa una fila respetando los encabezados y deja el producto oculto (Tiendanube: "Mostrar en tienda" = NO). Las fotos se suben aparte. Si el usuario prefiere, cargarlo por el navegador como borrador u oculto.
- **Mercado Libre, Instagram, Facebook u otra:** entregar `ficha.md` con título, descripción, precio, medidas y fotos, lista para copiar. Si quiere, completar el formulario en el navegador hasta antes de publicar y dejar que él confirme.

## 5. Cerrar

1. Dejar en `<carpeta de la pieza>/producto/`: `producto.json`, `producto_woocommerce.csv`, `ficha.md` (y `plantilla_completa.csv` si corresponde), más las fotos.
2. Decir dónde quedó el borrador (enlace al producto en el administrador si se creó) y qué falta revisar antes de publicarlo.
3. Actualizar el panel (skill `panel`) con `--producto <carpeta>/producto/producto.json`, la foto principal en `--archivos`, y si hay, el enlace público del producto en `--url-tienda`.
4. Registrar en `historial.csv`.
5. Terminar con una línea "Te toca: …" (revisar el borrador y publicarlo, o imprimir la pieza y sacarle fotos).
