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
| `/restaurar` | Volver atrás un perfil, ordenar perfiles de prueba, desinstalar |
| `/ayuda` | Cómo pedir una pieza, el circuito y los comandos (el manual de uso) |

Además, la skill `impresion-3d` responde cualquier duda de configuración: conoce los 1015 parámetros de OrcaSlicer 2.5.1 (en español), recetas por tipo de pieza, materiales, calibración, diagnóstico de fallas y los plugins de Orca que valen la pena.

## Cómo funciona

- Claude trabaja en su espacio y llega a tu PC por la app de escritorio: lamina con tu Orca (orca-mcp), modela con CAD por código (o Blender, opcional) y escribe solo en las carpetas que conectás.
- Si un plugin de Orca resuelve lo que pedís (un llavero, un cartel, un florero), te lo sugiere con sus riesgos. No instala nada.
- Después de cada laminado compara tu Orca con lo que conoce (parámetros nuevos o que ya no están) y una vez por mes revisa si salió una versión nueva o hay plugins útiles. Lo anota en tu carpeta de trabajo.
- Cada pieza queda en su carpeta: modelo editable (`pieza.py`), STL, vista previa, G-code, configuración usada e informe.
- Tus datos (impresoras, nombres de perfiles, precios, tienda) viven en `taller-3d/config.json` dentro de tu carpeta de trabajo, no en el plugin.
- Antes de cambiar algo, hace un respaldo y lo anota en el historial.
- Con el uso, `aprendizajes.md` guarda qué funcionó con tus materiales e impresoras.

## Instalación

1. **Sumá el plugin a Claude** (cualquiera de estas):
   - **Desde GitHub, con actualizaciones automáticas:** en claude.ai o en la app de escritorio, **Customize → Plugins → Add → Add marketplace**, escribí `noamix/Taller-3d-printaia` e instalá **taller-3d**.
   - **En Claude Code:**
     ```
     /plugin marketplace add noamix/Taller-3d-printaia
     /plugin install taller-3d@taller-3d
     ```
   - **Desde el archivo:** bajá `taller-3d.plugin` de [Releases](https://github.com/noamix/Taller-3d-printaia/releases) y subilo en **Customize → Plugins → Add → Upload plugin**. Las versiones nuevas las tenés que bajar de nuevo.
2. **Prepará la PC:** en Claude escribí `/instalar`. Te deja el instalador para Linux o Windows, que primero revisa que la PC alcance (procesador, memoria, placa de video, disco e internet) y qué tenés instalado, y saltea lo que ya está. Usa versiones fijas con verificación SHA-256, tiene modo prueba y desinstalador. Detalles en [INSTALACION.md](INSTALACION.md).

## Componentes

- `skills/impresion-3d/`: conocimiento, reglas de seguridad, scripts (`cad.py`, `revisar_stl.py`, `vista_previa.py`, `perfil_orca.py`, `revisar_gcode.py`, `producto_tienda.py`, `novedades_orca.py`), datos de impresoras y materiales, catálogo de parámetros de Orca, guía de plugins de Orca y pruebas (`scripts/tests/`).
- `skills/pieza`, `diseno`, `calibrar`, `impresoras`, `publicar`, `instalar`, `restaurar`, `ayuda`: flujos de trabajo.
- `MANUAL.md`: manual de uso.
- `hooks/`: bloqueos automáticos de seguridad.
- `instalador/`: instaladores y desinstaladores para Linux y Windows.

## Probado con

Ubuntu 24.04, OrcaSlicer 2.5.1, orca-mcp 0.1.0, Creality Ender-3 V3 Plus. El instalador de Windows se revisó con PowerShell 7 (sintaxis y funciones), pero todavía no se probó en una PC con Windows. macOS: instalación manual, sin probar.

## Versión

0.1.4. Cambios en [CHANGELOG.md](CHANGELOG.md).

## Licencia

GNU Affero General Public License, versión 3 ([LICENSE](LICENSE)): podés usarlo, cambiarlo y compartirlo; si distribuís una versión cambiada, tiene que ir con la misma licencia y con su código. El catálogo de parámetros sale de OrcaSlicer, que tiene la misma licencia: ver [AVISOS-DE-TERCEROS.md](AVISOS-DE-TERCEROS.md).

## Contacto

Leo, el autor. Errores y pedidos: [Issues](https://github.com/noamix/Taller-3d-printaia/issues). Problemas de seguridad, en privado: ver [SECURITY.md](SECURITY.md).
