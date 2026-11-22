# Manual de uso de taller-3d

Cómo pedirle una pieza a Claude y qué pasa desde que la pedís hasta que la imprimís.

## Antes de empezar (una sola vez)

1. Sumá el plugin desde el menú de **Claude Desktop**, la app de escritorio, con la dirección de GitHub `noamix/Taller-3d-printaia` (no se hace desde el chat), e instalá lo necesario en tu PC (ver [INSTALACION.md](INSTALACION.md)).
2. En Claude escribí `/taller-3d:instalar`: revisa que todo ande, te pregunta en qué impresora de tu Orca querés trabajar, investiga sus datos oficiales y la configura, y hace una pieza de prueba.
3. La primera vez te pide que leas el [aviso de uso](DISCLAIMER.md) y escribas ACEPTO.

La PC tiene que estar prendida y con la app de Claude abierta, porque ahí están tu Orca y tus carpetas. Con eso, podés pedir piezas desde la PC o desde el celular.

## Tres maneras de pedir

| Querés… | Pedilo así | Qué recibís |
|---|---|---|
| **Solo el diseño** (lo imprimís en otro lado, lo mandás a un servicio o querés el archivo) | "Diseñame…", "necesito el STL de…", `/taller-3d:diseno` | Modelo paramétrico: STL, archivo editable con las medidas arriba y una vista. No hace falta la PC. |
| **La pieza lista para imprimir** en tu impresora | "Haceme…", "imprimime…", `/taller-3d:pieza` | Todo lo anterior más la configuración, el G-code revisado y el costo. |
| **La pieza y su publicación** en tu tienda | "…y publicala", o decí que sí cuando Claude te lo ofrece | Además, el borrador del producto con fotos, descripción y el precio con el margen que elijas. |

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

También podés escribir `/taller-3d:pieza` y Claude te guía.

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
        ├── ¿solo el diseño? → STL + archivo editable y listo (/taller-3d:diseno)
        ↓ sí, para imprimir
 4. Configuración según el uso (perfiles de trabajo AUTO)
        ↓
 5. Laminado en tu Orca ⇄ ajustes (hasta 3 vueltas)
        ↓
 6. Revisión de seguridad ── no pasa → se corrige; no se entrega
        ↓ pasa
 7. Entrega en tu carpeta (G-code, modelo, vista, informe, costo real)
        ├── en paralelo, si tenés tienda: borrador de la publicación
        │   (fotos de producto, descripción, el margen que elegís) → lo aprobás vos
        ↓
 8. Imprimís vos (USB o app de la impresora)
        ↓
 9. Contás cómo salió → Claude ajusta y aprende
        ↓
10. Foto real de la pieza → va primera en la publicación
    y publicás el producto cuando quieras
