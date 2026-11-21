# taller-3d

Plugin para Claude que arma un taller de impresión 3D con OrcaSlicer: diseña piezas, elige la mejor configuración según para qué es la pieza, lamina, revisa el G-code por seguridad, calcula el costo, calibra filamentos y prepara la publicación para tu tienda.

**Nunca arranca una impresión: el G-code lo imprimís vos.** Leé el [aviso de uso](DISCLAIMER.md) y la [política de seguridad](SECURITY.md).

**Para empezar, leé el [manual de uso](MANUAL.md):** cómo pedirle una pieza a Claude, con ejemplos, y el circuito completo de la pieza.

## Qué podés pedir

| Comando | Para qué |
|---|---|
| `/pieza` | "Haceme un soporte para…", "imprimime esto", una foto o medidas → modelo, configuración, laminado, revisión, costo y, si querés, la publicación en paralelo |
| `/diseno` | Solo el modelo 3D paramétrico (STL, archivo editable y vista), sin laminar; sirve sin la PC conectada |
| `/calibrar` | Calibrar un filamento con los tests de Orca, leyendo los resultados en fotos |
| `/impresoras` | Agregar o revisar impresoras (límites, perfiles, cama) y ver qué perfiles sobran |
| `/publicar` | Armar el producto con precio por costo y margen y cargarlo como borrador en tu tienda |
| `/instalar` | Instalar o revisar que todo ande (saltea lo que ya está) y hacer una pieza de prueba |
| `/catalogo` | Ver todas tus piezas en una página (`catalogo.html`) con su vista, datos y archivos, buscarlas y marcarlas como impresas |
| `/restaurar` | Volver atrás un perfil, ordenar perfiles de prueba, desinstalar |
| `/ayuda` | Cómo pedir una pieza, el circuito y los comandos (el manual de uso) |

Además, la skill `impresion-3d` responde cualquier duda de configuración: conoce los 1015 parámetros de OrcaSlicer 2.5.1 (en español), recetas por tipo de pieza, materiales, calibración, diagnóstico de fallas y los plugins de Orca que valen la pena.

## Cómo funciona

- Claude trabaja en su espacio y llega a tu PC por la app de escritorio: lamina con tu Orca (orca-mcp), modela con CAD por código (o Blender, opcional) y escribe solo en las carpetas que conectás.
- Trabaja con las impresoras que tenés en Orca. Si tenés varias, te pregunta en cuál querés trabajar; la primera vez que usás una, investiga en internet sus datos oficiales (temperaturas máximas, volumen, perfiles de Orca) y la configura óptima. El plugin no trae impresoras cargadas: cada una queda preparada en tu carpeta de trabajo.
- Si una pieza no entra en la impresora elegida, te dice en cuál de tus otras impresoras entra.
- Si un plugin de Orca resuelve lo que pedís (un llavero, un cartel, un florero), te lo sugiere con sus riesgos. No instala nada.
- Después de cada laminado compara tu Orca con lo que conoce (parámetros nuevos o que ya no están) y una vez por mes revisa si salió una versión nueva o hay plugins útiles. Lo anota en tu carpeta de trabajo.
- Cada pieza queda en su carpeta: modelo editable (`pieza.py`), STL, vista previa, G-code, configuración usada e informe.
- Tus datos (impresoras, nombres de perfiles, precios, tienda) viven en `taller-3d/config.json` dentro de tu carpeta de trabajo, no en el plugin. Los datos de cada impresora, en `taller-3d/impresoras/`.
- Antes de cambiar algo, hace un respaldo y lo anota en el historial.
- Con el uso, `aprendizajes.md` guarda qué funcionó con tus materiales e impresoras.

## Instalación

