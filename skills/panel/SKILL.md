---
name: panel
description: Muestra y mantiene el panel del taller (panel.html en la carpeta de trabajo), con cada idea y pieza, el paso en que está (idea, diseño, lista para imprimir, impresa, en la tienda), lo que sigue, para qué impresora es y sus archivos; también anota ideas para más adelante. Se usa cuando el usuario dice "mostrame el panel", "qué tengo pendiente", "en qué está cada pieza", "anotá esta idea", "mostrame el catálogo", "qué piezas hice", "dónde quedó el llavero" o "marcá esta pieza como impresa".
---

# /panel: tus ideas y piezas, y en qué paso está cada una

Cargar antes la skill `impresion-3d` y seguir sus reglas, sobre todo el procedimiento de escritura (sección 4). Script: `<raíz del plugin>/skills/impresion-3d/scripts/catalogo.py`.

El panel son dos archivos de la carpeta de trabajo:
- `taller-3d/catalogo.json`: el índice, una entrada por idea anotada (`ideas/AAAA-MM-DD_nombre`, sin carpeta en la PC) o por carpeta de `impresiones/` o `disenos/`.
- `panel.html`: la página que el usuario abre con doble clic. Arriba, cuántas ideas están pendientes, cuántas piezas en proceso y cuántas terminadas. Después, "Para hacer" (lo más avanzado primero) y las terminadas por mes. Cada tarjeta muestra el recorrido (Idea → Diseño → Lista para imprimir → Impresa → En la tienda), lo que sigue, la vista o la foto, la impresora, medidas, material, tiempo, gramos, costo, precio y enlaces a sus archivos. Tiene buscador y filtros (pendientes, en proceso, terminadas). Las imágenes se cargan de la carpeta de cada pieza: no hace falta traerlas.

Los pasos salen de lo que hay: una idea está pendiente; con modelo, diseñada; con G-code, lista para imprimir; marcada como impresa o con una foto de la pieza, impresa (terminada); con producto armado, en la tienda. Publicar es opcional: una pieza impresa ya está terminada.

## Al empezar

La skill `impresion-3d` (sección 3) pide decir en una línea lo pendiente al comienzo de cada conversación con el taller:
```bash
python3 -I catalogo.py resumen --catalogo catalogo.json --corto
```
("Tenés 2 ideas pendientes y 1 lista para imprimir. Todo está en panel.html, en tu carpeta de trabajo."). Si no hay nada pendiente, no decir nada.

## Mostrar el panel

1. Traer `taller-3d/catalogo.json` y contestar con `resumen` (en texto, con lo que sigue en cada una). Si pide ver la página, decir dónde está (`<trabajo>/panel.html`, doble clic; conviene guardarla como favorito del navegador). Claude no puede abrir ventanas en la PC sin terminal.
2. Si el usuario quiere seguir con algo, ofrecer el paso que corresponda: una idea o un diseño → `/pieza` (o `/diseno`); lista para imprimir → recordar el G-code y el `.3mf`; impresa → contar cómo salió o `/publicar`.

## Anotar una idea

Cuando el usuario cuenta algo que quiere hacer más adelante ("después quiero hacer un soporte para la tele", "anotá esta idea"), o deja un pedido para otro momento, ofrecer anotarla (si lo pidió, anotarla directamente):
```bash
python3 -I catalogo.py idea --catalogo catalogo.json --nombre "Soporte para la tele" \
  [--nota "para colgar el decodificador, 15 × 10 cm"] [--impresora "<nombre>"]
```
La nota guarda lo que ya se sabe (medidas, para qué es, material) para no volver a preguntarlo. Después, rehacer la página y escribir los dos archivos (abajo). Si la descarta, `quitar-idea --carpeta ideas/AAAA-MM-DD_nombre` (solo las ideas se sacan; las piezas tienen archivos).

**Cuando una idea se hace pieza** (`/pieza` o `/diseno` sobre una idea del panel): usar la nota como punto de partida y, al registrar la pieza, `agregar ... --de-idea ideas/AAAA-MM-DD_nombre`: la idea pasa a la pieza con su nombre y su nota.

## Armar o rehacer el panel

