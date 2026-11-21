---
name: pieza
description: Diseña, configura y lamina una pieza de punta a punta, con revisión de seguridad del G-code y presupuesto. Se usa cuando el usuario dice "haceme una pieza", "imprimime", "necesito un soporte, una caja, una tapa o un adaptador", manda una foto, un dibujo o medidas de algo para fabricar, o trae un STL para laminar.
---

# /pieza: de la idea al G-code revisado

Cargar antes la skill `impresion-3d` (reglas de seguridad, rutas y procedimiento de escritura) y seguir sus reglas en todo momento. Scripts: `<raíz del plugin>/skills/impresion-3d/scripts/`. Las referencias (`references/...`) son las de la skill `impresion-3d`.

Usar una lista de tareas si la pieza lleva modelado. Mantener informado con frases cortas; las decisiones y resultados van en el informe final.

**¿Hace falta laminar?** Si el usuario quiere solo el modelo (el STL, el archivo editable, "lo imprimo en otro lado", "un diseño paramétrico") o la PC no está conectada, seguir `/diseno`. Si no queda claro, preguntarlo una sola vez (tabla de `/diseno`).

## 0. Preparación (una vez por conversación)

1. `get_device_info`: verificar que `orca-mcp` esté `announced` y que estén conectadas la carpeta de trabajo y las de perfiles de Orca (`process`, `filament` y `machine`). Si faltan, pedir acceso **una sola vez** con `device_request_folder_access` listando solo esas carpetas. Si el permiso se rechaza, pedir que conecte esas carpetas desde la app de Claude (menú + → Agregar carpeta). Si `orca-mcp` no está, derivar a `/instalar`.
2. Traer `taller-3d/config.json` de la carpeta de trabajo (y `taller-3d/novedades-orca.json` si existe). Si no hay configuración, derivar a `/instalar`.
3. Si `config.json` no tiene `aceptacion`, mostrar el resumen del aviso de uso y pedir ACEPTO (skill `impresion-3d`, regla 8).
4. Elegir la impresora (`references/impresoras.md`, sección 1, que ve también las impresoras sin copia de usuario): la que diga el usuario; si no dice y en Orca hay varias, preguntar en cuál quiere trabajar (primero la elegida en Orca o la última usada), avisando que elegirla en la ventana de Orca no le llega a Claude. Si la elegida no tiene copia de usuario, ofrecer crearla. Si esa impresora todavía no está preparada en el taller, prepararla con `/impresoras` (se investiga en internet y se configura óptima) antes de seguir. Traer su JSON (`datos`, en `taller-3d/impresoras/`) con `device_stage_files`: es el `--impresora` de los scripts. Si eligió una distinta de `impresora_por_defecto`, al registrar la entrega dejarla como `impresora_por_defecto` (la última usada aparece primera la próxima vez).
5. Preparar Python: `pip install --break-system-packages -q manifold3d numpy matplotlib`.

## 1. Entender la pieza (cuestionario corto)

Si el pedido no lo dice, preguntar con AskUserQuestion (hasta 4 preguntas juntas; si no está disponible, en texto):

| Pregunta | Opciones |
|---|---|
| ¿Para qué es? | Funcional (soporta esfuerzo) · Se ve (estética) · Encastre o mecanismo · Prototipo rápido |
| ¿Dónde va a estar? | Interior · Al sol o al aire libre · Cerca de calor (auto, motor, más de 50 °C) · Con agua o humedad |
| ¿Material? | Los filamentos de la configuración del usuario + "Otro" |
| ¿Qué priorizás? | Calidad · Resistencia · Velocidad · Ahorro de material |

Además, en texto: medidas críticas (con calibre si es un encastre), cantidad, color y fecha si la hay. **No inventar medidas:** si falta una que importa, preguntarla. Si manda una foto, usarla para la forma y pedir las medidas que la foto no da.

Con las respuestas, decidir y anotar: material (si va al sol o al calor, nunca PLA), receta (`references/recetas.md`), orientación y si es un uso crítico (regla 9). Si las medidas ya muestran que no entra en la impresora elegida, avisarlo antes de modelar y sugerir otra suya donde entre (Revisar, paso 1).

