# Con qué modelar: código, Blender o un modelo que ya existe

La herramienta se elige antes de modelar, por cómo se describe la pieza, no por cuál es más cómoda. El código (`cad.py`) es más rápido y exacto, y por eso tienta usarlo para todo; con algo que se define por su aspecto sale un muñeco de bloques que igual pasa la revisión técnica (malla cerrada, medidas, voladizos).

## La regla

| Cómo se describe la pieza | Con qué | Ejemplos |
|---|---|---|
| Con medidas: largos, diámetros, ángulos, agujeros, tornillos, encastres | Código: `cad.py` (`references/cad.md`) | soporte, caja, tapa, adaptador, gancho, separador, plantilla, bisagra |
| Por cómo se ve: una figura, un animal, una cara, un mango que siga la mano, una forma suave o esculpida, un logo, texto | Blender por código (abajo) o un modelo que ya exista | figura, maceta con forma, llavero con un personaje propio, cartel con letras |
| Las dos cosas | Cada parte con su herramienta, y se unen con `importar_stl` y `unir` de `cad.py` | soporte de celular con una figura arriba, caja con la tapa decorada, base con un nombre |
| Con la foto de algo que existe y hay que copiar, o algo que se pide por cómo se ve y Blender por código no hace bien | Un generador de modelos por IA (Hunyuan 3D, con la cuenta del usuario): `references/foto-a-3d.md`. Sin cuenta, Blender por código o un modelo que ya exista | una máscara, una figura, una escultura, un animal con detalle |
| Un objeto que resuelve un plugin de Orca | Ofrecer el plugin (`references/plugins-orca.md`) | llavero o cartel con nombre, florero, Gridfinity, litofanía |

Señales de que no es para código: lleva texto; tiene curvas libres que no son arcos ni piezas de revolución; pasa suave de una sección a otra; tiene todas las aristas redondeadas; tiene relieve o textura; el usuario lo describe con adjetivos ("redondito", "orgánico", "como un dinosaurio") o con la foto de algo que no es una pieza mecánica.

`cad.py` hace cajas con las aristas verticales redondeadas, cilindros, conos, esferas, tubos, prismas de un polígono, piezas de revolución, hexágonos, agujeros para tornillos, tuercas e insertos, chaflán en la base, uniones, restas e intersecciones. No hace texto, curvas libres, transiciones entre secciones distintas, barridos a lo largo de una curva, redondeos de aristas en cualquier dirección ni escultura.

## No aproximar con formas simples

No armar con esferas, conos y cajas algo que se define por su aspecto (un gato de esferas, una cara de cilindros) ni mostrarlo como si estuviera bien. Si a mitad de camino el código no alcanza, parar, decirlo en una línea ("con código queda como un muñeco de bloques: lo hago en Blender") y cambiar de herramienta.

## Antes de modelar algo conocido, ver si ya existe

Para objetos comunes o reconocibles (una figura típica, un organizador conocido, un repuesto de un producto popular), buscar en Printables, MakerWorld y Thingiverse antes de modelar. Ofrecer hasta tres, con enlace, autor y licencia, junto con la opción de hacerlo a medida (AskUserQuestion).

- Si la pieza es para vender, sirven solo las que permiten uso comercial. Avisar con las otras (CC BY-NC o sin licencia clara), como en `/publicar`.
- No bajar archivos con la terminal ni con scripts: el usuario lo baja a su carpeta de trabajo (o Claude con el navegador, pidiendo permiso para la descarga) y se sigue desde la revisión del STL.
- Personajes, mascotas de marcas y logos ajenos no se modelan, tampoco cambiando la pose o el estilo: ofrecer un diseño propio. Un modelo bajado de un personaje no se puede vender aunque su licencia diga comercial, porque el personaje tiene dueño.

## Blender por código

Claude modela escribiendo código, no a mano. Sale bien lo que se arma con:

- bolas que se funden (metaballs), para cuerpos y figuras simples;
- curvas con espesor (`bevel`) y piezas de revolución, para formas suaves;
- el modificador Skin sobre un esqueleto de aristas, para patas, ramas o asas;
- subdivisión (Subdivision Surface), para suavizar una forma de bloques;
- texto (objeto Text con `extrude`), para letras en relieve, con la fuente que trae Blender u otra libre;
- desplazamiento con una textura, para relieves.

**Dónde:** en el espacio de Claude, con `bpy` (el mismo de las fotos de producto: `pip install --break-system-packages bpy`), o en el Blender de la PC (MCP) si el usuario quiere abrir el modelo ahí. En el espacio de Claude conviene trabajar con los datos y no con `bpy.ops`: cada objeto, con sus modificadores, pasa a malla con `bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))`, y el STL se escribe a mano desde `loop_triangles`.

**Medidas y malla:** 1 unidad de Blender = 1 mm (`scene.unit_settings.scale_length = 0.001`). Al final, cerrar la malla con Remesh en modo Voxel (0,2 mm para texto; 0,4 a 0,6 mm para figuras) y escribir el STL. Las bolas tienen que fundirse de verdad: una cabeza demasiado lejos del cuerpo queda flotando (la revisión la rechaza).

**Archivos:** el script se guarda como `modelo.py`, con las medidas que importan arriba, como `pieza.py`, para poder cambiarlas y regenerar. Si sirve, también el `.blend`.

