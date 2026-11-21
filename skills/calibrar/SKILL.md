---
name: calibrar
description: Guía la calibración de un filamento en OrcaSlicer (temperatura, caudal máximo, pressure advance, flujo, retracción y tolerancia), lee los resultados en fotos y guarda los valores en el perfil con respaldo. Se usa cuando el usuario dice "calibrar", "calibrá el filamento", "torre de temperatura", "nuevo rollo", "cambié de marca de filamento" o quiere mejorar la calidad de un material.
---

# /calibrar: calibrar un filamento

Cargar antes la skill `impresion-3d` y seguir sus reglas. Guía detallada de cada test: `references/calibracion.md` de esa skill (todas las referencias de esta skill son de `impresion-3d`). Scripts: `<raíz del plugin>/skills/impresion-3d/scripts/`.

## 1. Preparar

1. Igual que `/pieza` paso 0: carpetas, `config.json`, aceptación del aviso.
2. Preguntar qué filamento (marca, material, color) y en qué impresora (como `/pieza` paso 4: si hay varias en Orca, preguntar; si no está preparada, `/impresoras`). Si el filamento no tiene perfil propio:
   - Proponer el nombre `<Marca> <Material> @<impresora>`.
   - Crearlo con `perfil_orca.py crear --tipo filamento --hereda "<filamento de sistema del material>" --impresora <json>`, con los valores de la ficha del fabricante (temperaturas, densidad) y los puntos de partida de `references/calibracion.md`.
   - Agregarlo a `filamentos` en `config.json`.
3. Recomendar secar el filamento antes de calibrar si es PETG, TPU o nylon, o si el rollo estuvo abierto.
4. Abrir `calibraciones/<filamento>.md` en la carpeta de trabajo (crearlo si no existe) para ir anotando.

## 2. Hacer los tests en orden

Para cada test, uno por vez:

1. Explicar en 2 o 3 líneas qué mide y por qué va en ese orden.
2. Dar los pasos exactos en Orca: menú **Calibración** → nombre del test → valores a cargar (inicio, fin, paso) para ese material. Recordar elegir antes en Orca la impresora, este filamento y la cama.
3. Pedir que lo imprima y mande una foto (de frente, buena luz, regla al lado) o la medición con calibre.
4. Leer el resultado. Si no se ve claro, decir qué se duda y pedir otra foto o la medida. No adivinar.
5. Calcular el valor (fórmulas en `references/calibracion.md`) y mostrar la cuenta.
6. Proponer el cambio en el perfil del filamento: traerlo, armar el nuevo con `perfil_orca.py crear --base <traído> --set <clave>=<valor> --anterior <traído> --impresora <json>`, mostrar los cambios y **pedir OK** (es un perfil del usuario). Con el OK: respaldo, escritura, historial.
7. Anotar en `calibraciones/<filamento>.md`: fecha, test, rango, lectura, valor final y nombre de la foto.

Orden: temperatura → caudal máximo (MVS) → pressure advance → flujo → retracción → (opcional) tolerancia. Si el flujo cambió mucho, repetir el pressure advance.

## 3. Cerrar

1. Laminar con `orca-mcp` una pieza chica de prueba (por ejemplo, un cubo de 20 mm generado con `cad.py`) usando el perfil calibrado. Traer el G-code y verificar en la cabecera que tomó los valores. Correr `revisar_gcode.py --impresora <json>`.
2. Resumir: valores finales, antes y después, y qué mejora esperar.
3. Si se hizo el test de tolerancia, guardar las holguras medidas en `taller-3d/aprendizajes.md` para que `/pieza` las use en encastres.
4. Recordar que Orca abierto no ve los cambios hasta reiniciarlo.
