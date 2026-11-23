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
| Carpetas conectadas | `connectedFolders` incluye la carpeta de trabajo y la de perfiles de usuario de Orca (`user/<id>`, o `process` y `filament` por separado) |
| Configuración | existe `<trabajo>/taller-3d/config.json` y tiene `aceptacion` e `impresoras` |
| Impresoras | `list_profiles` (machine): cuáles hay en Orca; en `config.json`, cuáles están preparadas (su `datos` es un JSON en `taller-3d/impresoras/` que pasa `impresora.py validar`). Si `datos` es un id viejo (`ender-3-v3-plus`), prepararla de nuevo con `/impresoras` |
| Windows: datos de Orca | si la plataforma es Windows, la carpeta de perfiles conectada **no** tiene que estar bajo `AppData` (ver sección 2) |
| Abrir Orca desde Claude y el panel (opcional, Linux) | `localMcpServers`: `taller3d-orca` `announced`. Si falta, decir que corriendo de nuevo el instalador (paso "Abrir Orca desde Claude y desde el panel") Claude y los botones del panel le abren Orca con la pieza. Si está, comprobar que atienda **esta** carpeta de trabajo con la sonda de abajo |
| Blender (opcional) | `localMcpServers` |
| Piezas desde una foto y textos de venta (opcional) | `config.json` tiene `generadores_ia` (cuenta de Hunyuan 3D, generador de imágenes y quién escribe los textos); Claude in Chrome conectado |

Si todo está bien, decirlo y ofrecer la pieza de prueba (paso 5). Si algo falta, seguir solo con lo que corresponda.

**Sonda de `taller3d-orca`** (no abre nada): llamar a `abrir_en_orca` con la ruta absoluta de un `.3mf` que no existe dentro de la carpeta de trabajo, por ejemplo `<trabajo>/taller-3d/sonda-no-existe.3mf`. Si contesta «No existe ese proyecto en la carpeta de trabajo», atiende esta carpeta. Si contesta «Solo abro proyectos que estén dentro de la carpeta de trabajo…», atiende otra (pasa si hay dos carpetas de trabajo o si el instalador corrió con otra): el botón «Abrila en Orca» no va a andar. Arreglo: que corra de nuevo `bash instalar.sh` (desde la 0.1.34 apunta siempre a `Documentos/Taller 3D`) y, cuando lo pida, **cierre la app de Claude del todo** (Salir desde el ícono de la bandeja; cerrar la ventana no alcanza), porque la app reescribe su configuración con lo que tiene en memoria y pisaría el cambio. Desde la 0.1.29 el instalador no escribe mientras la app siga abierta. El programa atiende una sola carpeta: si el usuario tiene dos, preguntarle cuál usa y ofrecer pasar a esa lo que sirva de la otra.

**Orca que no aparece:** si `check_installation` no lo encuentra, preguntar si usa uno portable (sin instalar) o en un contenedor (distrobox, toolbox, Docker). En ese caso el instalador lo usa con `--orca <ruta>` (Linux) o `-Orca <ruta>` (Windows). Con Docker, Orca tiene que ver la carpeta personal en la misma ruta; si no, recomendar el oficial al lado.

## 2. Falta orca-mcp, Orca o la conexión

Dejar el instalador del sistema en la PC y explicar en 5 líneas qué hace: antes de tocar nada revisa que la PC alcance (sistema, procesador, memoria, placa de video, disco, internet y, en Windows, permisos) y se detiene si no; revisa qué hay y saltea lo que ya está; pide ACEPTO; verifica la huella de Orca (y en Windows la firma digital); y anota todo para poder desinstalarlo. Si el usuario cuenta qué dijo la revisión de la PC, interpretarlo: lo que "no alcanza" frena; los avisos de placa de video solo afectan la ventana de Orca, no el laminado desde Claude.

1. Pedir acceso a una carpeta conocida (por ejemplo, Descargas) si no hay ninguna conectada.
2. Copiar a `/mnt/user-data/outputs/taller-3d/instalador/` y commitear juntos a `<carpeta>/taller-3d-instalador/`, más `DISCLAIMER.md` e `INSTALACION.md`:
   - **Linux:** `instalar.sh`, `desinstalar.sh` y `abrir_orca.py` (el programa que deja a Claude y al panel abrir la ventana de Orca: va al lado de `instalar.sh`). Indicar: abrir una terminal ahí, correr `bash instalar.sh --prueba`, leer, y después `bash instalar.sh`. Si ya estaba instalado, saltea lo que hay y suma lo nuevo.
   - **Windows:** `instalar.ps1`, `desinstalar.ps1`, `instalar-windows.bat` y `desinstalar-windows.bat`. Indicar: doble clic en `instalar-windows.bat` (si Windows muestra un aviso, "Más información" → "Ejecutar de todos modos"); para ver antes qué haría, abrir PowerShell en la carpeta y correr `.\instalar-windows.bat -Prueba`. Avisar que el instalador de Windows no se probó en una PC real todavía.
   - **macOS:** guiar con la sección C de `INSTALACION.md` (sin instalador; decirlo).
