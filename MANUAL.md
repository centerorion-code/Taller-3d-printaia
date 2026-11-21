# Manual de uso de taller-3d

Cómo pedirle una pieza a Claude y qué pasa desde que la pedís hasta que la imprimís.

## Antes de empezar (una sola vez)

1. Sumá el plugin desde el menú de **Claude Desktop**, la app de escritorio, con la dirección de GitHub `noamix/Taller-3d-printaia` (no se hace desde el chat), e instalá lo necesario en tu PC (ver [INSTALACION.md](INSTALACION.md)).
2. En Claude escribí `/instalar`: revisa que todo ande, te pregunta en qué impresora de tu Orca querés trabajar, investiga sus datos oficiales y la configura, y hace una pieza de prueba.
3. La primera vez te pide que leas el [aviso de uso](DISCLAIMER.md) y escribas ACEPTO.

La PC tiene que estar prendida y con la app de Claude abierta, porque ahí están tu Orca y tus carpetas. Con eso, podés pedir piezas desde la PC o desde el celular.

## Tres maneras de pedir

| Querés… | Pedilo así | Qué recibís |
|---|---|---|
| **Solo el diseño** (lo imprimís en otro lado, lo mandás a un servicio o querés el archivo) | "Diseñame…", "necesito el STL de…", `/diseno` | Modelo paramétrico: STL, archivo editable con las medidas arriba y una vista. No hace falta la PC. |
| **La pieza lista para imprimir** en tu impresora | "Haceme…", "imprimime…", `/pieza` | Todo lo anterior más la configuración, el G-code revisado y el costo. |
| **La pieza y su publicación** en tu tienda | "…y publicala", o decí que sí cuando Claude te lo ofrece | Además, el borrador del producto con precio, imagen y descripción. |

Si no queda claro cuál querés, Claude te lo pregunta una sola vez.

## Cómo pedir una pieza

Escribí qué necesitás con tus palabras, como se lo pedirías a alguien que sabe imprimir. Cuanto más claro el pedido, menos preguntas y mejor resultado.

Un buen pedido dice:

- **Qué es y para qué sirve:** "un soporte para colgar el router en la pared".
- **Las medidas que importan:** tomalas con calibre si la pieza tiene que encastrar en algo.
- **Dónde va a estar:** adentro, al sol, cerca de una fuente de calor o en contacto con agua.
- **Cuánto esfuerzo hace:** "sostiene 600 g", "se abre y se cierra todos los días".
- **Material y color,** si tenés preferencia.
- **Fotos o un dibujo,** si ayudan, con una regla al lado.

### Ejemplos

- "Haceme un soporte para colgar el router en la pared. El router mide 250 × 180 × 40 mm y pesa 600 g. En PETG negro, con dos agujeros para tornillos de 4 mm."
- "Necesito una tapa a presión para un tarro. El borde mide 82,5 mm de diámetro por fuera (medido con calibre). Que no se salga sola."
- "Se rompió esta traba de la persiana (te mando foto con regla). Mide 40 × 12 mm y el agujero es de 6 mm. Va al sol."
- "Te paso este STL que bajé de Printables. Es decorativo: quiero que quede lo más lindo posible."
- "Imprimime 10 separadores de 10 mm de alto para tornillos M3."
- "Diseñame un organizador para cajón de 3 divisiones, 300 × 120 × 50 mm. Solo el STL, que lo imprimo en un servicio. Que pueda cambiar la cantidad de divisiones."
- "Quiero hacer llaveros con nombre para vender." Si hay un plugin de Orca que lo hace, Claude te lo sugiere (y te dice de quién es y qué riesgos tiene); si preferís, lo diseña él.

También podés escribir `/pieza` y Claude te guía.

### Si no sabés algo

No pasa nada: Claude te pregunta lo que falta. Lo único que no inventa son las medidas: si una importa y no la sabés, te va a pedir que la midas.

## El circuito

