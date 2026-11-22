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
- **Modelos ajenos:** si la pieza sale de un modelo bajado de internet (en el panel, `origen: stl_descargado` con su `fuente` y su `licencia`: partir de eso), preguntar de dónde y revisar su licencia antes de publicar. Si es de uso no comercial (por ejemplo, CC BY-NC) o no tiene licencia clara, avisar que no se puede vender sin permiso del autor y no cargarla. Un personaje, una mascota de marca o un logo ajeno tampoco se vende, aunque la licencia del modelo diga comercial: el personaje o la marca tienen dueño.
- **El margen lo elige el usuario en cada producto** (sección 4). No publicar con el margen habitual sin preguntarle.
- **Se carga después de ver la vista previa** (sección 4, paso 5) y de que el usuario la apruebe.

## 1. Datos de la pieza

1. Ubicar la carpeta de la pieza en `<trabajo>/impresiones/...` y traer `informe_gcode.json`, `pieza.stl` (o su informe) y `vista.png`. Si no hay G-code laminado, ofrecer `/pieza` primero: sin tiempo y gramos no hay costo.
2. Si no hay `informe_stl.json`, generarlo: `revisar_stl.py pieza.stl --material <m> --json informe_stl.json`.
3. Pedir lo que falte: nombre comercial, para qué sirve (una frase), color, categoría, y las fotos reales si ya está impresa (pueden mandarlas desde el celular).

## 2. Fotos

1. **Fotos reales**, si las hay: son la imagen principal.
2. **Fotos de producto renderizadas** (antes de imprimir, o para sumar vistas): cuatro ángulos distintos, cuadradas, sin texto, la primera con fondo blanco puro (lo que pide Mercado Libre). Se hacen con Blender, en la PC si está su conector y si no en el espacio de Claude, con `render_producto.py`: **seguir `references/fotos-de-producto.md` de la skill `impresion-3d`**. Lanzarlas en segundo plano mientras se escribe el texto, y mirarlas antes de mostrarlas (si un ángulo repite otro o no muestra nada, se saca).
3. Si no se puede usar Blender, `vista_previa.py pieza.stl <carpeta>/producto/foto_producto.png --producto --color "<color>"` (más simple, también sin texto).

## 3. Texto

El título (sirve también para Mercado Libre), la descripción corta y dos párrafos de venta. La lista de datos (medidas, material, peso, cuidados, demora y avisos) la arma `producto_tienda.py` desde los informes.

- **Si `generadores_ia.textos` es `"gemini"`:** los escribe el Gemini gratis del usuario en su navegador y Claude los revisa (`references/textos-con-gemini.md` de la skill `impresion-3d`). Avisarlo en una línea antes de abrir Gemini.
- **Si no:** los escribe Claude con las reglas del mismo pedido (`textos_ia.py prompt` las da), en un JSON con `titulo`, `descripcion_corta`, `descripcion` y `palabras_clave`, y pasan por la misma revisión: `textos_ia.py revisar --datos datos_texto.json --respuesta <json> --autor claude --json textos.json`.
- Si Gemini no anda (sin sesión, límite del día, no carga), los escribe Claude y lo dice en una línea.

## 4. Precio

1. Traer `taller-3d/config.json` y pedir todo junto: lo que falta configurar, el costo de la pieza y las opciones de margen.
   ```bash
   python3 -I producto_tienda.py --opciones --config config.json --informe-gcode informe_gcode.json
   ```
   Si falta el consumo de la impresora, buscarlo y guardarlo sin preguntar (`references/costos.md` de la skill `impresion-3d`, «El consumo de la impresora»). Si falta otra cosa (sale con su frase: la boleta de luz, el precio de la impresora, el precio del filamento, tu hora, cómo factura y su Ingresos Brutos, las comisiones del canal), pedirla de a un dato, guardarla con respaldo (`costos.py impuestos` y `costos.py margen` guardan lo suyo) y volver a correrlo. Si el usuario prefiere seguir sin eso, seguir: el precio sale con la lista de lo que falta.
