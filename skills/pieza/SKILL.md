---
name: pieza
description: Diseña, configura y lamina una pieza de punta a punta, con revisión de seguridad del G-code y presupuesto. Se usa cuando el usuario dice "haceme una pieza", "imprimime", "necesito un soporte, una caja, una tapa o un adaptador", manda una foto, un dibujo o medidas de algo para fabricar, o trae un STL para laminar.
---

# /pieza: de la idea al G-code revisado

Cargar antes la skill `impresion-3d` (reglas de seguridad, rutas y procedimiento de escritura) y seguir sus reglas en todo momento. Scripts: `<raíz del plugin>/skills/impresion-3d/scripts/`. Las referencias (`references/...`) son las de la skill `impresion-3d`.

Usar siempre una lista de tareas con las etapas (Entender la pieza, Modelo, Configuración, Laminar y revisar, Entregar) y tildar cada una al terminarla: es la guía del usuario, que ve en qué etapa está. Mantener informado con frases cortas; las decisiones y resultados van en el informe final. En cada pausa en la que el usuario tiene que hacer algo (contestar, aprobar la vista, imprimir), terminar con una línea **"Te toca: …"** que diga qué y cómo.

**¿Hace falta laminar?** Si el usuario quiere solo el modelo (el STL, el archivo editable, "lo imprimo en otro lado", "un diseño paramétrico") o la PC no está conectada, seguir `/diseno`. Si no queda claro, preguntarlo una sola vez (tabla de `/diseno`).

## 0. Preparación (una vez por conversación)

1. `get_device_info`: verificar que `orca-mcp` esté `announced` y que estén conectadas la carpeta de trabajo y la de perfiles de usuario de Orca (`user/<id>`, que tiene `process`, `filament` y `machine`; o esas carpetas por separado). Si faltan, pedir acceso **una sola vez** con `device_request_folder_access` listando solo esas carpetas (si la carpeta de trabajo no existe, `/instalar`, sección 3). Si el permiso se rechaza, pedir que conecte esas carpetas desde la app de Claude (menú + → Agregar carpeta). Si `orca-mcp` no está, derivar a `/instalar`.
2. Traer `taller-3d/config.json` de la carpeta de trabajo (y `taller-3d/novedades-orca.json` si existe). Si no hay configuración, derivar a `/instalar`.
3. Si `config.json` no tiene `aceptacion`, mostrar el resumen del aviso de uso y pedir ACEPTO (skill `impresion-3d`, regla 8).
4. Ver qué impresoras tiene (`references/impresoras.md`, sección 1, que ve también las impresoras sin copia de usuario). La impresora se elige en cada pieza, en la sección 1, **antes de calcular nada**: si entra, los perfiles, el tiempo y el costo dependen de ella. No se pregunta si el usuario la nombró, si tiene una sola o si para lo que pide sirve una sola (no entra en las otras, o el material pide cerramiento y es la única cerrada): decir en una línea cuál y por qué.
5. Preparar Python: `pip install --break-system-packages -q manifold3d numpy matplotlib`.

## 1. Entender la pieza (cuestionario corto)

Si el pedido no lo dice, preguntar con AskUserQuestion (hasta 4 preguntas juntas; si no está disponible, en texto):

| Pregunta | Opciones |
|---|---|
| ¿En qué impresora? (solo si hay que preguntarla, paso 0.4) | Una por impresora, la recomendada primero con "(Recomendada)": la que mejor encaja por tamaño y material; si da igual, la última usada (`impresora_por_defecto`). En la descripción: tamaño de la cama, si es cerrada y "ya preparada" o "hay que prepararla (unos minutos, solo la primera vez)" |
| ¿Para qué es? | Funcional (soporta esfuerzo) · Se ve (estética) · Encastre o mecanismo · Prototipo rápido |
| ¿Dónde va a estar? | Interior · Al sol o al aire libre · Cerca de calor (auto, motor, más de 50 °C) · Con agua o humedad |
| ¿Material? | Los filamentos de la configuración del usuario + "Otro" |
| ¿Qué priorizás? | Calidad · Resistencia · Velocidad · Ahorro de material |

Si con la impresora son más de 4 preguntas, la impresora va en la primera tanda. Además, en texto: medidas críticas (con calibre si es un encastre), cantidad, color y fecha si la hay. **No inventar medidas:** si falta una que importa, preguntarla. Si manda una foto, usarla para la forma y pedir las medidas que la foto no da.