## 2. Modelo

Crear la carpeta de la pieza en el contenedor: `/mnt/user-data/outputs/taller-3d/impresiones/AAAA-MM-DD_nombre/`.

- **Pieza funcional o geométrica:** escribir `pieza.py` con `cad.py` según la plantilla de `references/cad.md` (parámetros arriba, medidas del usuario, holguras de `holgura()` o de `aprendizajes.md` si hay calibración propia). Correrlo para generar `pieza.stl`.
- **Forma orgánica, decorativa o con texto:** Blender (MCP) o un modelo que traiga el usuario. Si trae un STL, traerlo con `device_stage_files`.
- **Objeto que resuelve un plugin de Orca** (llavero, cartel o placa con nombre, florero, caja Gridfinity, litofanía, texturas): antes de modelar, buscar en el Plugin Hub (`references/plugins-orca.md`) y, si hay uno que sirva, ofrecerlo junto con la opción de hacerlo acá. Si lo usa, el STL que genere sigue desde la revisión de abajo.
- **Pieza muy grande para la impresora elegida:** primero ver si entra en otra de sus impresoras (Revisar, paso 1); si no, partirla con encastres o tornillos.

Revisar:
1. `revisar_stl.py pieza.stl --impresora <json> --otras <carpeta taller-3d/impresoras traída> --material <m> --esperado <AxBxC>` (y `--rotar/--apoyar/--centrar --salida` si hay que orientarla). RECHAZADO → corregir el modelo.
   - **No entra en la impresora elegida:** el informe dice en cuál de sus otras impresoras preparadas entra (`entra_en_otras`). Si tiene otras en Orca sin preparar, buscar su volumen de impresión oficial en internet. Si alguna entra, sugerírsela ("No entra en la X, pero sí en tu Y. ¿La hacemos ahí?"); si la elige, prepararla con `/impresoras` si hace falta y seguir con esa. Si ninguna entra, ofrecer partirla con encastres o escalarla.
2. `vista_previa.py pieza.stl vista.png --titulo "<nombre>"` y **mostrar la vista** al usuario (SendUserFile). Si es un diseño nuevo, esperar su OK antes de seguir; si es un STL que trajo, seguir.

## 3. Configuración

1. Base: perfil de proceso del usuario que mejor encaje (o el de sistema de la impresora según la prioridad) y el perfil de filamento del material.
2. Armar `AUTO proceso @<impresora>` con la base y la receta:
   ```bash
   python3 -I perfil_orca.py crear --tipo proceso --nombre "<proceso_auto>" --hereda "<perfil de sistema>" \
     --base "<proceso base traído>" --set clave=valor ... --anterior "<AUTO actual traído>" \
     --config <config.json> --impresora <datos> --material <m> \
     --salida /mnt/user-data/outputs/taller-3d/perfiles
   ```
   Armar **siempre** `AUTO filamento @<impresora>` a partir del filamento del usuario, con `--cama "<cama de la configuración>"` (por línea de comandos Orca usa las temperaturas de "Cool Plate"; `--cama` copia ahí las de la cama real) y, si hace falta, cambios del caso (por ejemplo, ventilador para puentes):
   ```bash
   python3 -I perfil_orca.py crear --tipo filamento --nombre "<filamento_auto>" --hereda "<inherits del filamento>" \
     --base "<filamento del usuario traído>" --cama "<cama>" [--set clave=valor ...] \
     --anterior "<AUTO filamento actual traído>" --config <config.json> --impresora <datos> --material <m> \
     --salida /mnt/user-data/outputs/taller-3d/perfiles
   ```
   Anotar la temperatura de cama de la primera capa que informa el script. Nunca modificar el perfil del filamento del usuario desde `/pieza`.
3. Escribir los perfiles en la PC con el procedimiento de escritura (respaldo del AUTO anterior, `expectedMtimeMs`).
4. Guardar `config_usada.json` en la carpeta de la pieza: perfiles, anulaciones y motivo de cada una.