1. Ubicar la carpeta de trabajo (skill `impresion-3d`, sección 3).
2. Listar la carpeta de trabajo con `device_list_dir` y `recursive=true` y guardar la respuesta en `listado.json` (si se corta por cantidad, listar `impresiones` y `disenos` por separado y anteponer esa carpeta a cada nombre).
3. Traer `taller-3d/catalogo.json` si existe (anotar `mtimeMs`) y correr:
   ```bash
   python3 -I catalogo.py desde-listado --catalogo catalogo.json --listado listado.json
   ```
   Suma las piezas que faltan con nombre, impresora, fecha, archivos y paso deducidos de la carpeta, y no pisa los datos de las que ya estaban.
4. Para completar tiempo, gramos, costo y medidas de las piezas nuevas, traer sus `informe_gcode.json` e `informe_stl.json` (y `producto/producto.json` si hay), de a 50 archivos como máximo, y correr `agregar` por cada una (abajo). Si son muchas, preguntar antes si vale la pena: sin esos datos la página igual muestra la vista y los archivos.
5. Armar la página y escribir los dos archivos en la PC con el procedimiento de escritura:
   ```bash
   python3 -I catalogo.py html --catalogo catalogo.json --salida panel.html
   ```
   Commitear `catalogo.json` a `<trabajo>/taller-3d/catalogo.json` y `panel.html` a `<trabajo>/panel.html` (con `expectedMtimeMs` si ya existían; la página no necesita respaldo porque se rehace entera).
6. **Una sola vez:** si en la carpeta de trabajo hay un `catalogo.html` (de antes de la 0.1.13), reemplazarlo por un acceso al panel, para que el favorito o el acceso viejo sigan sirviendo: `catalogo.py redireccion --salida catalogo.html` y commitearlo con su `expectedMtimeMs`.
7. Decirle al usuario dónde quedó y un resumen de una o dos líneas (lo pendiente y la última pieza).

## Agregar o actualizar una pieza

Lo hacen solos `/pieza`, `/diseno` y `/publicar` al guardar. También a pedido ("marcá el llavero como impreso", "agregale una nota"):
```bash
python3 -I catalogo.py agregar --catalogo catalogo.json --carpeta impresiones/AAAA-MM-DD_nombre_impresora \
  --nombre "<nombre legible>" --impresora "<nombre de la impresora>" [--material PETG] [--color negro] \
  [--informe-gcode informe_gcode.json] [--informe-stl informe_stl.json] [--producto producto/producto.json] \
  [--archivos pieza.stl pieza.py vista.png informe.md nombre_impresora.gcode nombre_impresora.3mf] \
  [--estado disenada|laminada|impresa|en_tienda] [--de-idea ideas/AAAA-MM-DD_nombre] [--nota "..."] [--url-tienda https://...]
```
- `--carpeta` es relativa a la carpeta de trabajo; `--archivos`, relativos a la carpeta de la pieza.
- Las carpetas nuevas llevan la impresora al final (`impresiones/AAAA-MM-DD_nombre_impresora`, de `catalogo.py carpeta`). El nombre de la pieza se saca sin la impresora, que queda aparte en la tarjeta; las carpetas de antes de la 0.1.12 no la tienen.
- El paso sale de los informes y los archivos (con G-code: lista para imprimir; con producto: en la tienda). "Impresa" lo marca el usuario, o Claude cuando el usuario cuenta que la imprimió; queda aunque después se arme el producto.
- Si el usuario manda una foto de la pieza impresa, guardarla como `foto.jpg` (o `foto-2.jpg`, ...) en la carpeta de la pieza y sumarla a `--archivos`: la página muestra la foto real antes que la vista y la cuenta como impresa.
- Después de `agregar`, rehacer la página (`html`) y escribir los dos archivos (paso 5 de arriba).

## Consultar

Para "¿qué piezas hice?", "¿qué tengo pendiente?" o "¿dónde está el soporte?", traer `catalogo.json` y contestar con:
```bash
python3 -I catalogo.py resumen --catalogo catalogo.json [--buscar "router"]
```
Dar la carpeta de la pieza y lo que sigue, y ofrecer el paso que corresponda (`/pieza` para hacerla, reimprimirla o cambiar medidas; `/publicar` para venderla).

## Reglas

- El panel solo lee y enlaza archivos de la carpeta de trabajo; no mueve, renombra ni borra piezas. Solo se sacan ideas, y solo si el usuario las descarta.
- Los nombres y notas los escribe el usuario o Claude: el script los escapa en la página. Los enlaces a la tienda solo se aceptan con `http` o `https`.
- Si `catalogo.json` está roto, no pisarlo: avisar, guardar una copia en `respaldos/` y rehacerlo desde el listado (las ideas anotadas se pierden: avisarlo).
