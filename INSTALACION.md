# Instalación de taller-3d

taller-3d convierte a Claude en un ayudante de impresión 3D: diseña piezas, elige la configuración de OrcaSlicer según el uso, lamina, revisa el G-code por seguridad, calcula costos, calibra filamentos y arma la publicación para tu tienda. **Nunca arranca una impresión: eso lo hacés vos.**

Antes de instalar, leé el [aviso de uso](DISCLAIMER.md).

## Qué necesitás

- Una cuenta de Claude con plan pago (Pro o superior) y la **app de escritorio de Claude** en la PC donde está Orca.
- Una PC con **Linux** (probado en Ubuntu 24.04) o **Windows 10/11** (instalador sin probar todavía en una PC real). macOS: a mano (sección C).
- Una impresora 3D que OrcaSlicer soporte.
- Blender es opcional (formas orgánicas o decorativas).
- Para pedir solo diseños (`/diseno`) alcanza con Claude: no hace falta instalar nada en la PC.

### Lo que pide la PC

Según OrcaSlicer: sistema de 64 bits, **4 GB de memoria como mínimo (8 GB o más recomendado)**, placa de video con **OpenGL 3.3** y 500 MB libres. El taller suma unos 200 MB (orca-mcp y su Python) y necesita internet para bajar todo.

Los dos instaladores, **antes de cambiar nada**, revisan que la PC alcance: sistema, procesador, memoria, placa de video, disco libre, internet y, en Windows, permisos para instalar. Si algo no alcanza, te dicen qué y no tocan nada. Si alcanza justo (por ejemplo, poca memoria o una placa vieja), te avisan y siguen. La placa de video solo importa para la ventana de Orca: Claude lamina igual sin ella.

Después **revisan qué tenés** (Orca, orca-mcp, la app de Claude, la carpeta de trabajo) y saltean lo que ya está. Si usás un Orca portable o en un contenedor, te preguntan la ruta.

## Primero: sumá el plugin a Claude desde GitHub