Si el pedido es una idea anotada en el panel, partir de su nota (medidas, uso, material) y preguntar solo lo que falte. Si el usuario lo deja para otro momento, ofrecer anotarlo como idea (skill `panel`).

**Con la impresora elegida**, antes de modelar: si se preguntó, avisar en una línea que elegirla en la ventana de Orca no le llega a Claude. Si no tiene copia de usuario, ofrecer crearla. Si todavía no está preparada en el taller, prepararla con `/impresoras` (se investiga en internet y se configura óptima). Si le falta el consumo, buscarlo y guardarlo sin preguntar (`references/costos.md`, «El consumo de la impresora»). Traer su JSON (`datos`, en `taller-3d/impresoras/`) con `device_stage_files`: es el `--impresora` de los scripts. Si eligió una distinta de `impresora_por_defecto`, al registrar la entrega dejarla como `impresora_por_defecto` (la última usada aparece primera la próxima vez).

Con las respuestas, decidir y anotar: material (si va al sol o al calor, nunca PLA), receta (`references/recetas.md`), orientación y si es un uso crítico (regla 9). Si las respuestas no cierran con la impresora elegida (un ABS en una abierta, medidas que no entran), avisarlo antes de modelar y sugerir otra suya donde sí (Revisar, paso 1).

## 2. Modelo

Nombre de la carpeta y de los archivos: `python3 -I catalogo.py carpeta --nombre "<nombre de la pieza>" --impresora "<nombre de la impresora en config.json>"` devuelve `carpeta` (`impresiones/AAAA-MM-DD_nombre_impresora`) y `archivo` (`nombre_impresora`, para el G-code y el proyecto de Orca). La impresora va en el nombre porque un G-code solo sirve para la impresora para la que se laminó. Crear `/mnt/user-data/outputs/taller-3d/<carpeta>/`. Si después cambia de impresora (por ejemplo, porque no entra), sacar el nombre de nuevo con la otra antes de escribir en la PC.

**Con qué modelar** (`references/modelado.md`): se decide antes de modelar, por cómo se describe la pieza y no por comodidad. Nunca aproximar con formas simples algo que se define por su aspecto.

- **Se describe con medidas** (funcional o geométrica): escribir `pieza.py` con `cad.py` según la plantilla de `references/cad.md` (parámetros arriba, medidas del usuario, holguras de `holgura()` o de `aprendizajes.md` si hay calibración propia). Correrlo para generar `pieza.stl`.
- **Se describe por cómo se ve** (figura, forma suave, logo, texto): Blender por código (`modelo.py`) o un modelo que ya exista. Si es algo conocido, antes ver si ya existe y ofrecerlo con su licencia. Personajes y marcas ajenas no se modelan. Si el usuario trae un STL, traerlo con `device_stage_files`.
- **Las dos cosas:** cada parte con su herramienta, unidas en `pieza.py` con `importar_stl` y `unir`.
- **Objeto que resuelve un plugin de Orca** (llavero, cartel o placa con nombre, florero, caja Gridfinity, litofanía, texturas): antes de modelar, buscar en el Plugin Hub (`references/plugins-orca.md`) y, si hay uno que sirva, ofrecerlo junto con la opción de hacerlo acá. Si lo usa, el STL que genere sigue desde la revisión de abajo.
- **Pieza muy grande para la impresora elegida:** primero ver si entra en otra de sus impresoras (Revisar, paso 1); si no, partirla con encastres o tornillos.

Revisar:
1. `revisar_stl.py pieza.stl --impresora <json> --otras <carpeta taller-3d/impresoras traída> --material <m> --esperado <AxBxC>` (y `--rotar/--apoyar/--centrar --salida` si hay que orientarla). RECHAZADO → corregir el modelo.
   - **No entra en la impresora elegida:** el informe dice en cuál de sus otras impresoras preparadas entra (`entra_en_otras`). Si tiene otras en Orca sin preparar, buscar su volumen de impresión oficial en internet. Si alguna entra, sugerírsela ("No entra en la X, pero sí en tu Y. ¿La hacemos ahí?"); si la elige, prepararla con `/impresoras` si hace falta y seguir con esa. Si ninguna entra, ofrecer partirla con encastres o escalarla.