```
 1. Pedido (texto, foto, medidas o STL)
        ↓
 2. Preguntas rápidas (uso, lugar, material, prioridad, medidas)
        ↓
 3. Diseño + vista previa ── ¿la aprobás? ── no → cambios y otra vista
        │                      (si hay un plugin de Orca que lo hace, te lo sugiere)
        ├── ¿solo el diseño? → STL + archivo editable y listo (/diseno)
        ↓ sí, para imprimir
 4. Configuración según el uso (perfiles de trabajo AUTO)
        ↓
 5. Laminado en tu Orca ⇄ ajustes (hasta 3 vueltas)
        ↓
 6. Revisión de seguridad ── no pasa → se corrige; no se entrega
        ↓ pasa
 7. Entrega en tu carpeta (G-code, modelo, vista, informe, costo)
        ├── en paralelo, si tenés tienda: borrador de la publicación
        │   (precio, imagen ilustrativa, descripción) → lo aprobás vos
        ↓
 8. Imprimís vos (USB o app de la impresora)
        ↓
 9. Contás cómo salió → Claude ajusta y aprende
        ↓
10. Foto real de la pieza → reemplaza la imagen ilustrativa
    y publicás el producto cuando quieras
```

### Paso a paso

1. **Pedido.** Texto, foto, medidas o un STL que ya tengas.
2. **Preguntas rápidas.** Hasta cuatro, con opciones para tocar: para qué es, dónde va, qué material y qué priorizás (calidad, resistencia, velocidad o ahorro de material). Además, las medidas que falten.
3. **Diseño y vista previa.** Claude diseña la pieza con medidas exactas y te muestra una imagen con cuatro vistas y las medidas. **Vos la aprobás** o pedís cambios ("más alta", "agujeros de 5 mm", "redondeá los bordes"). Si trajiste un STL, revisa que esté sano y que entre en la cama.
4. **Configuración.** Elige los ajustes según el uso: paredes, relleno, velocidades, temperaturas, soportes y orientación. Los guarda en dos perfiles de trabajo llamados "AUTO". **Tus perfiles no se tocan.**
5. **Laminado.** Lamina en tu Orca y mira el resultado: tiempo, gramos, voladizos y temperaturas. Si algo no cierra, ajusta y vuelve a laminar, hasta tres veces antes de consultarte.
6. **Revisión de seguridad.** Revisa el G-code: temperaturas, que no salga de la cama, que no tenga comandos que cambien la configuración de la impresora y que apague todo al terminar. **Si no pasa, no se entrega.**
7. **Entrega.** Deja todo en una carpeta y te resume tiempo, gramos, costo (si cargaste precios), las decisiones con el porqué y qué mirar durante la impresión. También podés abrir `pieza.stl` en Orca y elegir los perfiles AUTO: quedan configurados igual.
   **En paralelo, la publicación:** si tenés tienda configurada, Claude te ofrece armar el producto en ese momento, con el precio calculado con el tiempo y los gramos reales y una imagen ilustrativa (dice "Imagen ilustrativa"). Lo aprobás vos, también desde la app de Claude en el celular, y queda como borrador.
8. **Imprimís vos.** Pasás el G-code a la impresora (por USB o con la app de la marca) y la arrancás desde ahí. **Claude nunca arranca una impresión.** Mirá la primera capa completa y no dejes la impresora sola.
9. **Contale cómo salió.** Mandale una foto, aunque haya salido bien. Si algo falló, lo diagnostica y lo corrige. Lo que funcionó queda anotado y mejora las próximas piezas.
10. **Vender.** Cuando tengas la pieza impresa, mandale la foto: la suma al producto como imagen principal. El borrador lo publicás vos desde tu tienda. Si no lo armaste antes, `/publicar` lo hace en cualquier momento.

## Qué decidís vos

- Aprobar el diseño antes de laminar.
- El material y la prioridad.
- Cualquier cambio en tus propios perfiles de Orca (siempre con respaldo).
- Arrancar la impresión.
- Publicar el producto: queda en borrador hasta que lo publiques vos.
- Instalar plugins de Orca: Claude solo los sugiere.

## Dónde quedan tus archivos

En tu carpeta de trabajo, la que elegiste al instalar (si apretaste Enter, `Documentos/Taller 3D`). Para usar otra, movela vos a donde quieras y decile a Claude la ruta nueva: te pide acceso y sigue desde ahí.