1. Instalá la app de escritorio de Claude (https://claude.ai/download) e iniciá sesión.
2. Andá a **Plugins › Agregar › Agregar marketplace › Agregar desde un repositorio** (en inglés: *Customize → Plugins → Add marketplace*), pegá `noamix/Taller-3d-printaia` (o `https://github.com/noamix/Taller-3d-printaia`) y tocá **Sincronizar**. Usá solo esta dirección: una copia (fork) puede traer cambios que nadie revisó.
3. Instalá **taller-3d**. Para recibir las versiones nuevas, activá la sincronización automática del marketplace (*Sync automatically*) o buscá actualizaciones (*Check for updates*) cuando quieras.

En Claude Code: `/plugin marketplace add noamix/Taller-3d-printaia` y `/plugin install taller-3d@taller-3d`; para las actualizaciones, ver el [README](README.md#instalación).

Más adelante el taller va a estar también en el directorio de plugins de Anthropic; cuando esté, esta guía lo va a explicar.

## A. Linux, con el instalador

1. Sumá el plugin a Claude (sección anterior), si todavía no lo hiciste.
2. Conseguí el instalador: en Claude escribí `/instalar` y te lo deja en una carpeta de tu PC. También lo podés bajar de GitHub: en la página del repositorio, **Code → Download ZIP**; descomprimilo y usá la carpeta `instalador/`.
3. Abrí una terminal en esa carpeta y corré primero el modo prueba, que muestra todo lo que haría sin cambiar nada:
   ```bash
   bash instalar.sh --prueba
   ```
4. Si estás de acuerdo, corré:
   ```bash
   bash instalar.sh
   ```
   El instalador:
   - revisa que la PC alcance y, si no, se detiene sin cambiar nada;
   - te muestra qué tenés y qué falta;
   - te muestra el aviso de uso y te pide que escribas ACEPTO;
   - usa el Orca que ya tengas (AppImage, Flatpak, del sistema, portable o en un contenedor). Si no hay, descarga **OrcaSlicer 2.5.1** de su página oficial de GitHub y verifica la huella SHA-256 (`073b8105c928356141db0ddbce88b81d52c7a9e2442f9baae0a9089c89ff04eb`); si no coincide, descarta el archivo;
   - si faltan bibliotecas del sistema que Orca necesita (OpenGL, WebKitGTK 4.1) o `fuse3` (lo usa el AppImage), te ofrece instalarlas con `sudo apt` (pide tu contraseña; podés decir que no: sin `fuse3`, Orca igual abre, más lento);
   - crea un lanzador (`~/.local/bin/orca-slicer-taller`) para que Claude use tus perfiles, y el acceso directo del menú si instaló Orca;
   - instala **orca-mcp 0.1.0** (licencia MIT), la conexión entre Claude y Orca, con `uv` o `pipx`;
   - te pregunta dónde guardar tus archivos (Enter = `Documentos/Taller 3D`) y crea ahí la carpeta de trabajo con su configuración;
   - si tu Orca es de Flatpak y no puede ver la carpeta de trabajo, te ofrece darle acceso solo a esa carpeta;
   - te muestra la entrada para la app de Claude y, si querés, la agrega con una copia de respaldo de tu configuración.
   Todo queda anotado en `~/.local/state/taller-3d/` (registro y lista de lo instalado).
5. Cerrá y abrí la app de Claude.

Opciones: `--orca RUTA` (un Orca que ya tengas: ejecutable, AppImage o el script que lo abre), `--datos-orca DIR` (su carpeta de datos), `--carpeta-apps DIR` (dónde guardar Orca), `--carpeta-trabajo DIR`, `--sin-app` (no tocar la configuración de la app).

**Orca en un contenedor (distrobox, toolbox, Docker):** Claude le pasa a Orca rutas de tu PC (el modelo, los perfiles y la carpeta de salida), así que el contenedor tiene que ver tu carpeta personal en la misma ruta. distrobox y toolbox lo hacen solos; en Docker, montá `$HOME` en `$HOME`. Si no, instalá el oficial al lado.

**Sistemas más viejos que Ubuntu 24.04:** el AppImage oficial no anda. Instalá Orca desde Flathub (`flatpak install flathub com.orcaslicer.OrcaSlicer`) y corré el instalador: lo encuentra solo.

## B. Windows, con el instalador

> Todavía no se probó en una PC con Windows: se revisó la sintaxis y las funciones con PowerShell 7. Si algo falla, el registro queda en `%LOCALAPPDATA%\taller-3d\` y podés mandárselo al autor.

1. Sumá el plugin a Claude (sección anterior), si todavía no lo hiciste.
2. Conseguí el instalador: en Claude escribí `/instalar` y te lo deja en una carpeta de tu PC. También lo podés bajar de GitHub: en la página del repositorio, **Code → Download ZIP**; descomprimilo (clic derecho → **Extraer todo**) y usá la carpeta `instalador/`.
3. Para ver qué haría sin cambiar nada: abrí PowerShell en esa carpeta y corré `.\instalar-windows.bat -Prueba`.
4. Hacé doble clic en **`instalar-windows.bat`**. Si Windows muestra "Windows protegió su PC", tocá "Más información" → "Ejecutar de todos modos".
   El instalador:
   - revisa que la PC alcance (sistema, procesador, memoria, placa de video, disco, internet y permisos) y, si no, se detiene sin cambiar nada;
   - te muestra qué tenés y qué falta (Orca, WebView2, la app de Claude, orca-mcp, la carpeta de trabajo);
   - te muestra el aviso de uso y te pide que escribas ACEPTO;
   - si la app de Claude es la versión empaquetada de Windows (MSIX, la que se baja hoy de claude.ai), te ofrece **mover la carpeta de datos de Orca** de `%APPDATA%\OrcaSlicer` a `C:\Users\<vos>\OrcaSlicer` y dejar un acceso en el lugar de siempre. Hace falta porque Windows guarda en un lugar privado los archivos nuevos que esa app crea dentro de AppData, y Orca no los vería. Orca sigue funcionando igual;
   - usa el Orca que ya tengas (instalado o portable). Si no hay, baja el **instalador oficial de OrcaSlicer 2.5.1** (x64 o ARM64), verifica su huella SHA-256 y su firma digital (ORCASLICER PTE. LTD.) y lo abre para que lo instales vos (Windows te pide permiso);
   - instala **orca-mcp 0.1.0** con uv. Si no tenés uv, baja la versión oficial 0.13.9 y verifica su huella;
   - te pregunta dónde guardar tus archivos (Enter = `Documentos\Taller 3D`; fuera de AppData) y crea ahí la carpeta de trabajo con su configuración;
   - con la app de Claude cerrada, agrega orca-mcp a su configuración, con copia de respaldo.
   Todo queda anotado en `%LOCALAPPDATA%\taller-3d\` (registro y lista de lo instalado).
5. Abrí la app de Claude.

Opciones (en PowerShell): `-Orca "<ruta de orca-slicer.exe>"` (por ejemplo, uno portable), `-CarpetaTrabajo "<carpeta>"`, `-SinApp`.

**Si preferís WSL con Ubuntu:** se puede usar el instalador de Linux adentro de WSL, pero no lo recomendamos: Orca abre como ventana de Linux y la app de Claude de Windows no ve orca-mcp sin configurarlo a mano. El instalador de Linux avisa si detecta WSL.

## C. macOS, a mano

1. Instalá OrcaSlicer 2.5.1 desde https://github.com/OrcaSlicer/OrcaSlicer/releases (versión oficial).
2. Instalá Python 3.10 o más nuevo y después orca-mcp: `pipx install orca-mcp==0.1.0` (o `uv tool install orca-mcp==0.1.0`).
3. En la app de Claude: Configuración → Desarrollador → Editar configuración, y agregá:
   ```json
   {
     "mcpServers": {
       "orca-mcp": {
         "command": "orca-mcp",
         "env": { "ORCASLICER_PATH": "/Applications/OrcaSlicer.app/Contents/MacOS/OrcaSlicer" }
       }
     }
   }
   ```
4. Reiniciá la app de Claude.

## Después de instalar (todos los sistemas)

1. **Abrí OrcaSlicer una vez** y agregá tu impresora con el asistente. Guardá una copia de usuario del perfil de la impresora, por ejemplo `Mi Ender-3 V3 Plus 0.4 nozzle`, y un perfil propio de proceso y de filamento: así Orca crea las carpetas de perfiles.
2. **Conectá las carpetas** en la app de Claude (menú + → Agregar carpeta), con las rutas que te muestra el instalador al final:
   - la carpeta de trabajo;
   - las carpetas `process` y `filament` de tus perfiles de Orca. Linux: `~/.config/OrcaSlicer/user/default/...` (Flatpak: `~/.var/app/com.orcaslicer.OrcaSlicer/config/OrcaSlicer/user/default/...`). Windows: `C:\Users\<vos>\OrcaSlicer\user\default\...` (**no** por AppData). macOS: `~/Library/Application Support/OrcaSlicer/user/default/...`.
3. En Claude escribí **`/instalar`**: revisa que todo ande, registra tu impresora, carga tus precios y tu tienda si querés, y hace una pieza de prueba.

## Blender (opcional)

Para formas orgánicas o decorativas, instalá Blender desde https://www.blender.org y su servidor MCP oficial siguiendo https://www.blender.org/lab/mcp-server/. Ojo: ese servidor ejecuta en Blender el código que genera la IA, sin protecciones propias; activalo solo cuando lo uses. Para piezas funcionales el taller usa CAD por código y no necesita Blender.

## Problemas frecuentes

| Problema | Qué hacer |
|---|---|
| Claude no ve Orca | Reiniciá la app de Claude. En `/instalar`, Claude te dice el estado de orca-mcp (y el error si no arranca). |
| "Preset not found" al laminar | Abrí Orca una vez; verificá que el perfil herede de uno de sistema. En Windows, que los datos de Orca estén fuera de AppData (paso B.4). |
| Windows: Orca no muestra los perfiles AUTO | La carpeta de perfiles está conectada por AppData o los datos no se movieron: corré de nuevo el instalador y conectá la ruta `C:\Users\<vos>\OrcaSlicer\...`. |
| Orca no abre (Linux): falta libOpenGL o WebKitGTK | `sudo apt install libopengl0 libwebkit2gtk-4.1-0 libjavascriptcoregtk-4.1-0` |
| Orca no abre (Windows): pide WebView2 | Instalá Microsoft Edge WebView2 desde https://developer.microsoft.com/microsoft-edge/webview2/ |
| Orca de Flatpak no lamina archivos de la carpeta de trabajo | `flatpak override --user --filesystem="<carpeta de trabajo>" com.orcaslicer.OrcaSlicer` |
| Orca no muestra un perfil nuevo | Cerralo y abrilo: lee los perfiles al iniciar. |
| Claude no puede escribir en la PC | Conectá las carpetas (paso 2 de "Después de instalar") o aprobá el permiso cuando lo pida. |

## Desinstalar

- Linux: `bash desinstalar.sh --prueba` muestra lo que quitaría; `bash desinstalar.sh` lo manda a la papelera (pide escribir QUITAR).
- Windows: `.\desinstalar-windows.bat -Prueba` muestra lo que quitaría; doble clic en `desinstalar-windows.bat` lo quita (pide escribir QUITAR) y devuelve los datos de Orca a AppData. Con `-Orca` también abre el desinstalador de Orca.
- La carpeta de trabajo y tus perfiles de Orca se conservan salvo que uses `--todo` (Linux) o `-Todo` (Windows) y lo confirmes.
- El plugin se quita desde la configuración de plugins de la app de Claude.