Por ahora el taller se instala desde este repositorio de GitHub. Se hace en **Claude Desktop** (la app de escritorio, https://claude.ai/download), desde su menú **Plugins**: no se hace pidiéndoselo a Claude en el chat. Más adelante va a estar también en el directorio de plugins de Anthropic, y esta sección va a explicar cómo sumarlo desde ahí.

1. **Sumá el plugin a Claude desde GitHub.** Usá solo esta dirección: una copia (fork) puede traer cambios que nadie revisó.
   - **En Claude Desktop:** en el menú de la app (no en el chat), andá a **Plugins › Agregar › Agregar marketplace › Agregar desde un repositorio** (en inglés: *Customize → Plugins → Add marketplace*), pegá `noamix/Taller-3d-printaia` (o `https://github.com/noamix/Taller-3d-printaia`), tocá **Sincronizar** e instalá **taller-3d**. Para recibir las versiones nuevas, activá la sincronización automática del marketplace (*Sync automatically*) o buscá actualizaciones (*Check for updates*) cuando quieras.
   - **En Claude Code:**
     ```
     /plugin marketplace add noamix/Taller-3d-printaia
     /plugin install taller-3d@taller-3d
     ```
     Claude Code no actualiza solo los marketplaces que no son de Anthropic: activá **Enable auto-update** en `/plugin` → **Marketplaces**, o actualizalo a mano con `claude plugin marketplace update taller-3d` y `claude plugin update taller-3d@taller-3d`, y reiniciá Claude Code.
   - Si alguien te pasó el archivo `taller-3d.plugin`, también lo podés subir con **Plugins › Agregar › Subir plugin**, pero así no se actualiza: conviene sumarlo desde GitHub.
2. **Prepará la PC:** con el plugin instalado, escribí `/instalar` en una conversación de Claude Desktop. Te deja el instalador para Linux o Windows, que primero revisa que la PC alcance (procesador, memoria, placa de video, disco e internet) y qué tenés instalado, y saltea lo que ya está. Usa versiones fijas con verificación SHA-256, tiene modo prueba y desinstalador. Detalles en [INSTALACION.md](INSTALACION.md).

## Qué corre, qué manda y qué baja

- **En el espacio de Claude:** los scripts de Python de `skills/impresion-3d/scripts/` diseñan las piezas (`cad.py`), revisan el STL y el G-code, validan los perfiles de Orca, calculan costos y precios, comparan tu Orca con lo que conoce el taller y arman el catálogo. Para el CAD y las imágenes instala `manifold3d`, `numpy`, `matplotlib` y `Pillow` con pip, ahí mismo.
- **En tu PC, los bloqueos automáticos** (`hooks/guardia.py`, en Cowork y Claude Code): corren con Python antes de que Claude escriba un archivo o use la terminal, leen solo ese archivo o ese comando y bloquean si no pasan la revisión. No mandan nada a ningún lado.
- **Qué toca en tu PC:** solo las carpetas que conectás (la de trabajo y las de perfiles de usuario de Orca), con respaldo antes de cambiar algo. Lamina con tu OrcaSlicer a través de orca-mcp, que se instala aparte; no viene en el plugin. Blender (por su MCP) es opcional.
- **Qué baja el instalador**, solo si lo corrés vos: OrcaSlicer 2.5.1 desde el GitHub de OrcaSlicer y uv 0.13.9 desde el GitHub de Astral (solo Windows), los dos con huella SHA-256 fija; orca-mcp 0.1.0 y sus dependencias desde PyPI; en Linux, si aceptás, paquetes del sistema con apt (fuse3, bibliotecas de Orca, pipx, xvfb). Agrega orca-mcp a la configuración de la app de Claude, con respaldo, y en Windows mueve la carpeta de datos de Orca fuera de AppData.
- **Qué manda a internet:** nada por su cuenta y sin telemetría. Lo único que sale es la publicación de un producto en **tu** tienda (WooCommerce, Tiendanube, Shopify o Mercado Libre), cuando lo pedís y siempre como borrador, por la conexión o el navegador que uses vos. Claude también busca en la web cuando revisa si hay versiones o plugins nuevos de Orca.

## Componentes

- `skills/impresion-3d/`: conocimiento, reglas de seguridad, scripts (`cad.py`, `revisar_stl.py`, `vista_previa.py`, `perfil_orca.py`, `revisar_gcode.py`, `impresora.py`, `producto_tienda.py`, `novedades_orca.py`, `catalogo.py`), datos de materiales, catálogo de parámetros de Orca, guía de plugins de Orca y pruebas (`scripts/tests/`).
- `skills/pieza`, `diseno`, `calibrar`, `impresoras`, `publicar`, `catalogo`, `instalar`, `restaurar`, `ayuda`: flujos de trabajo.
- `MANUAL.md`: manual de uso.
- `hooks/`: bloqueos automáticos de seguridad.
- `instalador/`: instaladores y desinstaladores para Linux y Windows.

## Probado con

Ubuntu 24.04, OrcaSlicer 2.5.1, orca-mcp 0.1.0, Creality Ender-3 V3 Plus. El instalador de Windows se revisó con PowerShell 7 (sintaxis y funciones), pero todavía no se probó en una PC con Windows. macOS: instalación manual, sin probar.

## Versión

0.1.7. Cambios en [CHANGELOG.md](CHANGELOG.md).

## Licencia

GNU Affero General Public License, versión 3 ([LICENSE](LICENSE)): podés usarlo, cambiarlo y compartirlo; si distribuís una versión cambiada, tiene que ir con la misma licencia y con su código. El catálogo de parámetros sale de OrcaSlicer, que tiene la misma licencia: ver [AVISOS-DE-TERCEROS.md](AVISOS-DE-TERCEROS.md).

## Contacto

Leo, el autor. Errores y pedidos: [Issues](https://github.com/noamix/Taller-3d-printaia/issues). Problemas de seguridad, en privado: ver [SECURITY.md](SECURITY.md).