2. **Preguntarle al usuario qué margen quiere en este producto**, con AskUserQuestion: una opción por margen (el más bajo, su habitual marcado "(tu margen habitual)", el más alto), cada una con el precio y la ganancia en su canal principal; con la opción de escribir un precio exacto. Si no hay AskUserQuestion, preguntarlo en una línea con las tres opciones. Con escalones, el habitual es el del escalón de esta pieza (la salida lo dice: «Margen: 60 % (escalón de piezas de hasta 3.000 de costo)»). Si el precio quedó en el mínimo por pieza, decirlo. Los impuestos de la venta (Ingresos Brutos, y el IVA si es responsable inscripto) ya van restados de la ganancia: si es responsable inscripto, el precio es con IVA incluido y el margen es sobre el precio sin IVA.
3. Si eligió un precio exacto, mostrar el margen real que le deja en cada canal (`costos.py pieza … --precio <precio>`). Si en algún canal la ganancia da negativa, decirlo claro antes de seguir.
4. Armar la ficha con lo elegido:
   ```bash
   python3 -I producto_tienda.py --nombre "<nombre>" --material <m> --color "<color>" --uso "<frase>" \
     --categoria "<categoría>" --etiquetas "<a,b>" --informe-gcode informe_gcode.json \
     --informe-stl informe_stl.json --config config.json --salida <carpeta>/producto \
     (--margen <margen elegido> | --precio <precio elegido>) [--canal mercadolibre] \
     --textos textos.json --carpeta <carpeta de la pieza, relativa a la de trabajo> \
     [--fotos-reales ../foto.jpg ../foto-2.jpg] [--csv] [--plantilla <csv exportado de su plataforma>]
   ```
   Deja tres archivos: `publicacion.json` (todo lo de la publicación; el producto para la tienda está en su clave `producto`), `ficha.md` y `vista-previa.html`. Con `--csv`, también el CSV para importar a mano en WooCommerce. Si solo hay fotos renderizadas, la descripción aclara que son ilustrativas.
5. **Vista previa:** la página del producto como se vería en su tienda (fotos, título, precio, descripción y ficha técnica) y, abajo, "Antes de publicar": fotos ilustrativas o reales, título para Mercado Libre con sus caracteres, primera foto con fondo blanco, precio y ganancia por canal y quién escribió el texto.
   - **Al costado del chat** (si están las herramientas de páginas de claude.ai): copiar las fotos a `vista-claude/fotos/`, achicadas a 800 px (Pillow, calidad 85), y armar la página:
     ```bash
     python3 -I vista_publicacion.py --publicacion <carpeta>/producto/publicacion.json --modo claude \
       --salida vista-claude/index.html
     ```
     Es siempre la misma página. La primera vez, `publish_files` (título "Vista previa de la publicación", ícono `store`) y después `declare_capabilities` con `{"comments": {}}`; guardar `"vista_previa_claude": {"slug": "…", "url": "…"}` en `config.json`. Las siguientes, `list_files`, `get_artifact` y `publish_files` con `mode: "replace"`. Engancharla a la conversación con `watch`.
   - **En la PC:** escribir `vista-previa.html` y las fotos en `<carpeta>/producto/` (el resto, después de aprobar) y dar el enlace `computer://`. Se abre con doble clic.
   - **Anotarla en el panel** (skill `panel`): `catalogo.py agregar --carpeta <carpeta de la pieza> --producto <carpeta>/producto/publicacion.json`, con `producto/vista-previa.html` y la foto principal en `--archivos`. Queda en el sector "Publicaciones" como vista previa, aunque todavía no se cargue en la tienda. Rehacer el panel.
   - **Esperar la aprobación:** el botón "Aprobar y cargar como borrador" de la página o un "sí" en el chat. Los pedidos de la página se atienden como los del panel (`references/panel-al-costado.md` de la skill `impresion-3d`, "Los pedidos desde el panel"). Con "Cambiar algo…" o un pedido en el chat: cambiar, volver a armar la ficha y la vista previa, y republicarla. Puede aprobar desde la app de Claude en el celular.

## 5. Cargar según la plataforma (`tienda.plataforma`)

Los datos del producto están en `publicacion.json`, clave `producto`: nombre, SKU, precio, descripciones, categoría, etiquetas, peso y medidas, con `status: draft`.