```
catalogo.html           todas tus piezas en una página: abrila con doble clic
impresiones/2026-11-21_soporte-router/
    pieza.py            modelo editable (las medidas están arriba de todo)
    pieza.stl           el modelo
    vista.png           la vista previa
    pieza-.../plate_1.gcode   lo que se imprime
    informe.md          tiempo, gramos, costo, decisiones y qué mirar
    config_usada.json   configuración usada y por qué
disenos/2026-11-21_organizador/
    pieza.py, pieza.stl, vista.png, parametros.md   pedidos de solo diseño
respaldos/              copias de lo que se cambió
calibraciones/          resultados de calibración por filamento
taller-3d/              tu configuración, el historial, el índice del catálogo, los aprendizajes y las novedades de tu Orca
```

El catálogo (`catalogo.html`) se actualiza solo cada vez que Claude guarda, lamina o publica una pieza. Muestra la vista (o la foto, si le mandaste una de la pieza impresa), las medidas, el material, el tiempo, los gramos, el costo, el precio y los archivos de cada una, ordenadas por mes, con buscador. Si tenías piezas de antes, pedí "armá el catálogo" y las suma.

## Cambiar una pieza ya hecha

Pedilo con tus palabras: "Hacé el soporte del router 1 cm más ancho" o "el agujero salió justo, agrandalo 0,2 mm". Claude edita el modelo, vuelve a laminar y lo revisa. Si sabés algo de programación, también podés cambiar las medidas en `pieza.py`.

## Otros pedidos

| Para… | Decí o usá |
|---|---|
| Solo el diseño, sin imprimir | `/diseno` o "necesito el STL de…" |
| Calibrar un rollo nuevo | `/calibrar` o "calibrá el PETG nuevo" |
| Trabajar con otra impresora | `/impresoras`, o decilo en el pedido ("en la Bambu") |
| Vender una pieza | `/publicar` |
| Ver todas tus piezas o buscar una | `/catalogo` |
| Volver atrás un cambio de perfil | `/restaurar` |
| Revisar que todo ande | `/instalar` |
| Una duda de configuración | "¿Qué es la costura en bisel?", "¿por qué salen hilos?" |
| Volver a ver este manual | `/ayuda` |

## Lo que el taller no hace (todavía)

- No arranca impresiones ni controla la impresora.
- No garantiza piezas para uso médico, de seguridad o en contacto con alimentos.
- Para figuras, formas orgánicas o texto en relieve necesita Blender, un plugin de Orca o un modelo existente: el diseño por código es para piezas funcionales.
- No imprime roscas: usa tornillos pasantes, tuercas o insertos de latón.
- Un encastre muy justo puede necesitar una prueba. Si calibrás la tolerancia con `/calibrar`, acierta más a la primera.

## Preguntas frecuentes

**¿Puedo pedir desde el celular?** Sí, con la PC prendida y la app de Claude abierta en la PC.

**¿Necesito la PC para un diseño?** No. Con `/diseno` Claude te manda el STL y el archivo editable por el chat. La PC hace falta para laminar y para dejar los archivos en tu carpeta.

**¿Se entera de las novedades de Orca?** Sí. Después de cada laminado compara tu Orca con lo que conoce (parámetros nuevos o que ya no están) y una vez por mes revisa si salió una versión nueva o hay plugins útiles. Te avisa solo lo que te sirve; nunca instala ni actualiza nada solo.

**¿Puedo aprobar desde el celular?** Sí: la conversación es la misma en la PC y en la app de Claude del celular.

**¿Tengo que tener Orca abierto?** No. Si lo tenés abierto, reinicialo para ver los perfiles nuevos.

**¿Gasta mi plan de Claude?** Sí: diseñar y ajustar consume uso de tu plan. Un pedido claro y con medidas ahorra vueltas.

**¿Puedo vender piezas de modelos bajados de internet?** Solo si la licencia del modelo lo permite: muchos son de uso no comercial. Revisala antes de publicar.

**¿Y si la pieza sale mal?** Mandale una foto y contale qué pasó: lo diagnostica, corrige el perfil o el modelo y lo anota para la próxima.

**¿Qué pasa con mis perfiles de Orca?** Solo se reescriben los "AUTO". Los tuyos se cambian únicamente si lo aprobás, siempre con respaldo, y `/restaurar` los vuelve atrás.