```

### Paso a paso

1. **Pedido.** Texto, foto, medidas o un STL que ya tengas.
2. **Preguntas rápidas.** Hasta cuatro, con opciones para tocar: para qué es, dónde va, qué material y qué priorizás (calidad, resistencia, velocidad o ahorro de material). Además, las medidas que falten.
3. **Diseño y vista previa.** Claude diseña la pieza con medidas exactas y te muestra una imagen con cuatro vistas y las medidas. **Vos la aprobás** o pedís cambios ("más alta", "agujeros de 5 mm", "redondeá los bordes"). Si trajiste un STL, revisa que esté sano y que entre en la cama.
4. **Configuración.** Elige los ajustes según el uso: paredes, relleno, velocidades, temperaturas, soportes y orientación. Los guarda en dos perfiles de trabajo llamados "AUTO". **Tus perfiles no se tocan.**
5. **Laminado.** Lamina en tu Orca y mira el resultado: tiempo, gramos, voladizos y temperaturas. Si algo no cierra, ajusta y vuelve a laminar, hasta tres veces antes de consultarte.
6. **Revisión de seguridad.** Revisa el G-code: temperaturas, que no salga de la cama, que no tenga comandos que cambien la configuración de la impresora y que apague todo al terminar. **Si no pasa, no se entrega.**
7. **Entrega.** Deja todo en una carpeta con el nombre de la pieza y de la impresora (te deja un enlace para ir directo a la carpeta y otro al `.3mf`), y te resume tiempo, gramos, costo real (con lo que cargaste; si falta algo, te dice qué), las decisiones con el porqué y qué mirar durante la impresión. **Para verla o tocarla en Orca, abrí el proyecto (`.3mf`) con doble clic:** se abre con tu impresora, el filamento, el proceso AUTO y tu tipo de cama ya elegidos. Si Claude tiene terminal en tu PC, te pregunta si querés que te abra Orca con la pieza.
   **En paralelo, la publicación:** si tenés tienda configurada, Claude te ofrece armar el producto en ese momento: fotos de producto hechas con Blender (fondo blanco, como pide Mercado Libre, y otra con sombra), la descripción y el precio con el tiempo y los gramos reales. **Te pregunta qué margen querés en ese producto**, con tres opciones y lo que ganás en cada canal, o le decís un precio. Lo aprobás vos, también desde la app de Claude en el celular, y queda como borrador.
8. **Imprimís vos.** Pasás el G-code a la impresora (por USB o con la app de la marca) y la arrancás desde ahí. **Claude nunca arranca una impresión.** Mirá la primera capa completa y no dejes la impresora sola.
9. **Contale cómo salió.** Mandale una foto, aunque haya salido bien. Si algo falló, lo diagnostica y lo corrige. Lo que funcionó queda anotado y mejora las próximas piezas.
10. **Vender.** Cuando tengas la pieza impresa, mandale la foto: la suma al producto como imagen principal (las fotos de Blender son ilustrativas). El borrador lo publicás vos desde tu tienda. Si no lo armaste antes, `/taller-3d:publicar` lo hace en cualquier momento.

## Qué decidís vos

- Aprobar el diseño antes de laminar.
- El material y la prioridad.
- Cualquier cambio en tus propios perfiles de Orca (siempre con respaldo).
- Arrancar la impresión.
- El margen de cada producto (o su precio).
- Publicar el producto: queda en borrador hasta que lo publiques vos.
- Instalar plugins de Orca: Claude solo los sugiere.

## Dónde quedan tus archivos

En tu carpeta de trabajo, la que elegiste al instalar (si apretaste Enter, `Documentos/Taller 3D`). Para usar otra, movela vos a donde quieras y decile a Claude la ruta nueva: te pide acceso y sigue desde ahí.

```
panel.html              el panel del taller: tus ideas y piezas y en qué paso está cada una (doble clic)
impresiones/2026-11-21_soporte-router_ender-3-v3-plus/
    soporte-router_ender-3-v3-plus.gcode   lo que se imprime (solo en esa impresora)
    soporte-router_ender-3-v3-plus.3mf     el proyecto de Orca: abrilo con doble clic
    pieza.py            modelo editable (las medidas están arriba de todo)
    pieza.stl           el modelo
    vista.png           la vista previa
    informe.md          tiempo, gramos, costo, decisiones y qué mirar
    producto/           la publicación: fotos de producto, ficha y precio
    config_usada.json   configuración usada y por qué
    laminado/           las vueltas de prueba de Orca (se pueden borrar)
disenos/2026-11-21_organizador/
    pieza.py, pieza.stl, vista.png, parametros.md   pedidos de solo diseño
