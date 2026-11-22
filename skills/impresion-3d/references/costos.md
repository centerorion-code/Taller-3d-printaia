# Costos y precios (`costos.py`)

El costo de una pieza sale de los datos del usuario en `config.json` y de lo que estima Orca (gramos y tiempo). El precio de venta se calcula por canal, con el margen que el usuario quiere ganar sobre el precio.

## Los datos, de dónde salen y cómo pedirlos

| Dato | Dónde va | Cómo conseguirlo |
|---|---|---|
| Precio del kWh | `costos.luz` | La boleta de luz del usuario (foto o PDF). Ver abajo. |
| Consumo de cada impresora | `impresoras[].costo.consumo_w` y `consumo_fuente` | Se busca en internet, sin preguntar (abajo): el promedio oficial, una prueba publicada o, si no hay, estimado por el tamaño de la cama. Medido con un medidor de enchufe es lo mejor. |
| Precio de cada impresora | `impresoras[].costo.precio` | Preguntar cuánto la pagó (con envío e impuestos). |
| Vida y mantenimiento | `impresoras[].costo.vida_horas`, `mantenimiento_pct` | Por defecto 4000 h (unos 3 años a 4 h por día) y 5 % del precio en repuestos. |
| Calentamiento | `impresoras[].costo.calentamiento_min` | Por defecto 5 minutos de cama y boquilla antes de imprimir. |
| Precio del filamento | `costos.filamentos.<material o perfil>.precio_kg` | Lo que paga el kilo (un rollo de 1 kg, con envío). |
| Fallas | `costos.fallas_pct` | Por defecto 10 % (5-10 % con experiencia, 15-25 % al empezar). |
| Tu hora | `costos.mano_de_obra.precio_hora` y `minutos_por_pieza` | Preparar, sacar soportes, limpiar y embalar. |
| Embalaje | `tienda.embalaje` | Bolsa, caja, etiqueta. |
| Canales de venta | `tienda.canales` | Comisión, cuotas, IVA sobre la comisión y cargo fijo de cada canal. |
| Margen habitual | `tienda.margen_precio_pct` | Qué parte del precio quiere ganar (por ejemplo 40 %). |

Pedir cada dato la primera vez que hace falta, de a uno, con la frase de `costos.py estado` ("Te paso mi boleta de luz…"). El consumo de la impresora no se pide: se busca (abajo). Lo que falta no frena el presupuesto: sale con la lista de lo que falta y lo que se supuso.

### La boleta de luz

Pedir una foto o el PDF de la última boleta. Leer:

- **Período** y **empresa**.
- **kWh consumidos** en el período.
- **Cargo variable por kWh**. Si la tarifa tiene escalones, el del último escalón que alcanzó: es lo que cuesta cada kWh de más.
- **Impuestos y tasas sobre la energía**, en %: IVA y las tasas provinciales y municipales que se cobran sobre el consumo. No sumar las que son montos fijos.
- **Cargos fijos** del período y **total**.

Después:

```
python3 -I costos.py luz --config config.json --kwh 310 --total 53072 --cargo-variable 120.5 \
    --impuestos-pct 26.9 --cargos-fijos 4800 --periodo 2026-10 --empresa EDET --salida config.json
```

- **Marginal** = cargo variable × (1 + impuestos %). Es el que se usa cuando está: los cargos fijos se pagan igual aunque no imprima.
- **Promedio** = (total − cargos fijos) / kWh. Es para cuando la boleta no separa el cargo variable.
- Si la boleta tiene más de 4 meses, el costo lo avisa: pedir una más nueva.

**Privacidad:** de la boleta se guardan solo los números de la tarifa (kWh, cargos, impuestos, total, período y empresa). Nunca el nombre, la dirección, el número de cliente o de medidor, el CUIT o DNI ni el código de pago. No guardar la imagen ni el PDF en la carpeta de trabajo ni en la memoria.

### El consumo de la impresora

Se busca en internet **sin preguntarle al usuario**, cada vez que una impresora entra al taller (`/impresoras`, `/instalar`) y cada vez que una cuenta de costo usa una impresora que no lo tiene (`/pieza`, `/publicar`, el botón "Buscá el consumo…" del panel). Lo que importa es el **promedio mientras imprime**. La potencia nominal de la ficha ("Rated power", la de la fuente) es el máximo calentando: con una fuente de 350 W se imprime con 100 a 170 W, según la cama y el material, y una Creality Hi dice 1150 W a 220 V (390 W a 110 V), que no es lo que gasta imprimiendo.

En este orden, con el modelo exacto de la impresora:

