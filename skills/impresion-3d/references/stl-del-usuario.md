# Pieza desde un STL que trae el usuario

El usuario ya tiene el modelo (lo diseñó, se lo pasaron o lo bajó) y quiere el mismo circuito que una pieza diseñada acá: revisarla, configurarla, laminarla, entregarla y, si quiere, publicarla. No se modela ni se le cambia la forma, salvo que lo pida. Lo usa `/pieza` (sección 2); todo lo demás de `/pieza` sigue igual.

## 1. Conseguir el archivo

- **Adjunto en el chat:** leerlo por su nombre. Es el camino del botón "Pieza desde un STL" del panel, que manda «Quiero hacer una pieza con un STL que ya tengo…»: pedir el archivo si no vino.
- **En la PC:** si está dentro de una carpeta conectada (la de trabajo, por ejemplo), ubicarlo con `device_list_dir` y traerlo con `device_stage_files`. Si está en otra (Descargas), pedir acceso solo a esa carpeta con `device_request_folder_access` diciendo para qué, y traer solo ese archivo. Si el chat no deja adjuntarlo, lo más simple es que lo copie a su carpeta de trabajo y diga el nombre.
- **Solo STL** (binario o de texto). Con un `.3mf`, `.obj` o `.step`: pedir que lo exporte como STL (en Orca: clic derecho sobre la pieza → Exportar como STL). Un `.gcode` no es un modelo: ya está laminado para otra impresora y no se puede revisar ni adaptar.
- Varios STL de un mismo objeto (partes): preguntar si van juntos en una cama o cada uno por separado; por defecto, una pieza por archivo.

## 2. Preguntar (una sola vez, junto con el cuestionario de `/pieza`)

1. **De quién es:** ¿lo hiciste vos o lo bajaste? Si lo bajó: de qué página y con qué licencia. Imprimirlo para uno mismo no tiene vueltas. **Para venderlo** hace falta una licencia que permita uso comercial: con CC BY-NC (u otra no comercial) o sin licencia clara, se puede dejar listo para imprimir pero no se arma la publicación sin permiso del autor. Un personaje, una mascota o un logo ajeno no se vende aunque la licencia del archivo diga comercial. Anotarlo en el panel (`--origen`, `--fuente`, `--licencia`): `/publicar` parte de eso.
2. **Cuánto tiene que medir**, si el tamaño no es obvio: un STL no dice su unidad.
3. Lo de siempre: impresora, para qué es, material, color, prioridad. Y **cómo se usa**: de dónde viene la fuerza y qué cara se ve, porque de eso sale la orientación.

## 3. Revisar y dejarlo imprimible

```bash
python3 -I revisar_stl.py original.stl --impresora <json de la impresora> --otras <taller-3d/impresoras traída> \
  --material <m> --orientar --json informe_original.json
```

- **RECHAZADO por malla abierta o caras sueltas:** no se "arregla" a ojo. Decir qué tiene y pedir que lo exporte de nuevo o que lo repare (en Orca: clic derecho → Reparar modelo; después, Exportar como STL). Una parte suelta en el aire, igual.
- **Cáscara fina** (un escaneo o un modelo generado por IA): `engrosar_stl.py` (`references/foto-a-3d.md`, sección 4).
- **Unidades y tamaño:** si avisa que es diminuta, o no coincide con lo que dijo el usuario, escalar con `--escala` (metros 1000, pulgadas 25.4, centímetros 10) o `--alto <mm>`, y confirmar las medidas finales con él antes de laminar.
- **No entra en la cama:** `--otras` dice en cuál de sus impresoras entra. Si no entra en ninguna, ofrecer escalarla (si el tamaño no importa) o decir que hay que partirla (no se parte sola).
- **Orientación:** `--orientar` compara las seis caras de apoyo (superficie de apoyo, voladizos, alto). Elegir con ese ranking **y** con el uso: capas a lo largo de la carga, la cara que se ve arriba o vertical, base ancha. Decirle al usuario cuál se eligió y por qué, en una línea.
- Dejar la pieza final:
  ```bash
  python3 -I revisar_stl.py original.stl --rotar <la elegida> [--escala N | --alto MM] --apoyar --centrar \
    --impresora <json> --material <m> --salida pieza.stl --json informe_stl.json
  ```
- `vista_previa.py pieza.stl vista.png --titulo "<nombre>"` y, si es decorativa, la foto renderizada. Mirarla antes de mostrarla y mostrársela al usuario con las medidas: es la confirmación de que se entendió el archivo.

## 4. Guardar y seguir

- Carpeta de la pieza como siempre (`catalogo.py carpeta`). Adentro: **`original.stl`** (el archivo del usuario, sin tocar) y **`pieza.stl`** (orientado y escalado: el que se lamina). No hay `pieza.py`.
- Seguir `/pieza` desde la configuración (sección 3) hasta la entrega: perfiles AUTO según el uso, laminado, revisión del G-code, G-code con nombre, proyecto `.3mf`, informe y costo.
- Panel: `catalogo.py agregar … --origen stl_propio` (o `stl_descargado --fuente <url> --licencia "<licencia>"`), con `original.stl` y `pieza.stl` en `--archivos`.
- Si pide un cambio de forma (un agujero, una base, cortar algo): `cad.importar_stl` y las operaciones de `cad.py` sobre el original, en un `pieza.py` (`references/cad.md`). Si el modelo es ajeno, la licencia también tiene que permitir modificarlo (las "ND" no).
- Al final, ofrecer `/publicar` igual que con cualquier pieza, salvo que la licencia no deje venderla: ahí decirlo y no ofrecerlo.
