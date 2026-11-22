---
name: publicar
description: Arma el producto de una pieza impresa (fotos, medidas, material, cuidados, texto de venta y precio según costo y margen), muestra una vista previa de cómo se vería en la tienda y, cuando el usuario la aprueba, lo carga como borrador (WooCommerce, otra plataforma por CSV, o ficha lista para copiar). Se usa cuando el usuario dice "publicá la pieza", "subila a la tienda", "cargala como producto", "armá la publicación", "cómo va a quedar publicada" o "cuánto la vendo".
---

# /publicar: de la pieza al producto en la tienda

Cargar antes la skill `impresion-3d` y seguir sus reglas. Scripts en `<raíz del plugin>/skills/impresion-3d/scripts/`: `producto_tienda.py`, `costos.py`, `render_producto.py`, `textos_ia.py` y `vista_publicacion.py`. Cómo se calculan el costo y el precio: `references/costos.md`.

## Reglas propias

- **Siempre como borrador.** Nunca dejar el producto visible al público: lo publica el usuario después de revisarlo.
- **Fotos reales para publicar.** Si la pieza todavía no está impresa, el borrador lleva fotos de producto renderizadas (sección 2) y la descripción aclara que son ilustrativas. Antes de que el usuario lo publique, recordarle sumar fotos reales de la pieza impresa como imagen principal.
- **Nada que no se pueda sostener:** no afirmar aptitud para alimentos, uso médico, certificaciones ni resistencias que no se midieron. Los cuidados salen del material. El texto de venta (lo escriba Gemini o Claude) no agrega datos: medidas, material, peso y cuidados salen de los informes, y el texto pasa por `textos_ia.py revisar` antes de usarse.
- **Sin claves en archivos.** No pedir ni guardar contraseñas en `config.json`; si la tienda necesita iniciar sesión, la inicia el usuario en el navegador.
- No subir el modelo (STL, 3MF) ni el G-code a la tienda.
- **Generada por IA desde una foto:** antes de publicar, confirmar que el usuario puede vender lo que generó Hunyuan (su acuerdo de servicio; ver `references/foto-a-3d.md`, sección 6) y que el objeto de la foto no es de otro.
- **Modelos ajenos:** si la pieza sale de un modelo bajado de internet, preguntar de dónde y revisar su licencia antes de publicar. Si es de uso no comercial (por ejemplo, CC BY-NC) o no tiene licencia clara, avisar que no se puede vender sin permiso del autor y no cargarla. Un personaje, una mascota de marca o un logo ajeno tampoco se vende, aunque la licencia del modelo diga comercial: el personaje o la marca tienen dueño.
- **El margen lo elige el usuario en cada producto** (sección 4). No publicar con el margen habitual sin preguntarle.
- **Se carga después de ver la vista previa** (sección 4, paso 6) y de que el usuario la apruebe.

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
     --material <m> --capa <altura de capa del G-code> [--tomas principal,atras,frente,arriba,tienda]
   ```
   Por defecto salen **cuatro fotos desde ángulos distintos**, cuadradas, sin texto, con la pieza en el 80 % del cuadro y numeradas en el orden de la galería: `producto-1-principal.jpg` (a tres cuartos, fondo blanco puro, sin sombra: la primera foto de Mercado Libre), `producto-2-atras.jpg` (el otro lado: la pieza girada 180°), `producto-3-frente.jpg` y `producto-4-arriba.jpg` (fondo blanco con sombra suave). La toma `tienda` suma `producto-5-tienda.jpg` (el ángulo de la principal con fondo claro cálido, para redes). Si un ángulo repite otro (una pieza igual de los dos lados) o no muestra nada (una placa vista de frente), sacarlo de `--tomas`. Tardan unos 7 minutos las cuatro (1200 px, 16 muestras): avisar antes, lanzarlas en segundo plano y, mientras tanto, seguir con el texto (sección 3). Mirarlas antes de mostrarlas. Los archivos se hacen en el espacio de Claude y se escriben en la carpeta `producto/` de la pieza en la PC (procedimiento de escritura).
3. **Si no se puede instalar Blender:** `vista_previa.py pieza.stl <carpeta>/producto/foto_producto.png --producto --color "<color>"` (más simple, también sin texto; `--leyenda` agrega "Imagen ilustrativa" abajo, solo para tiendas propias).
4. Reglas de Mercado Libre para la primera foto: fondo blanco puro, sin textos, logos ni marcas de agua, el producto ocupando la mayor parte del cuadro, cuadrada y de 1200 px o más. Las renderizadas ya cumplen.

## 3. Texto

El título (sirve también para Mercado Libre), la descripción corta y dos párrafos de venta. La lista de datos (medidas, material, peso, cuidados, demora y avisos) la arma `producto_tienda.py` desde los informes.

- **Si `generadores_ia.textos` es `"gemini"`:** los escribe el Gemini gratis del usuario en su navegador y Claude los revisa (`references/textos-con-gemini.md` de la skill `impresion-3d`). Avisarlo en una línea antes de abrir Gemini.
- **Si no:** los escribe Claude con las reglas del mismo pedido (`textos_ia.py prompt` las da), en un JSON con `titulo`, `descripcion_corta`, `descripcion` y `palabras_clave`, y pasan por la misma revisión: `textos_ia.py revisar --datos datos_texto.json --respuesta <json> --autor claude --json textos.json`.
- Si Gemini no anda (sin sesión, límite del día, no carga), los escribe Claude y lo dice en una línea.

## 4. Precio

1. Traer `taller-3d/config.json` y correr `costos.py estado --config config.json`. Si falta el consumo de la impresora, buscarlo y guardarlo sin preguntar (`references/costos.md` de la skill `impresion-3d`, «El consumo de la impresora»). Si falta otra cosa para el costo, pedirla de a un dato con su frase (la boleta de luz, el precio de la impresora, el precio del filamento, tu hora, las comisiones del canal) y guardarla con respaldo. Si el usuario prefiere seguir sin eso, seguir: el precio sale con la lista de lo que falta.
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
     --textos textos.json --carpeta <carpeta de la pieza, relativa a la de trabajo> \
     [--fotos-reales ../foto.jpg ../foto-2.jpg] [--plantilla <csv exportado de su plataforma>]
   ```
   Además de la ficha, deja `publicacion.json` y `vista-previa.html`. Si solo hay fotos renderizadas, la descripción aclara que son ilustrativas.