1. **El promedio oficial:** ficha, manual o ayuda del fabricante (Prusa y Bambu Lab lo publican, a veces por material; usar el del material que más usa). `--promedio <W> --origen oficial --fuente <enlace>`.
2. **Una prueba publicada** del mismo modelo, medida con un medidor de enchufe mientras imprime (una reseña con mediciones o el wiki del fabricante; no un comentario suelto de un foro ni una tienda). `--promedio <W> --origen prueba --fuente <enlace>`.
3. **Si solo está la potencia nominal, estimarlo por el tamaño de la cama:** `--datos <JSON de la impresora>` (o `--cama 300x300`), `--material <el que más usa en esa impresora>`, `--nominal <W de la ficha>` y `--fuente <enlace de la ficha>`. Si tiene calefactor de cámara activo (para ABS), decir que con la cámara prendida consume bastante más.
4. **Preguntar** solo si no se encuentra nada de eso (por ejemplo, una impresora armada a mano sin ficha): "No encontré cuánto consume tu <impresora>. ¿Qué tamaño de cama tiene? Si tenés un medidor de enchufe, mejor: medila en una impresión."

```
python3 -I costos.py consumo --config config.json --impresora <id> --datos <impresora>.json --material PETG \
    --nominal 350 --fuente "<enlace de la ficha>" --salida config.json
```

Guardarlo con `--salida` y escribir `config.json` con el procedimiento de escritura (respaldo). El script anota `consumo_w`, `consumo_fuente` (de dónde salió), `consumo_fecha` y `potencia_nominal_w`, y no pisa un dato mejor (un medido con un estimado) salvo con `--reemplazar`. Decirle al usuario en una línea lo que se encontró y de dónde, con el enlace; si es estimado, que con un medidor de enchufe se puede medir el real ("Quiero medir el consumo real…" en el panel).

- **Medido por el usuario:** con un medidor de enchufe, los kWh de una impresión entera divididos por sus horas: `--promedio <W> --origen medido`. Es el mejor dato.
- **Lo que diga el usuario sin medirlo:** `--origen usuario`. Si es el número de la etiqueta de la fuente, es la potencia nominal: estimarlo con `--nominal` en vez de usarlo como promedio.

### Los canales

`tienda.canales` tiene un canal por clave (`tienda`, `mercadolibre`, `tiendanube`…):

```json
"canales": {
  "tienda": {"nombre": "Tu tienda", "comision_pct": 0},
  "mercadolibre": {"nombre": "Mercado Libre", "comision_pct": 15, "iva_comision": true,
                   "cuotas_pct": 0, "cargo_fijo": 1000, "cargo_fijo_hasta": 20000}
}
```

La comisión de Mercado Libre depende de la categoría y del tipo de publicación, y cambia: buscarla en la web para la categoría del usuario antes de guardarla, y decirle de dónde salió. `iva_comision`: si el canal cobra IVA sobre su comisión. `cargo_fijo_hasta`: el precio desde el que ya no cobra el cargo fijo.

## Las fórmulas

```
material      = gramos / 1000 × precio del kg
luz           = consumo (W) × (horas de Orca + calentamiento) / 1000 × precio del kWh
máquina       = precio de la impresora / horas de vida × (1 + mantenimiento %) × horas de Orca
fallas        = (material + luz + máquina) × fallas % / (1 − fallas %)
mano de obra  = minutos / 60 × precio de tu hora
costo         = material + luz + máquina + fallas + mano de obra + embalaje

precio = (costo + cargo fijo × (1 + IVA)) / (1 − (comisión % + cuotas %) × (1 + IVA) − margen %)
```

El IVA va sobre las comisiones solo si el canal lo cobra.

## El margen

- Es **sobre el precio**: de cada venta, qué parte le queda de ganancia después de comisiones y costos. Un recargo del 50 % sobre el costo es un margen del 33 %: margen = recargo / (100 + recargo).
- El `margen_pct` de antes de la 0.1.14 era un recargo. `costos.py` lo convierte y avisa: confirmarlo con el usuario y guardar `margen_precio_pct`.
- **En cada producto se elige** (skill `publicar`): `costos.py pieza … --margenes` da tres opciones (una más baja, la habitual y una más alta) con el precio y la ganancia en cada canal. Si el usuario dice un precio, `--precio 4500` muestra el margen real que le deja en cada canal. Si en algún canal la ganancia da negativa, decirlo claro.

```
python3 -I costos.py pieza --config config.json --informe-gcode informe_gcode.json --impresora hi --margenes
python3 -I costos.py pieza --config config.json --informe-gcode informe_gcode.json --impresora hi --precio 4500
```

## Cómo mostrarlo

En el informe de la pieza: el costo total y sus partes, el precio en cada canal (con lo que se lleva el canal y lo que queda), lo que se supuso y lo que falta. Los importes con punto de miles, sin decimales.
