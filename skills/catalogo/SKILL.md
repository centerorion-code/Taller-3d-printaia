---
name: catalogo
description: Arma, actualiza y consulta el catálogo de diseños e impresiones del taller (catalogo.html en la carpeta de trabajo, con la vista de cada pieza, sus datos y sus archivos). Se usa cuando el usuario dice "mostrame el catálogo", "armá el catálogo", "qué piezas hice", "buscá el soporte del router", "dónde quedó el llavero" o "marcá esta pieza como impresa".
---

# /catalogo: todas las piezas en una página

Cargar antes la skill `impresion-3d` y seguir sus reglas, sobre todo el procedimiento de escritura (sección 4). Script: `<raíz del plugin>/skills/impresion-3d/scripts/catalogo.py`.

El catálogo son dos archivos de la carpeta de trabajo:
- `taller-3d/catalogo.json`: el índice, una entrada por carpeta de `impresiones/` o `disenos/`.
- `catalogo.html`: la página que el usuario abre con el navegador desde la carpeta de trabajo. Muestra la vista o la foto de cada pieza, medidas, material, tiempo, gramos, costo, precio, estado y enlaces a sus archivos, ordenadas por mes, con buscador y filtros. Las imágenes se cargan de la carpeta de cada pieza: no hace falta traerlas.

## Armar o rehacer el catálogo

1. Ubicar la carpeta de trabajo (skill `impresion-3d`, sección 3).
2. Listar la carpeta de trabajo con `device_list_dir` y `recursive=true` y guardar la respuesta en `listado.json` (si se corta por cantidad, listar `impresiones` y `disenos` por separado y anteponer esa carpeta a cada nombre).
3. Traer `taller-3d/catalogo.json` si existe (anotar `mtimeMs`) y correr:
   ```bash
   python3 -I catalogo.py desde-listado --catalogo catalogo.json --listado listado.json
   ```
   Suma las piezas que faltan con nombre, fecha, archivos y estado deducidos de la carpeta, y no pisa los datos de las que ya estaban.
4. Para completar tiempo, gramos, costo y medidas de las piezas nuevas, traer sus `informe_gcode.json` e `informe_stl.json` (y `producto/producto.json` si hay), de a 50 archivos como máximo, y correr `agregar` por cada una (abajo). Si son muchas, preguntar antes si vale la pena: sin esos datos la página igual muestra la vista y los archivos.
5. Armar la página y escribir los dos archivos en la PC con el procedimiento de escritura:
   ```bash
   python3 -I catalogo.py html --catalogo catalogo.json --salida catalogo.html --titulo "Mis piezas 3D"
   ```
   Commitear `catalogo.json` a `<trabajo>/taller-3d/catalogo.json` y `catalogo.html` a `<trabajo>/catalogo.html` (con `expectedMtimeMs` si ya existían; la página no necesita respaldo porque se rehace entera).
6. Decirle al usuario dónde quedó (`<trabajo>/catalogo.html`, que lo abra con doble clic) y un resumen de una o dos líneas: cuántas piezas, la última y si alguna quedó sin datos.

## Agregar o actualizar una pieza

Lo hacen solos `/pieza`, `/diseno` y `/publicar` al guardar. También a pedido ("marcá el llavero como impreso", "agregale una nota"):
```bash
python3 -I catalogo.py agregar --catalogo catalogo.json --carpeta impresiones/AAAA-MM-DD_nombre_impresora \
  --nombre "<nombre legible>" --impresora "<nombre de la impresora>" [--material PETG] [--color negro] \
  [--informe-gcode informe_gcode.json] [--informe-stl informe_stl.json] [--producto producto/producto.json] \
  [--archivos pieza.stl pieza.py vista.png informe.md nombre_impresora.gcode nombre_impresora.3mf] \
  [--estado disenada|laminada|impresa|en_tienda] [--nota "..."] [--url-tienda https://...]
```
- `--carpeta` es relativa a la carpeta de trabajo; `--archivos`, relativos a la carpeta de la pieza.
- Las carpetas nuevas llevan la impresora al final (`impresiones/AAAA-MM-DD_nombre_impresora`, de `catalogo.py carpeta`). El nombre de la pieza se saca sin la impresora, que queda aparte en la tarjeta; las carpetas de antes de la 0.1.12 no la tienen.
- El estado sale solo de los informes (con G-code: lista para imprimir; con producto: en la tienda como borrador). "Impresa" lo marca el usuario, o Claude cuando el usuario cuenta que la imprimió.
- Si el usuario manda una foto de la pieza impresa, guardarla como `foto.jpg` (o `foto-2.jpg`, ...) en la carpeta de la pieza y sumarla a `--archivos`: la página muestra la foto real antes que la vista.
- Después de `agregar`, rehacer la página (`html`) y escribir los dos archivos (paso 5 de arriba).

## Consultar

Para "¿qué piezas hice?" o "¿dónde está el soporte?", traer `catalogo.json` y contestar con:
```bash
python3 -I catalogo.py resumen --catalogo catalogo.json [--buscar "router"]
```
Dar la ruta de la carpeta de la pieza y, si quiere seguir con ella, ofrecer el paso que corresponda (`/pieza` para reimprimir o cambiar medidas, `/publicar` para venderla).

## Reglas

- El catálogo solo lee y enlaza archivos de la carpeta de trabajo; no mueve, renombra ni borra piezas.
- Los nombres y notas los escribe el usuario o Claude: el script los escapa en la página. Los enlaces a la tienda solo se aceptan con `http` o `https`.
- Si `catalogo.json` está roto, no pisarlo: avisar, guardar una copia en `respaldos/` y rehacerlo desde el listado.
