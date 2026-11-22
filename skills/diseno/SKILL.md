---
name: diseno
description: Diseña un modelo 3D paramétrico y entrega el STL, el archivo editable con sus medidas y una vista, sin laminar ni usar Orca. Se usa cuando el usuario pide solo el diseño o el archivo ("diseñame", "haceme el modelo 3D", "necesito el STL", "un diseño paramétrico", "lo imprimo en otro lado", "es para un servicio de impresión", "no hace falta laminar", "solo el archivo") o cuando la PC no está conectada.
---

# /diseno: solo el modelo, sin laminar

Cargar antes la skill `impresion-3d` (reglas y `references/cad.md`). Scripts: `<raíz del plugin>/skills/impresion-3d/scripts/`.

## ¿/diseno o /pieza?

| El pedido dice o da a entender | Ir a |
|---|---|
| "el diseño", "el modelo", "el STL", "el archivo", "paramétrico", "lo imprimo en otro lado, en otra impresora o en un servicio", "no hace falta laminar", "sin Orca", o la PC no está conectada | `/diseno` |
| "imprimime", "dejalo listo para imprimir", "laminalo", "el G-code", "¿cuánto tarda o cuánto gasta?", o nombra su impresora | `/pieza` |
| "publicalo", "subilo a la tienda" | `/pieza` y después `/publicar` |
| No queda claro | Preguntar una sola vez: "¿Querés solo el modelo (STL y archivo editable) o también dejarlo listo para imprimir en tu impresora?" |

Si a mitad de `/diseno` pide imprimirla, seguir con `/pieza` desde la configuración (sección 3), con este mismo modelo.

## 1. Entender la pieza

- Para qué es, medidas críticas (con calibre si es un encastre), material previsto si lo sabe (cambia holguras y espesores) y si quiere variantes. **No inventar medidas.**
- Preguntar qué medidas quiere poder cambiar después: esos son los parámetros (por ejemplo, largo, diámetro del tornillo, espesor de pared, cantidad de divisiones).
- Si es un objeto que resuelve un generador de Orca (llavero, cartel, florero, Gridfinity), mencionarlo en una línea como alternativa (`references/plugins-orca.md`) y seguir con el diseño propio, que es lo que pidió.
- Si es algo conocido (una figura típica, un repuesto de un producto popular), ver antes si ya existe un modelo y ofrecerlo con su licencia (`references/modelado.md`).

## 2. Modelo

**Con qué modelar** (`references/modelado.md`), antes de empezar y por cómo se describe la pieza: con medidas, `pieza.py` con `cad.py` (abajo); por cómo se ve (figura, forma suave, logo, texto), Blender por código (`modelo.py`, con las medidas que importan arriba) o un modelo que ya exista; si es mixta, cada parte con su herramienta, unidas en `pieza.py` con `importar_stl` y `unir`; para copiar algo de una foto (o algo que Blender por código no hace bien), generarlo por IA desde la foto o desde una imagen aprobada (`references/foto-a-3d.md`). Nunca aproximar con formas simples algo que se define por su aspecto.

1. Carpeta: `python3 -I catalogo.py carpeta --tipo diseno --nombre "<nombre>"` → `/mnt/user-data/outputs/taller-3d/<carpeta>/` (`disenos/AAAA-MM-DD_nombre`). Si se diseña para una impresora puntual (la nombró o se revisó contra la suya), sumar `--impresora "<nombre>"`: queda al final del nombre.
2. `pieza.py` con `cad.py` según `references/cad.md`: **todos los parámetros arriba**, con nombre claro y un comentario con unidad y rango razonable; el modelo se calcula a partir de ellos, sin números sueltos en el cuerpo. Holguras con `holgura()` o de `aprendizajes.md`.
3. Correrlo para generar `pieza.stl`.
4. Revisar: `revisar_stl.py pieza.stl --impresora ninguna --esperado <AxBxC> [--material <m>] --json informe_stl.json` (malla cerrada, medidas, apoyo y voladizos). Si el usuario dijo en qué impresora la va a imprimir y está preparada en el taller, usar sus datos (`--impresora <json>`) para revisar también que entre en la cama, y con `--otras <carpeta taller-3d/impresoras>` el informe dice en cuál de sus otras impresoras entra si en esa no. RECHAZADO → corregir.
5. `vista_previa.py pieza.stl vista.png --titulo "<nombre>"`; si es decorativa o mixta, también la foto renderizada (`references/modelado.md`, «Revisar y mostrar»). Mirarlas antes: si no se reconoce lo pedido o falta algo, corregir. Mostrarlas, decir qué es aproximado y esperar su OK si es un diseño nuevo.
6. Variantes (por ejemplo, tres tamaños): un STL por variante cambiando solo los parámetros.

## 3. Entregar

- Archivos: `pieza.py` (editable), `pieza.stl` (uno por variante), `vista.png` y `parametros.md`. Si se hizo en Blender, `modelo.py` (y el `.blend` si sirve) y la foto. Si se generó por IA, la foto, el original en `hunyuan/` y el STL escalado y engrosado.
- `parametros.md`: tabla de parámetros (nombre, valor, unidad, qué cambia), cómo regenerar (`python3 pieza.py`, con `cad.py` al lado) y que para cambiar algo alcanza con pedirlo ("hacelo 5 mm más alto").
- Recomendaciones de impresión en 3 a 5 líneas: orientación, material sugerido, si lleva soportes. Sin laminar.
- Mandar los archivos con `SendUserFile`. Si la PC está conectada y hay carpeta de trabajo, dejarlos también en `<trabajo>/<carpeta>/` con el procedimiento de escritura (y dar el enlace `computer://` a la carpeta, skill `impresion-3d`, sección 3), registrar en `historial.csv` y actualizar el panel (skill `panel`; con `--de-idea` si salió de una idea anotada) con `informe_stl.json` y los archivos.
- Ofrecer el paso siguiente: dejarla lista para imprimir (`/pieza`) o armar la publicación (`/publicar`, con fotos de producto renderizadas hasta tener la foto real).

## Reglas

- Sin la PC conectada se puede hacer todo `/diseno`: no hace falta Orca. El aviso de uso (regla 8) se pide antes de escribir en la PC.
- Usos críticos (regla 9): avisar igual que en `/pieza`.
- Si el usuario trae un modelo ajeno para modificar, preguntar de dónde es y respetar su licencia.