3. Al terminar, que cierre y abra la app de Claude y vuelva a escribir `/taller-3d:instalar` (en la app los comandos llevan el prefijo del plugin).
- No correr comandos de instalación por otros medios ni pedir contraseñas.

### Windows: datos de Orca fuera de AppData

La app de Claude de Windows es un paquete MSIX: Windows manda a una carpeta privada los archivos **nuevos** que la app crea dentro de `AppData`, y Orca no los ve. Por eso el instalador mueve la carpeta de datos de Orca a `C:\Users\<usuario>\OrcaSlicer` y deja una unión de carpetas en `%APPDATA%\OrcaSlicer`.

- Conectar siempre la carpeta de perfiles por la ruta nueva (`C:\Users\<usuario>\OrcaSlicer\user\default`), nunca por `AppData`.
- Si la carpeta de perfiles conectada está bajo `AppData` o `list_profiles` muestra rutas bajo `AppData` sin la unión, **no escribir perfiles nuevos**: explicar el motivo y pedir que corra de nuevo el instalador (ofrece mover los datos).
- Después de escribir el primer perfil `AUTO`, pedir que confirme que aparece en Orca (reiniciándolo). Si no aparece, es este problema.

## 3. Carpetas

Hacen falta dos: la **carpeta de trabajo** (diseños, impresiones con sus vistas y G-code, respaldos y configuración) y la **carpeta de perfiles de usuario de Orca** (`user/<id>`, que tiene `process`, `filament` y `machine`). La app solo conecta carpetas que ya existen: primero ubicarlas, después crear la de trabajo si falta y recién ahí pedir acceso a las dos en **un solo pedido**.

1. **Ubicar la carpeta de trabajo: es siempre `Taller 3D`, dentro de la carpeta de documentos del usuario** (`Documentos/Taller 3D` en Linux; `Documents\Taller 3D` o `Documentos\Taller 3D` en Windows; `Documents/Taller 3D` en macOS). No se pregunta dónde guardar y no se usa otra carpeta, para que todas las piezas queden en un solo lugar.
   - Si ya está conectada y tiene `taller-3d/config.json`, seguir: no preguntar nada.
   - Si no, ver si ya existe: `device_list_dir` sobre la carpeta de documentos (`Documentos` o `Documents`, según `homeDirectories` de `get_device_info`; sin permiso muestra solo los nombres de las carpetas) y buscar `Taller 3D`. Si en la carpeta personal están `Documentos` y `Documents`, usar la que ya tenga `Taller 3D`; si ninguna la tiene, preguntar cuál de las dos usa. En Windows con OneDrive, la carpeta de documentos puede estar dentro de `OneDrive`: usar la que diga el instalador en su cierre.
   - **Si hay un taller en otra carpeta** (una carpeta conectada con otro nombre que tiene `taller-3d/config.json`; pasa con instalaciones anteriores a la 0.1.34, o si el instalador avisó «Antes usabas …»): decirlo y ofrecer mudarlo con «Mudar un taller de otra carpeta» (abajo). No seguir guardando piezas nuevas en la otra.
2. **Si `Taller 3D` no existe, crearla** antes de pedir el acceso:
   - **Con terminal en la PC** (`device_bash`): crearla directamente con sus subcarpetas (`mkdir -p "<ruta>/impresiones" "<ruta>/disenos" "<ruta>/respaldos" "<ruta>/calibraciones" "<ruta>/taller-3d/impresoras"`; en PowerShell, `New-Item -ItemType Directory -Force -Path` con cada una).
   - **Sin terminal**, ofrecer las dos formas en una pregunta (`AskUserQuestion` si está; si no, en el texto):
     - **"Que la cree Claude"** (recomendada): pedir acceso a la carpeta de documentos solo para crearla, diciendo en el motivo que el permiso dura esta conversación y que se usa solo para la carpeta nueva. Crearla con sus subcarpetas escribiendo el `LEEME.md` de cada una (paso 4) y, de ahí en adelante, trabajar solo dentro de ella. En las próximas conversaciones se pide solo esa.
     - **"La creo yo"**: pedírselo en un mensaje propio, con estos pasos (así queda creada y conectada a la vez):
       1. En la app de Claude, tocá el **+** del cuadro de mensaje y elegí **Agregar carpeta**.
       2. En la ventana que se abre, entrá a **Documentos**.
       3. Creá una carpeta nueva con el botón de esa ventana (en Windows y macOS dice **Nueva carpeta**; en Linux es el ícono de carpeta con un **+**, arriba) y ponele **Taller 3D**.
       4. Entrá a **Taller 3D** y elegila (**Seleccionar** o **Abrir**). Después escribime "listo".
     Si rechaza el permiso o no responde, no volver a pedirlo: mandarle esos mismos pasos.