respaldos/              copias de lo que se cambió
calibraciones/          resultados de calibración por filamento
taller-3d/              tu configuración, el historial, el índice del panel, los aprendizajes y las novedades de tu Orca
```

## El panel del taller

`panel.html`, en tu carpeta de trabajo, es tu administrador: abrilo con doble clic (conviene guardarlo como favorito del navegador). Cada idea y cada pieza es una tarjeta con su recorrido:

```
Idea → Diseño → Lista para imprimir → Impresa → En la tienda
```

- Arriba, cuántas ideas están **pendientes**, cuántas piezas **en proceso** y cuántas **terminadas**, con filtros y un buscador.
- Primero va **"Para hacer"** (lo más avanzado primero) y después las terminadas, por mes.
- Cada tarjeta dice **a quién le toca lo que sigue**: "Le toca a Claude: dejarla lista para imprimir" o "Te toca: imprimirla". Tiene botones con el pedido ("Diseñala", "Ya la imprimí", "Publicala"…), para qué impresora es, la vista (o la foto de la pieza impresa), medidas, material, tiempo, gramos, costo, precio y los archivos.
- **Tu taller:** arriba, lo que falta para que los costos y precios sean reales (la boleta de luz, el consumo de tu impresora, tu hora…), con un botón para cada cosa.
- En el archivo, los botones copian el pedido para que lo pegues en el chat.
- **Ideas para después:** contale a Claude "anotá esta idea: un soporte para la tele, 15 × 10 cm" y queda pendiente con lo que ya se sabe. Cuando la quieras hacer, pedila por su nombre.
- Al empezar a usar el taller, Claude te dice en una línea qué tenés pendiente.

Se actualiza solo cada vez que Claude anota una idea o guarda, lamina o publica una pieza. Una pieza impresa ya está terminada: publicarla es opcional. Si tenías piezas de antes, pedí "armá el panel" y las suma.

### El panel al costado del chat

En claude.ai y en la app de Claude, el panel también puede estar **al costado del chat**: Claude lo publica en tu cuenta (es privado: lo ves solo vos) y se actualiza solo. La primera vez te pregunta si lo querés.

Ahí **los botones le mandan el pedido directo a Claude**: tocás "Ya la imprimí" o "Publicala" y le llega a la conversación que publicó el panel, que lo hace y te contesta. Si en ese momento Claude está trabajando en otra cosa, lo hace cuando termina. Si la página no puede mandarlo (por ejemplo, desde una conversación que ya no está), el botón copia el pedido para que lo pegues en el chat.

### La guía

- Al empezar sin un pedido concreto ("hola", "¿qué hacemos?"), Claude te ofrece opciones para tocar con lo que sigue: la pieza que tenés para imprimir, una idea anotada, lo que falta configurar o algo nuevo.
- Mientras hace una pieza, ves las etapas en la lista de tareas (entender, modelo, configuración, laminar y revisar, entregar).
- Cada vez que te toca hacer algo, termina con **"Te toca: …"**: qué hacer y cómo.

## Cambiar una pieza ya hecha

Pedilo con tus palabras: "Hacé el soporte del router 1 cm más ancho" o "el agujero salió justo, agrandalo 0,2 mm". Claude edita el modelo, vuelve a laminar y lo revisa. Si sabés algo de programación, también podés cambiar las medidas en `pieza.py`.

## Otros pedidos

Los comandos llevan el nombre del plugin adelante (`/taller-3d:...`): si escribís `/pieza` a secas, no corre. Con tus palabras también funciona.

| Para… | Decí o usá |
|---|---|
| Solo el diseño, sin imprimir | `/taller-3d:diseno` o "necesito el STL de…" |
| Calibrar un rollo nuevo | `/taller-3d:calibrar` o "calibrá el PETG nuevo" |
| Trabajar con otra impresora | `/taller-3d:impresoras`, o decilo en el pedido ("en la Bambu") |
| Vender una pieza | `/taller-3d:publicar` |
| Ver tus ideas y piezas y qué sigue en cada una | `/taller-3d:panel` o "¿qué tengo pendiente?" |
| Anotar una idea para más adelante | "Anotá esta idea: …" |
| Volver atrás un cambio de perfil | `/taller-3d:restaurar` |
| Revisar que todo ande | `/taller-3d:instalar` |
| Una duda de configuración | "¿Qué es la costura en bisel?", "¿por qué salen hilos?" |
| Volver a ver este manual | `/taller-3d:ayuda` |

## Lo que el taller no hace (todavía)

- No arranca impresiones ni controla la impresora.
- No garantiza piezas para uso médico, de seguridad o en contacto con alimentos.
- Para figuras, formas orgánicas o texto en relieve necesita Blender, un plugin de Orca o un modelo existente: el diseño por código es para piezas funcionales.
- No imprime roscas: usa tornillos pasantes, tuercas o insertos de latón.
- Un encastre muy justo puede necesitar una prueba. Si calibrás la tolerancia con `/taller-3d:calibrar`, acierta más a la primera.

## Preguntas frecuentes

**¿Puedo pedir desde el celular?** Sí, con la PC prendida y la app de Claude abierta en la PC.

**¿Necesito la PC para un diseño?** No. Con `/taller-3d:diseno` Claude te manda el STL y el archivo editable por el chat. La PC hace falta para laminar y para dejar los archivos en tu carpeta.

**¿Se entera de las novedades de Orca?** Sí. Después de cada laminado compara tu Orca con lo que conoce (parámetros nuevos o que ya no están) y una vez por mes revisa si salió una versión nueva o hay plugins útiles. Te avisa solo lo que te sirve; nunca instala ni actualiza nada solo.

**¿Puedo aprobar desde el celular?** Sí: la conversación es la misma en la PC y en la app de Claude del celular.

**¿Tengo que tener Orca abierto?** No. Si lo tenés abierto, cerralo y volvé a abrirlo para ver los perfiles nuevos; después abrí el proyecto `.3mf` de la pieza.

**Abrí el proyecto de una pieza vieja y Orca marca cambios (↺) en los perfiles AUTO. ¿Está mal?** No: los AUTO se rehacen en cada pieza, y el proyecto trae los ajustes con que se hizo esa. Si la volvés a laminar desde ahí, sale igual que la primera vez.

**¿Por qué la carpeta y el G-code dicen el nombre de la impresora?** Porque un G-code sirve solo para la impresora para la que se laminó: así no se confunde, ni en la PC ni en la pantalla de la impresora.

**¿Claude me puede abrir Orca?** Si tiene terminal en tu PC, te pregunta si querés que te lo abra con la pieza. Si no, abrí el `.3mf` con doble clic. Imprimir es siempre tuyo: Claude no usa la pestaña Dispositivo ni los botones Imprimir o Enviar.

**¿Gasta mi plan de Claude?** Sí: diseñar y ajustar consume uso de tu plan. Un pedido claro y con medidas ahorra vueltas.

**¿Cómo calcula el costo?** Suma el material (gramos de Orca × precio del kilo), la luz (el consumo de tu impresora × las horas, con el precio del kWh de tu boleta), el desgaste de la impresora (lo que la pagaste repartido en sus horas de vida), las que salen mal (10 % si no le decís otra cosa), tu tiempo y el embalaje. Si falta un dato, te dice cuál y la frase para dárselo.

**¿Para qué quiere mi boleta de luz?** Para sacar lo que te cuesta de verdad cada kWh. Guarda solo los números de la tarifa (kWh, cargos, impuestos, período y empresa): nunca tu nombre, tu dirección ni tus números de cliente o de medidor.

**¿Cómo pone el precio?** Con tu margen **sobre el precio**: de cada venta, qué parte te queda después de las comisiones. Un 40 % quiere decir que de cada $ 1.000 te quedan $ 400 de ganancia. Ojo: un recargo del 50 % sobre el costo es un margen del 33 %. El precio sale por canal (tu tienda, Mercado Libre con su comisión e IVA…), y en cada producto elegís el margen o le decís un precio y te muestra cuánto ganás en cada canal.

**¿Las fotos de producto son reales?** Son renders 3D de tu pieza, con el color y el tipo de plástico, para tener la publicación lista antes de imprimir. La descripción aclara que son ilustrativas; cuando la imprimas, mandale una foto real y va primera.

**¿Puedo vender piezas de modelos bajados de internet?** Solo si la licencia del modelo lo permite: muchos son de uso no comercial. Revisala antes de publicar.

**¿Y si la pieza sale mal?** Mandale una foto y contale qué pasó: lo diagnostica, corrige el perfil o el modelo y lo anota para la próxima.

**¿Qué pasa con mis perfiles de Orca?** Solo se reescriben los "AUTO". Los tuyos se cambian únicamente si lo aprobás, siempre con respaldo, y `/taller-3d:restaurar` los vuelve atrás.
