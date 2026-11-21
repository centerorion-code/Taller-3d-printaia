# Cambios

## 0.1.5 (2026-11-21)

- **Catálogo de piezas** (`/catalogo` y `catalogo.py`): `catalogo.html` en la carpeta de trabajo muestra todas las piezas con su vista (o la foto real, si la mandaste), medidas, material, tiempo, gramos, costo, precio, estado y enlaces a sus archivos, ordenadas por mes, con buscador y filtros. Se actualiza solo cuando `/pieza`, `/diseno` o `/publicar` guardan algo, y "armá el catálogo" suma las piezas que ya tenías. El índice queda en `taller-3d/catalogo.json`.
- La página funciona sin internet y escapa todo lo que muestra; los enlaces a la tienda solo se aceptan con `http` o `https`.
- 46 pruebas automáticas.

## 0.1.4 (2026-11-21)

- **Licencia GNU AGPL 3.0** (`LICENSE`), con encabezado de licencia en cada script y `AVISOS-DE-TERCEROS.md`, que detalla qué sale de OrcaSlicer (el catálogo de parámetros) y las licencias de lo que usa o instala el taller.
- **Listo para GitHub:** `.claude-plugin/marketplace.json` convierte el repositorio en un marketplace; el README explica cómo sumarlo desde Claude, desde Claude Code o con el archivo.
- Contacto por GitHub (Issues y reporte privado de seguridad); el mail del autor ya no figura en el plugin.
- **Los instaladores revisan, antes de cambiar nada, que la PC alcance:** sistema, procesador, memoria (4 GB mínimo, 8 GB recomendado), placa de video (OpenGL 3.3 en Linux; en Windows, driver, máquina virtual o placa vieja), disco libre, internet y, en Windows, permisos para instalar. Si algo no alcanza, se detienen sin tocar nada; si alcanza justo, avisan.
- Linux: el AppImage de Orca necesita `fusermount` (paquete `fuse3`); si falta, el instalador lo ofrece, y si no se instala, Orca abre extrayéndose (más lento).
- **Los instaladores preguntan dónde guardar tus archivos** (Enter = `Documentos/Taller 3D`); si ya habías instalado, usan la misma carpeta. `/instalar` pregunta lo mismo.

### Correcciones de seguridad (revisión independiente)

- **Bloqueos que se podían esquivar:**
  - `device_commit_files` con `fileUuid` en lugar de `stagedPath` pasaba sin revisión. Ahora los G-code, proyectos y perfiles tienen que ir con `stagedPath`, y si el archivo no se puede leer o revisar, no se escribe (falla cerrado).
  - La revisión del G-code leía mal líneas que el firmware sí ejecuta: con número de línea y suma de control (`N10 M104 S400*45`), con los parámetros pegados (`M104S400`, `M302P1`) o con la letra repetida. Ahora las lee igual que el firmware. Se suman M149, M301, M304, G92 Z y M221 por encima del 200 % (rechazo), y M81 y M221 por encima del 120 % (aviso).
  - En los perfiles, una temperatura con un espacio al final (`"400 "`) no se controlaba. Ahora sí, y también las de espera, purga y torre. El G-code de adentro del perfil (inicio, fin, cambio de capa o de filamento) pasa por la misma revisión que el laminado.
- **Más cobertura del bloqueo automático:**
  - `Write`, `Edit` y `MultiEdit` (Claude Code), y `device_bash` en la PC.
  - Más extensiones: `.g`, `.gc`, proyectos `.3mf` y `.gcode.3mf`. El G-code binario (`.bgcode`) se rechaza, porque no se puede leer.
  - Rutas con `..`, los perfiles que vienen con Orca, `orca_plugins` y `OrcaSlicer.conf`.
  - Escribir, mover o borrar en la carpeta de Orca desde la terminal.
  - Más formas de subir archivos: `curl -sF`, rclone, lftp, nube y otras. `ftp` en el medio de otra palabra ya no da falso positivo.
- **Desinstaladores:**
  - Linux: las confirmaciones leían líneas de la lista de lo instalado. Solo se quita lo que está dentro de tu carpeta personal; sin papelera, va a una carpeta en tu casa. Se toleran configuraciones de la app con `mcpServers` vacío.
  - Windows: los datos de Orca se copian de vuelta antes de sacar la unión, y si algo falla queda como estaba. Al instalar, si no se puede crear la unión, se devuelve la carpeta. Solo se deshacen las entradas conocidas, y nada fuera de su lugar.
- **Instaladores:**
  - Ya no se cortan en silencio cuando falta OpenGL o `ldconfig`. Si algo falla a mitad de camino, avisan qué quedó y cómo deshacerlo.
  - El lanzador acepta rutas con espacios, comillas o `$`. Con Orca de Flatpak, los temporales de orca-mcp van a una carpeta que el Flatpak ve.
  - Antes de tocar la configuración se espera a que la app de Claude esté cerrada, reconocida por su ruta y no por el nombre, que comparte con Claude Code. En Windows, la app de la Tienda que todavía lee la configuración de la clásica parte de una copia de esa.
  - El registro de Windows se lee clave por clave. El instalador de Orca ya no espera a que cierres Orca. Las opciones sin valor dan un error claro.
