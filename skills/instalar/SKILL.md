---
name: instalar
description: Prepara o revisa la instalación del taller 3D en la PC del usuario (OrcaSlicer, conexión orca-mcp, carpetas, aviso de uso, configuración, impresora, costos y tienda), saltea lo que ya está y hace una pieza de prueba. Se usa cuando el usuario dice "instalar", "configurar el taller", "es la primera vez", "revisá que esté todo bien", "no anda Orca desde Claude", "tengo Orca portable" o después de instalar el plugin.
---

# /instalar: instalación guiada y chequeo

Cargar antes la skill `impresion-3d` y seguir sus reglas. Archivos del instalador: `<raíz del plugin>/instalador/` y `<raíz del plugin>/INSTALACION.md`.

## 1. Diagnóstico (siempre primero)

Con `get_device_info` y las herramientas de Orca, armar una tabla corta de estado. **Todo lo que ya está se marca como listo y no se vuelve a hacer.**

| Punto | Cómo verificarlo |
|---|---|
| PC conectada y sistema | `get_device_info` responde; anotar la plataforma (Linux, Windows o macOS) |
| orca-mcp | `localMcpServers`: `announced`; si está `failed`, mostrar el error que reporta |
| Orca instalado | `check_installation`: ruta, tipo (nativo, AppImage, Flatpak) y versión del banner |
| Perfiles de Orca | `list_profiles`: hay un perfil de máquina de usuario; anotar la carpeta real de los perfiles |
| Carpetas conectadas | `connectedFolders` incluye la carpeta de trabajo y `process`/`filament` de Orca |
| Configuración | existe `<trabajo>/taller-3d/config.json` y tiene `aceptacion` e `impresoras` |
| Windows: datos de Orca | si la plataforma es Windows, la carpeta de perfiles conectada **no** tiene que estar bajo `AppData` (ver sección 2) |
| Blender (opcional) | `localMcpServers` |

Si todo está bien, decirlo y ofrecer la pieza de prueba (paso 5). Si algo falta, seguir solo con lo que corresponda.

**Orca que no aparece:** si `check_installation` no lo encuentra, preguntar si usa uno portable (sin instalar) o en un contenedor (distrobox, toolbox, Docker). En ese caso el instalador lo usa con `--orca <ruta>` (Linux) o `-Orca <ruta>` (Windows). Con Docker, Orca tiene que ver la carpeta personal en la misma ruta; si no, recomendar el oficial al lado.

## 2. Falta orca-mcp, Orca o la conexión

Dejar el instalador del sistema en la PC y explicar en 5 líneas qué hace: antes de tocar nada revisa que la PC alcance (sistema, procesador, memoria, placa de video, disco, internet y, en Windows, permisos) y se detiene si no; revisa qué hay y saltea lo que ya está; pide ACEPTO; verifica la huella de Orca (y en Windows la firma digital); y anota todo para poder desinstalarlo. Si el usuario cuenta qué dijo la revisión de la PC, interpretarlo: lo que "no alcanza" frena; los avisos de placa de video solo afectan la ventana de Orca, no el laminado desde Claude.

1. Pedir acceso a una carpeta conocida (por ejemplo, Descargas) si no hay ninguna conectada.
2. Copiar a `/mnt/user-data/outputs/taller-3d/instalador/` y commitear juntos a `<carpeta>/taller-3d-instalador/`, más `DISCLAIMER.md` e `INSTALACION.md`:
   - **Linux:** `instalar.sh` y `desinstalar.sh`. Indicar: abrir una terminal ahí, correr `bash instalar.sh --prueba`, leer, y después `bash instalar.sh`.
   - **Windows:** `instalar.ps1`, `desinstalar.ps1`, `instalar-windows.bat` y `desinstalar-windows.bat`. Indicar: doble clic en `instalar-windows.bat` (si Windows muestra un aviso, "Más información" → "Ejecutar de todos modos"); para ver antes qué haría, abrir PowerShell en la carpeta y correr `.\instalar-windows.bat -Prueba`. Avisar que el instalador de Windows no se probó en una PC real todavía.
   - **macOS:** guiar con la sección C de `INSTALACION.md` (sin instalador; decirlo).
3. Al terminar, que cierre y abra la app de Claude y vuelva a `/instalar`.
- No correr comandos de instalación por otros medios ni pedir contraseñas.