3. **Pedir acceso en un solo pedido** (`device_request_folder_access`) a la carpeta de trabajo y a la de perfiles de usuario de Orca, `user/<id>`: con esa alcanzan `process`, `filament` y `machine`, aunque `machine` todavía no exista (ahí se puede guardar después la copia de la impresora). Comprobar antes con `device_list_dir` que las dos existan. Rutas de la carpeta de perfiles: Linux `~/.config/OrcaSlicer/user/default` (Flatpak: `~/.var/app/com.orcaslicer.OrcaSlicer/config/OrcaSlicer/user/default`); Windows, la ruta nueva de la sección 2 (`C:\Users\<usuario>\OrcaSlicer\user\default`); macOS `~/Library/Application Support/OrcaSlicer/user/default`. Confirmar la ruta real con `list_profiles`.
   - Si ya tiene conectadas `process` y `filament` por separado, sirven igual; sumar `user/<id>` cuando haga falta `machine`.
   - Si `user/<id>` no existe, Orca todavía no guardó ningún perfil propio: pedirle que abra Orca, elija su impresora y guarde una copia (`references/impresoras.md`, sección 1, paso 4), y después conectarla.
   - Si rechaza el permiso, no repetir el pedido: explicarle cómo conectarlas desde el **+** → **Agregar carpeta**.
4. Crear `impresiones/`, `disenos/`, `respaldos/`, `calibraciones/`, `taller-3d/` y `taller-3d/impresoras/` escribiendo un `LEEME.md` corto en cada una (si no existen).

### Mudar un taller de otra carpeta a `Taller 3D`

Para quien tiene su taller en otra carpeta (instalaciones anteriores a la 0.1.34) o en dos. Nada se borra: lo que no se muda queda en la carpeta vieja y la borra el usuario cuando quiera.

1. Conectar las dos carpetas (la otra y `Documentos/Taller 3D`; crearla si falta, paso 2 de arriba) y traer de cada una `taller-3d/config.json`, `catalogo.json` e `historial.csv` (los que haya), cada taller a una carpeta local distinta.
2. Unirlos: `python3 -I mudar_taller.py --origen <la otra> --destino <la de Taller 3D> --carpeta "<ruta de Taller 3D en la PC>" --salida <carpeta local>`. De la configuración manda la más completa y la otra completa lo que falte; quedan las impresoras de las dos y todas las piezas. Lee la salida: lista las carpetas de piezas que hay que mover y avisa si alguna está repetida.
3. **Mover las carpetas** de las piezas, `respaldos/`, `taller-3d/impresoras/` y `taller-3d/blender/` a `Taller 3D`, con el mismo nombre. Con terminal en la PC (`device_bash`), con `mv` y sin pisar nada que ya exista. Sin terminal Claude no puede mover: darle al usuario la lista para que las mueva él con el explorador de archivos (o, si usa Claude Code en esa PC, el pedido escrito para pegarle). Esperar su «listo» y comprobar con `device_list_dir` que cada pieza del catálogo unido tenga su carpeta en `Taller 3D`.
4. Recién entonces escribir en `Taller 3D/taller-3d/` los tres archivos unidos (procedimiento de escritura, con respaldo de los que hubiera), rehacer `panel.html` (skill `panel`) y republicar el panel al costado. Si cada taller tenía su panel al costado, queda el de la configuración que mandó; el otro lo borra el usuario si quiere.
5. Si está `taller3d-orca`, hacer la sonda (sección 1): si atiende la carpeta vieja, que corra de nuevo el instalador con la app cerrada del todo.
6. Decirle que de ahora en más todo se guarda en `Taller 3D` y que la carpeta vieja puede borrarla (o desconectarla de la app) cuando vea que no falta nada.

## 4. Configuración inicial