**Piezas mixtas:** la parte funcional va en `pieza.py` con `cad.py`, y la decorativa en `modelo.py`. En `pieza.py`: `figura = importar_stl("figura.stl")`, ubicarla con `mover`, hundida unos 0,5 mm en la base para que se unan, y `unir(base, figura)`.

Para algo realista (una persona, un animal con detalle, una escultura), ni el código ni Blender por código alcanzan: ofrecer un modelo existente o generarlo por IA desde una foto o, si no hay foto, desde una imagen que el usuario apruebe antes (`references/foto-a-3d.md`).

**Lo generado y lo diseñado juntos** (una máscara de Hunyuan con un soporte para la mesa): primero lo generado, escalado y engrosado; después lo demás, medido sobre su STL, con el encastre de `hueco_para` de `cad.py`. El estilo de lo diseñado decide la herramienta: geométrico (escalones, grecas, planos) por código; orgánico o con curvas libres, en Blender. Detalle en `references/foto-a-3d.md`, sección 5.

**Plantilla de `modelo.py`** (probada con `bpy` 5.3: un pato con bolas que se funden y un texto en relieve):

```python
import struct
from pathlib import Path

import bpy
import numpy as np

# Medidas que importan (mm)
TEXTO, ALTO_LETRA, RELIEVE = "LEO", 10, 2

bpy.ops.wm.read_factory_settings(use_empty=True)
escena = bpy.context.scene
escena.unit_settings.scale_length = 0.001                  # 1 unidad = 1 mm


def a_malla(obj, voxel=None):                              # objeto con sus modificadores → malla cerrada
    if voxel:
        if obj.type != "MESH":
            obj = bpy.data.objects.new(obj.name + "_m", a_malla(obj))
            escena.collection.objects.link(obj)
        mod = obj.modifiers.new("cerrar", "REMESH")
        mod.mode, mod.voxel_size = "VOXEL", voxel
    return bpy.data.meshes.new_from_object(obj.evaluated_get(bpy.context.evaluated_depsgraph_get()))


def escribir_stl(me, ruta):
    me.calc_loop_triangles()
    v = np.array([x.co[:] for x in me.vertices])
    t = np.array([x.vertices[:] for x in me.loop_triangles])
    tri = v[t]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    reg = np.zeros(len(tri), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    reg["n"], reg["v"] = n, tri
    Path(ruta).write_bytes(b"taller-3d".ljust(80) + struct.pack("<I", len(tri)) + reg.tobytes())


mb = bpy.data.metaballs.new("pato")
mb.resolution = mb.render_resolution = 0.8
pato = bpy.data.objects.new("pato", mb)
escena.collection.objects.link(pato)
for tipo, co, r, tam in [("ELLIPSOID", (0, 0, 14), 16, (1.25, 0.85, 0.7)),     # cuerpo
                         ("BALL", (9, 0, 24), 10, None),                        # cabeza: cerca, para que se funda
                         ("ELLIPSOID", (19, 0, 23), 6, (1.3, 0.7, 0.35))]:      # pico
    e = mb.elements.new(type=tipo)
    e.co, e.radius = co, r
    if tam:
        e.size_x, e.size_y, e.size_z = tam
escribir_stl(a_malla(pato, voxel=0.6), "figura.stl")

cu = bpy.data.curves.new("texto", type="FONT")
cu.body, cu.size, cu.extrude, cu.align_x = TEXTO, ALTO_LETRA, RELIEVE / 2, "CENTER"
texto = bpy.data.objects.new("texto", cu)
escena.collection.objects.link(texto)
escribir_stl(a_malla(texto, voxel=0.2), "texto.stl")
```

Después, en `pieza.py`: `importar_stl("figura.stl")` e `importar_stl("texto.stl")`, ubicarlas con `mover` (el texto queda centrado en Z = 0: subirlo para que asome sobre la base) y `unir` con la base. Revisar dónde quedó cada parte: un texto metido entero adentro de la base no se ve, y la revisión del STL no lo nota.

## Revisar y mostrar

1. `revisar_stl.py`: además de la malla y las medidas, mira las partes separadas. Una parte suelta en el aire es RECHAZO (pasa con bolas que no se llegaron a fundir); una que toca la pieza sin estar unida es advertencia: unirla. También avisa si la pieza es una cáscara fina (lo típico de los modelos de IA): engrosarla con `engrosar_stl.py`.
2. Piezas funcionales: `vista_previa.py` (cuatro vistas con medidas).
3. Decorativas o mixtas: además, una foto renderizada, porque las cuatro vistas no alcanzan para juzgar cómo se ve:
   ```bash
   pip install --break-system-packages bpy pillow          # si no está: unos 400 MB, una vez por conversación
   python3 -I render_producto.py --stl pieza.stl --salida <carpeta>/producto --tomas tienda --tam 800 \
     --muestras 16 [--color "<color>"] [--material <m>]
   ```
   Tarda unos 40 segundos y deja `producto/producto-2-tienda.jpg`; `/publicar` después la rehace en alta. Si no se puede instalar Blender, `vista_previa.py pieza.stl foto.png --producto --color "<color>"`.
4. Antes de mostrarla, mirarla (leer la imagen): ¿se reconoce lo pedido sin que lo digan? ¿Coincide con la foto o el dibujo que mandó el usuario? ¿Falta algo, como un texto que quedó adentro de la base? Si no cierra, corregir o cambiar de herramienta antes de mostrarla. Al mostrarla, decir qué es aproximado ("las orejas son simplificadas").