6. **Vista previa:** la página del producto como se vería en su tienda (fotos, título, precio, descripción y ficha técnica) y, abajo, "Antes de publicar": fotos ilustrativas o reales, título para Mercado Libre con sus caracteres, primera foto con fondo blanco, precio y ganancia por canal y quién escribió el texto.
   - **Al costado del chat** (si están las herramientas de páginas de claude.ai): copiar las fotos a `vista-claude/fotos/`, achicadas a 800 px (Pillow, calidad 85), y armar la página:
     ```bash
     python3 -I vista_publicacion.py --publicacion <carpeta>/producto/publicacion.json --modo claude \
       --salida vista-claude/index.html
     ```
     Es siempre la misma página. La primera vez, `publish_files` (título "Vista previa de la publicación", ícono `store`) y después `declare_capabilities` con `{"comments": {}}`; guardar `"vista_previa_claude": {"slug": "…", "url": "…"}` en `config.json`. Las siguientes, `list_files`, `get_artifact` y `publish_files` con `mode: "replace"`. Engancharla a la conversación con `watch`.
   - **En la PC:** escribir `vista-previa.html` y las fotos en `<carpeta>/producto/` (el resto, después de aprobar) y dar el enlace `computer://`. Se abre con doble clic.
   - **Esperar la aprobación:** el botón "Aprobar y cargar como borrador" de la página o un "sí" en el chat. Los pedidos de la página se atienden como los del panel (skill `panel`, "Los pedidos desde el panel"). Con "Cambiar algo…" o un pedido en el chat: cambiar, volver a armar la ficha y la vista previa, y republicarla. Puede aprobar desde la app de Claude en el celular.

## 5. Cargar según la plataforma (`tienda.plataforma`)

- **WooCommerce:**
  1. Si hay herramientas de WordPress/WooCommerce conectadas (por ejemplo, el plugin del adaptador MCP de WordPress), crear el producto con los datos de `producto.json` y estado **borrador**; subir las fotos a la biblioteca de medios y asignarlas.
  2. Si no, usar el navegador: abrir `<url>/wp-admin/post-new.php?post_type=product`, completar nombre, descripción, descripción corta, precio, SKU, peso, medidas, categoría y etiquetas, subir las fotos y **Guardar borrador** (no "Publicar"). Si pide iniciar sesión, que la inicie el usuario.
  3. Si no hay navegador ni conexión, dejar `producto_woocommerce.csv` (ya viene con Publicado = -1, borrador) y explicar: Productos → Importar → elegir el archivo → mapear columnas → Ejecutar; después subir las fotos al producto.
- **Tiendanube, Shopify u otra con importación por CSV:** pedir que exporte su plantilla de productos (en Tiendanube: Productos → Lista de productos → Exportar e importar) y pasarla con `--plantilla`. El script completa una fila respetando los encabezados y deja el producto oculto (Tiendanube: "Mostrar en tienda" = NO). Las fotos se suben aparte. Si el usuario prefiere, cargarlo por el navegador como borrador u oculto.
- **Mercado Libre, Instagram, Facebook u otra:** entregar `ficha.md` con título, descripción, precio, medidas y fotos, lista para copiar. Si quiere, completar el formulario en el navegador hasta antes de publicar y dejar que él confirme.

## 6. Cerrar

1. Dejar en `<carpeta de la pieza>/producto/`: `producto.json`, `producto_woocommerce.csv`, `ficha.md`, `textos.json`, `publicacion.json` y `vista-previa.html` (y `plantilla_completa.csv` si corresponde), más las fotos.
2. Decir dónde quedó el borrador (enlace al producto en el administrador si se creó, y en WooCommerce también su vista previa real, la de "Vista previa" del borrador; y el enlace `computer://` a la carpeta `producto/` de la pieza) y qué falta revisar antes de publicarlo.
3. Actualizar el panel (skill `panel`) con `--producto <carpeta>/producto/producto.json`, la foto principal en `--archivos`, y si hay, el enlace público del producto en `--url-tienda`.
4. Registrar en `historial.csv`.
5. Terminar con una línea "Te toca: …" (revisar el borrador y publicarlo, o imprimir la pieza y sacarle fotos).