1. **Aviso de uso:** si `config.json` no tiene `aceptacion`, mostrar un resumen de `DISCLAIMER.md` (puntos 1-8 en una línea cada uno) y pedir que escriba ACEPTO. Guardar fecha, versión del plugin y texto.
2. **Impresora:** ver todas las impresoras de Orca, no solo las que tienen copia de usuario (`references/impresoras.md`, sección 1), preguntar en cuál quiere trabajar y prepararla con `/impresoras`: datos investigados en internet, tipo de cama, perfiles propios que ya tenga y perfiles AUTO óptimos. Las demás se preparan cuando las elija.
3. **Costos (opcional, se puede hacer después):** para que el costo de cada pieza sea real (`references/costos.md` de la skill `impresion-3d`). Pedir de a uno y guardar cada respuesta:
   - **La boleta de luz:** "Mandame una foto o el PDF de tu última boleta de luz". Leer los números de la tarifa y correr `costos.py luz` (solo se guardan esos números, nada personal).
   - **La impresora:** cuánto la pagó. El consumo no se pregunta: lo busca `/impresoras` al prepararla (si falta, buscarlo ahora: `references/costos.md` de la skill `impresion-3d`, «El consumo de la impresora») y se cuenta en una línea de dónde salió. Si tiene un medidor de enchufe y quiere el real, que lo mida en una impresión.
   - **El filamento:** cuánto paga el kilo de cada material que usa.
   - **Su tiempo:** cuánto vale su hora y cuántos minutos le dedica a cada pieza (preparar, sacar soportes, embalar). Fallas: 10 % si no sabe.
   - **Cómo factura (si vende):** monotributo, responsable inscripto, exento o sin facturar, y si paga Ingresos Brutos (qué %; 0 si va incluido en el monotributo). Si es responsable inscripto, de qué compras descuenta el IVA (las que compra con factura A: material, máquina, embalaje; la luz solo si la boleta está a nombre del negocio). Guardarlo con `costos.py impuestos` (`references/costos.md`, «Impuestos de la venta»). No dar consejo impositivo: si duda, que lo confirme con su contador.
4. **Tienda (opcional):** plataforma (WooCommerce, Tiendanube, Shopify, Mercado Libre u otra), URL, dónde vende (`tienda.canales`: la comisión de cada canal; la de Mercado Libre, buscarla en la web para su categoría), su margen habitual **sobre el precio** (explicar que un recargo del 50 % es un margen del 33 % y que «el doble del costo» es un recargo del 100 %, o sea 50 % de margen; guardarlo con `costos.py margen --margen <m>` o `--recargo <r>`; en cada producto se vuelve a elegir), embalaje, redondeo y demora. Opcional: margen por escalones según el costo de la pieza y precio mínimo por pieza (`costos.py margen --escalones … --minimo-pieza …`, `references/costos.md`). Sin contraseñas.
   Al final, `costos.py estado --config config.json` muestra lo que quedó listo y lo que falta: decirlo en pocas líneas, con la frase para completarlo después.
5. **Piezas desde una foto (opcional):** preguntar si tiene cuenta en Hunyuan 3D (https://3d.hunyuan.tencent.com, gratis, con puntos por día) y si usa Gemini o Flow para generar imágenes. Preguntar también si quiere que los textos de venta de sus publicaciones los escriba su Gemini gratis (con su cuenta de Google, en el navegador; Claude los revisa) o Claude. Guardarlo en `generadores_ia` (`textos`: `gemini` o `claude`). Si tiene Hunyuan, decirle que deje la sesión abierta en Chrome y que apague en Chrome «Preguntar dónde guardar cada archivo» (Configuración → Descargas), así los modelos se bajan solos (`references/foto-a-3d.md`).
6. Escribir `config.json` (formato en `references/configuracion.md` de la skill `impresion-3d`) con el procedimiento de escritura y crear `historial.csv` con encabezado. Si ya existe, completar solo lo que falte.

## 5. Pieza de prueba

1. Generar con `cad.py` un cubo de calibración de 20 × 20 × 20 mm con chaflán inferior.
2. Laminar con los perfiles de la impresora elegida: `AUTO proceso` y `AUTO filamento` creado con `--cama` de la configuración (como en `/pieza`).
3. Traer el G-code y correr `revisar_gcode.py --impresora <json> --cama-primera-capa <temperatura>`: tiene que salir APROBADO, con las temperaturas y la cama correctas.
4. Mostrar tiempo, gramos y costo (con `revisar_gcode.py … --config config.json`; si faltan datos, decir cuáles) y dejar todo en la carpeta de `catalogo.py carpeta --nombre "Cubo de prueba" --impresora "<impresora>"`, con el G-code con nombre y el proyecto `.3mf` como en `/pieza` (sección 5). Decir que abra el `.3mf` con doble clic para ver la pieza en Orca con todo elegido.
5. Armar el panel (skill `panel`) con el cubo y la caja "Tu taller". En claude.ai, ofrecer el panel al costado del chat (skill `panel`).
6. Cerrar con: qué quedó listo, qué falta (si algo), los comandos disponibles, que en la app llevan el prefijo del plugin (`/taller-3d:pieza`, `/taller-3d:diseno`, `/taller-3d:calibrar`, `/taller-3d:impresoras`, `/taller-3d:publicar`, `/taller-3d:panel`, `/taller-3d:restaurar`, `/taller-3d:ayuda`), y que también puede pedir todo con sus palabras, y cómo pedir una pieza con un ejemplo de `MANUAL.md`. Ofrecer dejar el manual en la carpeta de trabajo.