### Windows: datos de Orca fuera de AppData

La app de Claude de Windows es un paquete MSIX: Windows manda a una carpeta privada los archivos **nuevos** que la app crea dentro de `AppData`, y Orca no los ve. Por eso el instalador mueve la carpeta de datos de Orca a `C:\Users\<usuario>\OrcaSlicer` y deja una unión de carpetas en `%APPDATA%\OrcaSlicer`.

- Conectar siempre las carpetas de perfiles por la ruta nueva (`C:\Users\<usuario>\OrcaSlicer\user\default\process` y `...\filament`), nunca por `AppData`.
- Si la carpeta de perfiles conectada está bajo `AppData` o `list_profiles` muestra rutas bajo `AppData` sin la unión, **no escribir perfiles nuevos**: explicar el motivo y pedir que corra de nuevo el instalador (ofrece mover los datos).
- Después de escribir el primer perfil `AUTO`, pedir que confirme que aparece en Orca (reiniciándolo). Si no aparece, es este problema.

## 3. Carpetas

1. Si no hay carpeta de trabajo, **preguntar dónde quiere guardar sus archivos** antes de crear nada: explicar en una línea qué va ahí (diseños, impresiones con sus vistas y G-code, respaldos y configuración) y ofrecer opciones (`AskUserQuestion` si está): `Documentos/Taller 3D` (recomendada), una carpeta que ya use para impresión 3D (si se ve una entre las conectadas) u otra que diga. No usar AppData en Windows ni la carpeta de Orca. Si el instalador ya la creó, usar esa sin volver a preguntar. Pedir acceso a la elegida junto con las carpetas `process` y `filament` de los perfiles de Orca en **un solo pedido**. Rutas: Linux `~/.config/OrcaSlicer/user/default/...` (Flatpak: `~/.var/app/<id>/config/OrcaSlicer/user/default/...`); Windows, la ruta nueva de la sección 2; macOS `~/Library/Application Support/OrcaSlicer/user/default/...`. Confirmar la ruta real con `list_profiles`.
2. Crear `impresiones/`, `disenos/`, `respaldos/`, `calibraciones/` y `taller-3d/` escribiendo un `LEEME.md` corto en cada una (si no existen).

## 4. Configuración inicial

1. **Aviso de uso:** si `config.json` no tiene `aceptacion`, mostrar un resumen de `DISCLAIMER.md` (puntos 1-8 en una línea cada uno) y pedir que escriba ACEPTO. Guardar fecha, versión del plugin y texto.
2. **Impresoras:** seguir `/impresoras` para la primera impresora (perfil de máquina de usuario, datos y límites, tipo de cama, perfiles propios de proceso y filamento que ya tenga, nombres AUTO).
3. **Costos (opcional):** precio del kWh, precio por kg de cada filamento, consumo de la impresora (180 W si no lo sabe; mejor medirlo).
4. **Tienda (opcional):** plataforma (WooCommerce, Tiendanube, Shopify, Mercado Libre u otra), URL, margen, costo por hora de máquina, embalaje, redondeo y demora. Sin contraseñas.
5. Escribir `config.json` (formato en `references/configuracion.md` de la skill `impresion-3d`) con el procedimiento de escritura y crear `historial.csv` con encabezado. Si ya existe, completar solo lo que falte.

## 5. Pieza de prueba

1. Generar con `cad.py` un cubo de calibración de 20 × 20 × 20 mm con chaflán inferior.
2. Laminar con los perfiles de la impresora predeterminada: `AUTO proceso` y `AUTO filamento` creado con `--cama` de la configuración (como en `/pieza`).
3. Traer el G-code y correr `revisar_gcode.py --cama-primera-capa <temperatura>`: tiene que salir APROBADO, con las temperaturas y la cama correctas.
4. Mostrar tiempo, gramos y costo (si hay precios) y dejar todo en `impresiones/AAAA-MM-DD_cubo-prueba/`.
5. Cerrar con: qué quedó listo, qué falta (si algo), los comandos disponibles (`/pieza`, `/diseno`, `/calibrar`, `/impresoras`, `/publicar`, `/restaurar`, `/ayuda`) y cómo pedir una pieza con un ejemplo de `MANUAL.md`. Ofrecer dejar el manual en la carpeta de trabajo.
