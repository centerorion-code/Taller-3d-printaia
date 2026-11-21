---
name: ayuda
description: "Explica cómo usar el taller 3D, con el manual de uso: cómo pedirle una pieza a Claude, qué datos dar, ejemplos de pedidos, el circuito completo de la pieza y los comandos disponibles. Se usa cuando el usuario pregunta \"cómo te pido una pieza\", \"cómo funciona el taller\", \"qué podés hacer\", \"cuál es el circuito\", \"manual\" o \"ayuda con el taller\"."
---

# /ayuda: manual de uso del taller

El manual está en `<raíz del plugin>/MANUAL.md` (la raíz es la carpeta que contiene `skills/`). Leerlo y responder con lo que el usuario necesita, sin pegarlo entero:

- **"¿Cómo funciona?" o "¿qué podés hacer?":** los 10 pasos del circuito en una línea cada uno, dos ejemplos de pedidos y la tabla de comandos.
- **"¿Cómo te pido una pieza?":** la lista de "Un buen pedido dice" y tres ejemplos. Si el usuario ya tiene una pieza en mente, ofrecer empezar ahí mismo con `/taller-3d:pieza`.
- **Una duda puntual** (archivos, cambios, celular, perfiles, venta): la respuesta de la sección o pregunta frecuente que corresponda.
- Si quiere el manual a mano, ofrecer dejar una copia en su carpeta de trabajo (`<trabajo>/MANUAL.md`) con `device_commit_files`, o mandarlo como archivo.

Al nombrar comandos, escribirlos con el prefijo del plugin, como se usan en la app (`/taller-3d:pieza`), y recordar que también se puede pedir todo con palabras.

Responder en el idioma del usuario, claro y breve. No prometer cosas que el manual dice que el taller no hace (arrancar impresiones, piezas médicas o para alimentos, roscas impresas).
