# Seguridad de taller-3d

## Principios

1. **Nunca arranca una impresión.** El plugin no usa herramientas de control de impresoras y entrega el G-code para que la persona lo imprima. Un bloqueo automático impide además mandar comandos de impresión por red (Moonraker, OctoPrint) desde la terminal.
2. **Revisión de seguridad de cada G-code** (`revisar_gcode.py`) antes de entregarlo:
   - temperaturas de boquilla y cama contra el máximo de la impresora y el rango del material;
   - movimientos fuera del área de impresión y Z negativa;
   - comandos que cambian o dañan la configuración del firmware (M500, M502, M997, M303, M301, M304, M149, M92, M906, M302, M211 S0, SAVE_CONFIG, FIRMWARE_RESTART, SET_KINEMATIC_POSITION, FORCE_MOVE, RUN_SHELL_COMMAND, etc.), G92 Z (cambia dónde cree la impresora que está la boquilla) y caudal M221 por encima del 200 %;
   - las líneas se leen como las lee el firmware: con número de línea y suma de control (`N10 M104 S400*45`), con los parámetros pegados (`M104S400`) o con letras repetidas (se toma el valor más alto);
   - variables del slicer sin reemplazar, unidades en pulgadas, extrusión antes de calentar;
   - que apague los calentadores al terminar.
   Si sale RECHAZADO, no se entrega, y un bloqueo automático impide escribirlo en la PC.
3. **Perfiles validados** (`perfil_orca.py`): cada clave existe en Orca 2.5.1, va en el tipo de perfil correcto, tiene un valor válido y respeta los límites de temperatura (también las de espera, purga y torre). El G-code que va adentro del perfil (inicio, fin, cambio de capa o de filamento) pasa por la misma revisión que el G-code laminado. Si hay un rechazo, no se escribe nada; el bloqueo automático lo verifica otra vez antes de escribir en la PC. Los perfiles que escribe Claude no pueden llevar scripts de posprocesado ni plugins de Orca (`post_process`, `plugins`, `slicing_pipeline_plugin`), porque Orca los ejecuta al laminar.
4. **Mínimo acceso:** solo escribe en las carpetas que el usuario conecta (perfiles de usuario de Orca y carpeta de trabajo, que el usuario elige al instalar). Nunca toca los perfiles de sistema de Orca, los que vienen con el programa, sus plugins (`orca_plugins`) ni su configuración (`OrcaSlicer.conf`): también está bloqueado.
5. **Reversible:** respaldo antes de cada cambio, historial de acciones y `/restaurar`. La conexión con la PC no puede borrar archivos; el desinstalador manda todo a la papelera.
6. **Privacidad:** sin telemetría. No sube modelos, G-code ni perfiles a internet (bloqueado desde la terminal). La única salida es la publicación de un producto en la tienda del propio usuario, a su pedido y como borrador. No guarda contraseñas.
7. **Instaladores verificables:** OrcaSlicer 2.5.1 y uv 0.13.9 (Windows) se bajan de sus publicaciones oficiales en GitHub y se comparan con una huella SHA-256 fija antes de usarlos; en Windows también se verifica la firma digital del instalador de Orca (ORCASLICER PTE. LTD.). orca-mcp 0.1.0 se instala desde PyPI con uv o pipx en versión fija, sin huella propia: ahí se confía en PyPI, y sus dependencias toman la última versión compatible. Modo prueba; sin `curl | sh`; `sudo` o permisos de administrador solo con consentimiento; registro de lo instalado y desinstalador que solo quita lo anotado (y nada fuera de tu carpeta personal). Usan lo que ya está instalado en lugar de reemplazarlo.
8. **Plugins de Orca:** el taller solo los sugiere; nunca los instala ni los activa. No hay plugins "oficiales": son de la comunidad, con una revisión automática, y pueden leer archivos y cambiar el laminado.
9. **Un solo origen:** el taller se distribuye desde https://github.com/noamix/Taller-3d-printaia. Sus bloqueos automáticos corren en tu PC, así que instalalo solo desde ahí: una copia (fork) o un archivo `.plugin` que te pasen pueden traer cambios que nadie revisó.

## Bloqueos automáticos (hooks)

`hooks/guardia.py` corre:

- **Antes de escribir en la PC** (`device_commit_files`, y `Write`/`Edit`/`MultiEdit` en Claude Code): revisa los G-code (`.gcode`, `.gco`, `.g`, `.gc`), los proyectos `.3mf` y `.gcode.3mf` (G-code de adentro, scripts y temperaturas de sus ajustes) y los perfiles de usuario de Orca. Rechaza el G-code binario (`.bgcode`), que no puede leer. Estos archivos tienen que ir con `stagedPath`: con `fileUuid` no los puede leer, así que no los deja pasar.
- **Antes de un comando de terminal** (Bash y `device_bash`): bloquea arrancar impresiones por red, subir modelos, G-code o perfiles a internet, y escribir, mover o borrar en la carpeta de datos de Orca.
- **Después de laminar:** recuerda revisar el G-code antes de entregarlo.

Con un archivo de impresión 3D falla cerrado: si no lo puede leer o revisar, no lo deja escribir. Con cualquier otro archivo o comando, si el propio guardia falla, deja pasar (para no trabar otros trabajos) y la revisión explícita de las skills sigue vigente. Necesita `python3` donde corren los hooks (en Cowork ya está; en Claude Code para Windows, instalá Python).

## Límites conocidos

- La revisión del G-code no detecta todo: no conoce los clips, pinzas u objetos sobre la cama, ni un offset Z mal calibrado, ni fallas mecánicas. Supervisá siempre la primera capa.
- Los bloqueos automáticos (hooks) los cargan Cowork y Claude Code; el chat común de claude.ai los ignora (y ahí tampoco hay acceso a la PC). Por eso las reglas de seguridad también están escritas en las skills, y las revisiones (`revisar_gcode.py`, `perfil_orca.py`) se corren siempre de forma explícita antes de entregar o escribir algo.
- Los bloqueos de la terminal reconocen las formas comunes de subir archivos o tocar la carpeta de Orca, pero un comando rebuscado puede esquivarlos: son una red de seguridad, no la única barrera. Las skills prohíben esas acciones igual.
- El servidor MCP de Blender ejecuta código sin protecciones propias (lo advierte la propia Blender Foundation): es opcional; activarlo solo cuando se use.
- Probado en Linux (Ubuntu 24.04) con una Creality Ender-3 V3 Plus. Otras impresoras se agregan con sus límites oficiales (`/impresoras`).
- El instalador de Windows no se probó todavía en una PC con Windows. En Windows, la app de Claude (MSIX) no puede crear archivos dentro de AppData que otros programas vean: por eso los datos de Orca se mueven fuera de AppData.

## Componentes de terceros

Las licencias de los programas que usa o instala el taller, y qué contenido sale de OrcaSlicer, están en [AVISOS-DE-TERCEROS.md](AVISOS-DE-TERCEROS.md).

## Reportar un problema de seguridad

Reportalo en privado desde GitHub: en el repositorio, pestaña **Security → Report a vulnerability** (https://github.com/noamix/Taller-3d-printaia/security/advisories/new). Contá qué pasó, con qué versión y cómo reproducirlo. No lo publiques en Issues hasta que esté corregido. Los demás problemas van a Issues: https://github.com/noamix/Taller-3d-printaia/issues