2. `vista_previa.py pieza.stl vista.png --titulo "<nombre>"`. Si la pieza es decorativa o mixta, sumar la foto renderizada (`references/modelado.md`, «Revisar y mostrar»). Mirarlas antes de mostrarlas: si no se reconoce lo pedido o falta algo, corregir o cambiar de herramienta. **Mostrar la vista** (y la foto) al usuario con SendUserFile y decir qué es aproximado. Si es un diseño nuevo, esperar su OK antes de seguir; si es un STL que trajo, seguir.

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

1. Escribir `pieza.stl` (y `pieza.py`, `vista.png`) en `<trabajo>/<carpeta>/` con `device_commit_files`.
2. `slice_model` con la ruta del STL en la PC, `machine_profile` = `perfil_maquina`, `process_profile` = el AUTO proceso, `filament_profile` = el AUTO filamento, `output_dir` = `<trabajo>/<carpeta>/laminado` (Orca deja ahí una subcarpeta por vuelta con `plate_1.gcode`: son borradores).
3. `get_slice_estimates` (tiempo, gramos) y, si hay voladizos o zonas críticas, `analyze_gcode_layers` en ese rango de Z.
4. Traer el G-code con `device_stage_files` y correr:
   ```bash
   python3 -I revisar_gcode.py <gcode> --impresora <datos> --material <m> --json informe_gcode.json \
     --cama-primera-capa <temperatura anotada> --config <config.json>
   ```
5. Verificar en el informe: temperaturas (la cama de la primera capa tiene que coincidir), ventilador, zona impresa, tiempo y gramos razonables para el volumen. Correr también `novedades_orca.py gcode <gcode> --estado <novedades-orca.json>` (skill `impresion-3d`, sección 7) y guardar el estado actualizado en la PC; si hay novedades, contarlas en una línea.
6. Si algo no cierra (tiempo excesivo para la prioridad, voladizos sin soporte, cama equivocada, advertencias), ajustar los perfiles (sección 3), la orientación o el modelo (sección 2) y volver a laminar. Máximo 3 vueltas sin consultar; si no converge, explicar el dilema y preguntar.
7. **RECHAZADO = no se entrega.**

## 5. Entregar

1. **G-code con nombre:** copiar el G-code aprobado (el que se trajo para revisarlo) a `/mnt/user-data/outputs/taller-3d/<carpeta>/<archivo>.gcode` y escribirlo en `<trabajo>/<carpeta>/` con `device_commit_files` (`stagedPath`). Es el que se imprime: el nombre dice para qué impresora es, también en la pantalla de la impresora.
2. **Proyecto de Orca**, para ver o tocar la pieza en la ventana de Orca:
   ```bash
   python3 -I proyecto_3mf.py --stl pieza.stl --gcode <G-code aprobado> --cama "<cama de la impresora en config.json>" \
     --nombre "<nombre de la pieza>" --salida /mnt/user-data/outputs/taller-3d/<carpeta>/<archivo>.3mf --json informe_3mf.json
   ```
   Lleva el modelo en el centro de la cama, los nombres y valores de los perfiles con que se laminó (la copia de la máquina, el AUTO proceso y el AUTO filamento) y la cama real (por línea de comandos Orca usa Cool Plate). Escribirlo con `device_commit_files` (`stagedPath`). Si el script avisa algo, contarlo en una línea; si no lo puede armar (sale 2), entregar sin proyecto y decir que abra `pieza.stl` en Orca y elija los perfiles AUTO.
3. Dejar también en la carpeta: `pieza.py` (si se modeló), `modelo.py` y las partes de Blender (si las hay), `pieza.stl`, `vista.png`, `config_usada.json`, `informe_gcode.json` e `informe.md`. En `laminado/` quedan las vueltas de Orca: se pueden borrar.

`informe.md` y la respuesta al usuario (breve):
- El G-code a imprimir (`<archivo>.gcode`) y su carpeta, con enlaces `computer://` a la carpeta y al `.3mf` (skill `impresion-3d`, sección 3).
- Tiempo, gramos y costo real con sus partes (material, luz, desgaste de la impresora, fallas, tu tiempo, embalaje; sale en `informe_gcode.json`, `references/costos.md`). Si faltan datos, decir cuáles en una línea con su frase de `costos.py estado` ("Te paso mi boleta de luz…"); el costo sale igual con lo que hay.
- 3 a 6 decisiones clave con el porqué (material, orientación, paredes/relleno, costura, soportes, cama).
- Resultado de la revisión de seguridad (APROBADO o advertencias explicadas).
- Qué mirar durante la impresión (primera capa, voladizos en tal altura) y el recordatorio de no dejarla sin supervisión.
- Cómo imprimir: pasar `<archivo>.gcode` por USB o por la app de la impresora y arrancar desde la impresora. **No arrancarla nunca desde acá.**
- Para verla o tocarla en Orca: tocar el enlace del `<archivo>.3mf` o abrirlo con doble clic; se abre con la impresora, el filamento, el proceso y la cama elegidos. Si Orca ya estaba abierto desde antes de que se crearan los perfiles AUTO, cerrarlo primero: si no, los muestra como cambios sobre el perfil de sistema (con los mismos valores).

