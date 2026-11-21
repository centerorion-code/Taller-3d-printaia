# Plugins de OrcaSlicer (2.5 o más nuevo)

Desde la versión 2.5, Orca acepta plugins escritos en Python (corren dentro de Orca, que trae su propio Python). Se consiguen en el **Plugin Hub** de Orca Cloud (cloud.orcaslicer.com → Plugins → Plugin Hub) o como archivo `.py`/`.whl` que da el autor.

## Lo que hay que saber antes de sugerir uno

- **No hay plugins "oficiales" de Orca.** El Plugin Hub es de la comunidad; al publicar pasan una revisión automática, sin revisión manual. Algunos son del equipo de Orca (por ejemplo, los de muestra de SoftFever) y hay fabricantes con cuenta verificada, pero eso no garantiza que el código sea seguro.
- **Hay listados duplicados o de terceros** con el mismo nombre (pasó con Support Fins). Preferir el listado que enlaza el autor desde su propio sitio o repositorio.
- Un plugin puede leer archivos y modificar el laminado o el G-code. Orca pide permiso antes de que salga de su carpeta de datos, use internet o abra otros programas.
- Tipos: **Script** (acción con botón o en Speed Dial: generadores, herramientas), **Slicing Pipeline** (corre durante el laminado y puede cambiar capas o G-code; se elige en Proceso → Otros → Plugin de la canalización de laminado, en modo Avanzado), **Página** (pestaña propia), **Agente de impresora** (conexión con impresoras) y **Texturas** (mapas para la herramienta Texture Displacement).
- Se instalan en `<datos de Orca>/orca_plugins/` (los del Hub, en `orca_plugins/_subscribed/<usuario>/`).

## Reglas del taller

1. **Sugerir, nunca instalar.** Claude no instala, activa ni configura plugins. Explica cuál, para qué, de quién es y cómo instalarlo; decide el usuario.
2. **Perfiles AUTO sin plugins ni scripts.** `perfil_orca.py` quita `post_process`, `plugins` y `slicing_pipeline_plugin` al copiar un perfil base y rechaza pedirlos con `--set`: Orca los ejecuta al laminar. Si el usuario quiere un plugin de laminado, lo elige él en Orca con sus perfiles y lamina desde Orca.
3. **Lo que sale de un plugin sigue el circuito normal.** Si un generador crea un STL (llavero, cartel, florero), traerlo con `device_stage_files` y seguir `/pieza` desde la revisión del STL: `revisar_stl.py`, perfiles AUTO, laminado, `revisar_gcode.py` y, si va a la tienda, `/publicar`.
4. **Agentes de impresora:** nunca usarlos para mandar o arrancar impresiones (regla 1 de seguridad).
5. **Modelos bajados con un plugin** (por ejemplo, de Printables o MakerWorld): revisar la licencia antes de venderlos, como en `/publicar`.
6. **Plugins que usan servicios pagos o cuentas** (IA, inventario en la nube): decir que necesitan cuenta, que los datos salen de la PC y si tienen costo.

## Cómo buscar (en el momento del pedido)

Cuando el pedido es un tipo de objeto o una función que un plugin podría resolver (llavero, cartel o placa con nombre, florero, caja organizadora o Gridfinity, litofanía, textura decorativa, soportes especiales, buscar un modelo ya hecho):

1. Buscar en la web con `allowed_domains: ["cloud.orcaslicer.com"]` y palabras en inglés (los listados están casi todos en inglés): por ejemplo `keychain`, `name tag`, `name sign`, `vase`, `gridfinity`, `lithophane`, `texture`, `support`.
2. Abrir el listado (`cloud.orcaslicer.com/p/<id>`) y anotar: autor, versión y fecha, tipo, sistemas operativos, versión mínima de Orca, permisos que pide, si necesita cuenta o pago, y los últimos comentarios (si dicen que no anda, decirlo).
3. Comparar con hacerlo con el taller (`cad.py` o Blender). Sugerir el plugin solo si ahorra trabajo o da un resultado mejor, en dos o tres líneas, con la alternativa propia.
4. Cómo se instala (para explicárselo al usuario): iniciar sesión en Orca Cloud dentro de Orca (botón de cuenta arriba a la derecha), Suscribirse en el listado, en Orca abrir Archivo → Plugins → Actualizar, tildar Activar y aceptar los permisos que pida si está de acuerdo. Un plugin de laminado además hay que agregarlo en el perfil de proceso (Otros → Plugin de la canalización de laminado).

## Plugins que vale la pena conocer (revisado el 21/11/2026)

Verificar el listado antes de sugerirlo: cambian rápido.

| Plugin | Tipo | Sirve para | Ojo |
|---|---|---|---|
| PrintPal | Script, todos los sistemas | Generadores de floreros, cajas y grillas Gridfinity, placas y carteles con nombre, con vista previa; además búsqueda de modelos y generación por IA | La generación por IA usa un servicio externo |
| Vase Maker | Script | Floreros paramétricos | En Linux y macOS guarda el STL y se importa a mano |
| ModelFinder | Script | Buscar y bajar modelos de Printables, MakerWorld y Thingiverse desde Orca | Revisar la licencia antes de vender; pide permiso por cada sitio |
| Support Fins (listado del autor, 1.0.11 o más nuevo) | Slicing Pipeline | Aletas de soporte que se sacan fácil en voladizos | Hay copias de terceros; instala numpy y mini-racer; va en el perfil de proceso |
| Packs de texturas (por ejemplo, FHSL Hard Surface) | Texturas | Mapas para Texture Displacement: terminaciones decorativas | Solo decoración |
| Filament Saver | Script | Sugiere ajustes según el uso con el motivo de cada uno | Se superpone con las recetas del taller |
| FilamentHub | Script | Base de filamentos, stock de bobinas y costos | Necesita cuenta de FilamentHub |
| Meshy for OrcaSlicer | Página | Modelos por IA desde texto o imagen | Solo Windows y macOS; servicio pago; revisar los términos para vender |
| Muestras de SoftFever | Slicing Pipeline | Torcer, afinar u ondular un modelo al laminar; textura difusa en el contorno | Experimental |