- **WooCommerce.** Usar el primer camino que esté disponible y decir cuál fue:
  1. **Con el conector de la tienda** (herramientas de WooCommerce o de WordPress en la conversación: las de productos que publica la tienda con el plugin MCP Adapter, u otras que tenga el usuario):
     1. **Buscar antes de crear.** Si la pieza tiene `id_tienda` en `catalogo.json`, es ese producto; si no, buscar por SKU. Si ya existe, **actualizarlo** en vez de crear otro, y decirlo. Si el que existe ya está publicado, no pisarlo sin preguntar: mostrar qué cambiaría (precio, texto) y esperar el OK; su estado no se toca.
     2. **Crear** (o actualizar) con los datos de `producto`, siempre con estado **borrador**.
     3. **Comprobar.** Volver a leer el producto y confirmar que quedó en borrador, con el SKU y el precio pedidos. Si uno nuevo quedó publicado, pasarlo a borrador ahí mismo y avisarlo.
     4. **Fotos.** Si la herramienta acepta imágenes, subirlas en el orden de `fotos` (la principal primero). Si no las acepta, o solo acepta direcciones web, no inventar un camino ni subirlas a otro sitio: dejar el borrador sin fotos y decirle al usuario cuáles subir (están en `producto/`, numeradas en el orden de la galería), o subirlas por el navegador si se puede (camino 2).
     5. **Anotar** el número del producto y su enlace (sección 6, paso 3).
  2. **Con el navegador**, si no hay conector: abrir `<url>/wp-admin/post-new.php?post_type=product` (o el producto que ya existe, buscándolo por SKU en Productos), completar nombre, descripción, descripción corta, precio, SKU, peso, medidas, categoría y etiquetas, subir las fotos si el navegador lo permite y **Guardar borrador** (no "Publicar"). Si pide iniciar sesión, que la inicie el usuario. Anotar el número del producto (está en la dirección: `post=<número>`).
  3. **Con un archivo**, si no hay conector ni navegador: armar la ficha con `--csv` y dejar `producto_woocommerce.csv` (ya viene con Publicado = -1, borrador). Explicar: Productos → Importar → elegir el archivo → mapear columnas → Ejecutar; después subir las fotos al producto.
  - **Si el usuario quiere conectar su tienda:** la tienda tiene que tener el plugin MCP Adapter (la guía es la de WooCommerce: developer.woocommerce.com/docs/features/mcp/) y se entra con una contraseña de aplicación de su usuario de WordPress. Esa contraseña la carga el usuario donde configura el conector: nunca en el chat ni en `config.json`. WooCommerce lo marca como función en prueba y este camino todavía no se probó con una tienda real (0.1.30): la primera vez, cargar un producto de prueba y revisarlo con el usuario antes de confiar en él.
- **Tiendanube, Shopify u otra con importación por CSV:** pedir que exporte su plantilla de productos (en Tiendanube: Productos → Lista de productos → Exportar e importar) y pasarla con `--plantilla`. El script completa una fila respetando los encabezados y deja el producto oculto (Tiendanube: "Mostrar en tienda" = NO). Las fotos se suben aparte. Si el usuario prefiere, cargarlo por el navegador como borrador u oculto.
- **Mercado Libre, Instagram, Facebook u otra:** entregar `ficha.md` con título, descripción, precio, medidas y fotos, lista para copiar. Si quiere, completar el formulario en el navegador hasta antes de publicar y dejar que él confirme.

## 6. Cerrar

1. Dejar en `<carpeta de la pieza>/producto/`: `publicacion.json`, `ficha.md`, `vista-previa.html` y `textos.json` (y `producto_woocommerce.csv` o `plantilla_completa.csv` si se usaron), más las fotos.
2. Decir dónde quedó el borrador (enlace al producto en el administrador si se creó, y en WooCommerce también su vista previa real, la de "Vista previa" del borrador; y el enlace `computer://` a la carpeta `producto/` de la pieza) y qué falta revisar antes de publicarlo: si quedó sin fotos, decirlo primero.
3. Actualizar el panel (skill `panel`): si se cargó en la tienda, `catalogo.py agregar … --id-tienda <número del producto>` (queda como borrador en "Publicaciones", y la próxima vez se actualiza ese producto en vez de crear otro) y el enlace en `--url-tienda`; si no se cargó, queda como vista previa. Cuando el usuario cuente que la publicó, `--estado-publicacion publicada`.
4. Registrar en `historial.csv`.
5. **Ofrecer el reel:** en una línea, si quiere un video para Instagram, TikTok o Shorts de la pieza (skill `video`, sale de lo que ya está en `producto/`). Si dice que sí, seguir con `/taller-3d:video`.
6. Terminar con una línea "Te toca: …" (revisar el borrador y publicarlo, o imprimir la pieza y sacarle fotos).