**Abrir Orca con la pieza** (opcional): preguntar "¿Te abro Orca con la pieza?" (si el usuario ya lo pidió, por ejemplo con el botón del panel, no preguntar). Si dice que sí:
- **Con `taller3d-orca`** (`get_device_info` lo muestra `announced`): llamar `abrir_en_orca` con la ruta del `.3mf` relativa a la carpeta de trabajo (`<carpeta>/<archivo>.3mf`). Contesta si la abrió o por qué no (y no abre dos veces la misma en pocos segundos).
- **Si no está, con `device_bash`**, lanzarlo en segundo plano con el proyecto, con `orca.ejecutable` de `config.json`:
- Linux, solo con sesión gráfica (`[ -n "$DISPLAY$WAYLAND_DISPLAY" ]`): `nohup "<ejecutable>" "<ruta del .3mf>" >/dev/null 2>&1 &` (Flatpak: `nohup flatpak run com.orcaslicer.OrcaSlicer "<ruta del .3mf>" >/dev/null 2>&1 &`).
- Windows (PowerShell): `Start-Process -FilePath "<ejecutable>" -ArgumentList '"<ruta del .3mf>"'`.
- macOS: `open -a OrcaSlicer "<ruta del .3mf>"`.

Si no se puede (sin `taller3d-orca`, sin sesión gráfica, sin ejecutable o sin `device_bash`), decir en una línea: "Tocá el enlace o abrí `<archivo>.3mf` con doble clic", con el enlace `computer://` al archivo, y una vez por conversación que corriendo de nuevo el instalador del taller (Linux) Claude y el panel pueden abrir Orca solos. Abrir la ventana está bien; imprimir es del usuario (skill `impresion-3d`, regla 1): nunca usar la pestaña Dispositivo (Device) de Orca ni sus botones Imprimir o Enviar, tampoco con el control del escritorio.

Registrar la entrega en `historial.csv` y actualizar el panel (skill `panel`, "Agregar o actualizar una pieza"; con `--de-idea` si salió de una idea anotada) con `--impresora "<nombre de la impresora>"`, `informe_gcode.json`, `informe_stl.json` y los archivos de la carpeta (`<archivo>.gcode`, `<archivo>.3mf`, `pieza.stl`, `pieza.py`, `vista.png`, `informe.md`).

### En paralelo: la publicación

Si `config.json` tiene `tienda.plataforma` y la pieza es para vender (o el usuario lo pidió), ofrecer en la misma respuesta: "¿Te armo ya la publicación? Queda en borrador con fotos de producto renderizadas hasta que tengas las reales." Si dice que sí, seguir `/publicar` con los datos de este laminado (tiempo y gramos reales); ahí se elige el margen de este producto. El usuario puede aprobar desde la app de Claude en el celular; nada se publica sin su OK.

Cerrar la entrega con **"Te toca: imprimir `<archivo>.gcode`** (pasalo a la impresora y arrancala desde ahí) **y después contame cómo salió"**. Si hay AskUserQuestion, ofrecer además las opciones que siguen: "Ya la imprimí", "Abrila en Orca" (si hay `device_bash`), "Armá la publicación" (si hay tienda) y "Cambiar algo".

## 6. Después de imprimir (aprendizaje)

Si el usuario cuenta cómo salió o manda una foto:
1. Diagnosticar con `references/diagnostico.md`.
2. Anotar en `taller-3d/aprendizajes.md`: fecha, pieza, perfil, material, resultado, problema y ajuste que funcionó (por ejemplo, la holgura real de un encastre).
3. Si el ajuste sirve para todo el material, proponer llevarlo al perfil con `/calibrar` o al AUTO de la próxima pieza.
4. Marcarla como impresa en el panel (`--estado impresa`); si mandó una foto, guardarla como `foto.jpg` en la carpeta de la pieza y sumarla.
5. Si quiere venderla, ofrecer `/publicar`.