- `SECURITY.md` dice con precisión qué se verifica con huella y qué no (orca-mcp viene de PyPI en versión fija, sin huella propia).
- Los datos que salen de OrcaSlicer llevan su aviso de origen y fecha de modificación.
- 45 pruebas automáticas.

## 0.1.3 (2026-11-21)

- **Instalador para Windows** (`instalar-windows.bat` + `instalar.ps1`, y su desinstalador): OrcaSlicer 2.5.1 oficial x64 o ARM64 con huella SHA-256 y firma digital verificadas, orca-mcp con uv (bajado y verificado si hace falta), carpeta de trabajo, entrada en la app de Claude con respaldo, modo prueba, registro y lista de lo instalado. Revisado con PowerShell 7 (sintaxis, compatibilidad con Windows PowerShell 5.1 y funciones); falta probarlo en una PC con Windows.
- En Windows, la app de Claude (MSIX) no puede crear archivos dentro de AppData que Orca vea: el instalador ofrece mover los datos de Orca a `C:\Users\<usuario>\OrcaSlicer` con una unión de carpetas, y el desinstalador los devuelve.
- Los dos instaladores **revisan primero qué hay** y saltean lo que ya está. Usan el Orca que ya tengas (AppImage, Flatpak, del sistema, instalado, portable o en un contenedor) y preguntan la ruta si no lo encuentran (`--orca` / `-Orca`). El de Linux avisa si corre en WSL y, con Orca de Flatpak, ofrece darle acceso solo a la carpeta de trabajo.
- La entrada de orca-mcp ahora indica también la carpeta de datos de Orca (`ORCASLICER_CONFIG_DIR`).
- **`/diseno`:** pedidos de solo diseño paramétrico (STL, `pieza.py`, vista y `parametros.md`), sin laminar y sin necesitar la PC. `revisar_stl.py --impresora ninguna` revisa la malla sin impresora.
- **Publicación en paralelo:** al terminar una pieza, `/pieza` ofrece armar el borrador de la tienda en el momento, con imagen ilustrativa (`vista_previa.py --producto --color`) hasta tener la foto real. Se aprueba también desde el celular.
- **Plugins de Orca:** guía (`references/plugins-orca.md`) con los que sirven al taller y sus riesgos; ante pedidos como llaveros, carteles o floreros, Claude busca en el Plugin Hub y los sugiere, sin instalarlos.
- **Novedades de Orca** (`novedades_orca.py`): después de cada laminado compara el Orca del usuario con las 750 claves de la 2.5.1; una vez por mes recuerda revisar versiones y plugins nuevos; detecta claves viejas en perfiles y perfiles TEST o AUTO que sobran. Lo aprendido queda en `taller-3d/novedades-orca.json`.
- Seguridad: los perfiles que escribe Claude no pueden llevar scripts de posprocesado ni plugins (`post_process`, `plugins`, `slicing_pipeline_plugin`), porque Orca los ejecuta al laminar; al copiar un perfil base se quitan y se avisa.
- El bloqueo automático también revisa perfiles en rutas de Windows y de Orca portable (`data_dir`).
- 34 pruebas automáticas.

## 0.1.2 (2026-11-21)

- Manual de uso (`MANUAL.md`): cómo pedir una pieza, ejemplos, el circuito completo, qué decide el usuario, dónde quedan los archivos y preguntas frecuentes.
- Comando `/ayuda`, que explica el taller a partir del manual.
- `/publicar` revisa la licencia de los modelos bajados de internet antes de cargarlos a la venta.

## 0.1.1 (2026-11-21)

- Contacto del autor y de seguridad (README, SECURITY.md y plugin.json).

## 0.1.0 (2026-11-21)

Primera versión.

- Skills: `impresion-3d` (conocimiento y reglas), `/pieza`, `/calibrar`, `/impresoras`, `/publicar`, `/instalar`, `/restaurar`.
- Scripts: CAD por código (`cad.py`), revisión de mallas (`revisar_stl.py`), vista previa (`vista_previa.py`), perfiles de Orca validados contra el catálogo (`perfil_orca.py`), revisión de seguridad de G-code con costo (`revisar_gcode.py`) y ficha de producto para tiendas (`producto_tienda.py`).
- Catálogo de los 1015 parámetros de OrcaSlicer 2.5.1 en español.
- Datos de la Creality Ender-3 V3 Plus y rangos de materiales.
- Bloqueos automáticos de seguridad (hooks).
- Instalador y desinstalador para Linux con versiones fijas y verificación SHA-256.
- 29 pruebas automáticas de los scripts y del guardia.
- Probado de punta a punta en una Ender-3 V3 Plus real: modelo, perfiles AUTO, laminado con orca-mcp y revisión APROBADA.
- Por línea de comandos Orca ignora el tipo de cama del proceso y usa "Cool Plate": el `AUTO filamento` copia las temperaturas de la cama real (`perfil_orca.py --cama`) y `revisar_gcode.py --cama-primera-capa` lo verifica.