## 4. Laminar y revisar (bucle)

1. Escribir `pieza.stl` (y `pieza.py`, `vista.png`) en `<trabajo>/impresiones/AAAA-MM-DD_nombre/` con `device_commit_files`.
2. `slice_model` con la ruta del STL en la PC, `machine_profile` = `perfil_maquina`, `process_profile` = el AUTO proceso, `filament_profile` = el AUTO filamento, `output_dir` = la carpeta de la pieza en la PC.
3. `get_slice_estimates` (tiempo, gramos) y, si hay voladizos o zonas críticas, `analyze_gcode_layers` en ese rango de Z.
4. Traer el G-code con `device_stage_files` y correr:
   ```bash
   python3 -I revisar_gcode.py <gcode> --impresora <datos> --material <m> --json informe_gcode.json \
     --cama-primera-capa <temperatura anotada> [--precio-kg <costos> --precio-kwh <costos> --watts <consumo_w>]
   ```
5. Verificar en el informe: temperaturas (la cama de la primera capa tiene que coincidir), ventilador, zona impresa, tiempo y gramos razonables para el volumen. Correr también `novedades_orca.py gcode <gcode> --estado <novedades-orca.json>` (skill `impresion-3d`, sección 7) y guardar el estado actualizado en la PC; si hay novedades, contarlas en una línea.
6. Si algo no cierra (tiempo excesivo para la prioridad, voladizos sin soporte, cama equivocada, advertencias), ajustar los perfiles (sección 3), la orientación o el modelo (sección 2) y volver a laminar. Máximo 3 vueltas sin consultar; si no converge, explicar el dilema y preguntar.
7. **RECHAZADO = no se entrega.**

## 5. Entregar

En la carpeta de la pieza en la PC dejar: `pieza.py` (si se modeló), `pieza.stl`, `vista.png`, el G-code, `config_usada.json`, `informe_gcode.json` e `informe.md`.

`informe.md` y la respuesta al usuario (breve):
- Ruta del G-code.
- Tiempo, gramos y costo (si hay precios en la configuración; si faltan, ofrecer cargarlos).
- 3 a 6 decisiones clave con el porqué (material, orientación, paredes/relleno, costura, soportes, cama).
- Resultado de la revisión de seguridad (APROBADO o advertencias explicadas).
- Qué mirar durante la impresión (primera capa, voladizos en tal altura) y el recordatorio de no dejarla sin supervisión.
- Cómo imprimir: pasar el G-code por USB o por la app de la impresora y arrancar desde la impresora. También puede abrir `pieza.stl` en Orca y elegir los perfiles `AUTO`: quedan configurados igual. **No arrancarla nunca desde acá.**

Registrar la entrega en `historial.csv` y actualizar el catálogo (skill `catalogo`, "Agregar o actualizar una pieza") con `informe_gcode.json`, `informe_stl.json` y los archivos de la carpeta.

### En paralelo: la publicación

Si `config.json` tiene `tienda.plataforma` y la pieza es para vender (o el usuario lo pidió), ofrecer en la misma respuesta: "¿Te armo ya la publicación? Queda en borrador con una imagen ilustrativa hasta que tengas la foto real." Si dice que sí, seguir `/publicar` con los datos de este laminado (tiempo y gramos reales). El usuario puede aprobar desde la app de Claude en el celular; nada se publica sin su OK.

## 6. Después de imprimir (aprendizaje)

Si el usuario cuenta cómo salió o manda una foto:
1. Diagnosticar con `references/diagnostico.md`.
2. Anotar en `taller-3d/aprendizajes.md`: fecha, pieza, perfil, material, resultado, problema y ajuste que funcionó (por ejemplo, la holgura real de un encastre).
3. Si el ajuste sirve para todo el material, proponer llevarlo al perfil con `/calibrar` o al AUTO de la próxima pieza.
4. Marcarla como impresa en el catálogo (`--estado impresa`); si mandó una foto, guardarla como `foto.jpg` en la carpeta de la pieza y sumarla.
5. Si quiere venderla, ofrecer `/publicar`.
