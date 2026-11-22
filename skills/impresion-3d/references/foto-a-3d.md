# Pieza desde una foto: el modelo lo genera una IA

Para copiar algo que existe (una máscara, una figura, una escultura, un adorno) o hacer algo que se pide por cómo se ve y que Blender por código no hace bien (una persona, un animal con detalle), el modelo 3D lo genera **Hunyuan 3D** de Tencent con la cuenta del usuario, desde su Chrome. Claude sube la foto, espera, baja el STL y lo deja imprimible. Probado de punta a punta el 22/11/2026 (la máscara de piedra).

No es para piezas con medidas (un soporte, un repuesto): ahí la foto es una referencia y se modela con `cad.py`. Personajes, mascotas de marcas, logos ajenos y personas reales sin su permiso no se generan, igual que no se modelan (`references/modelado.md`).

## Qué hace falta

- **Cuenta en Hunyuan 3D** (https://3d.hunyuan.tencent.com) con la sesión abierta en el Chrome del usuario, y Claude in Chrome conectado. Lo dice `generadores_ia.hunyuan` de `config.json`; si no está, preguntarlo una vez. Crear la cuenta, entrar y resolver captchas lo hace el usuario: nunca escribir contraseñas.
- **Puntos:** cada generación gasta puntos de su cuenta (se ven arriba a la derecha de la página). Antes de generar, decir cuántos va a gastar y cuántos le quedan. El plan de la pieza que el usuario aprueba en el cuestionario es su OK; si después hay que generar de nuevo, avisarlo otra vez.
- **Descargas:** acceso a su carpeta de descargas con `device_request_folder_access`, una vez por conversación. Conviene que en Chrome esté apagado «Preguntar dónde guardar cada archivo» (Configuración → Descargas); si está prendido, el archivo igual sirve (paso 3.4).
- **Sin cuenta:** ofrecer que la cree (es gratis, con un cupo de puntos por día) o seguir por Blender por código o un modelo existente.

## 1. Las fotos

- **Una foto** alcanza: lo que no se ve (el dorso, los costados) lo inventa el generador.
- **Varias fotos** del mismo objeto (frente, atrás, izquierda, derecha; Hunyuan acepta de 2 a 8 en «Imágenes múltiples») dan un modelo más fiel. Si el usuario puede sacarlas, pedírselas: la misma distancia, el objeto centrado y entero, fondo liso, luz pareja y nada más en la foto.
- **Lo que pide Hunyuan:** PNG, JPG o WebP de hasta 10 MB y al menos 128 × 128 px; fondo liso, un solo objeto, sin texto, y que el objeto no quede chico en la foto.
- **Retocar antes de subir** si hace falta (sacar una soga o un soporte, el fondo, recortar), con Python (Pillow u OpenCV), y mostrarle el resultado. Guardar la foto original y la retocada en la carpeta de la pieza (`foto.jpg`, `foto-retocada.jpg`).
- **Los ángulos que faltan se pueden generar** con Nano Banana (Gemini o Flow, con la cuenta del usuario, `generadores_ia.imagenes`): «el mismo objeto visto desde atrás, desde la izquierda y desde la derecha, fondo liso, la misma escala y luz». Esas vistas son inventadas: sirven para que el 3D salga coherente y para que el usuario decida cómo es lo que no se ve, no para copiar algo real. Mostrarlas y usarlas solo si las aprueba. Gastan de su cupo diario, que Google cambia seguido: decirlo y, si hace falta, mirarlo en su cuenta.

## 2. Sin foto: primero una imagen

Si pide algo por cómo se ve que el código y Blender por código no hacen bien:

1. Armar el pedido de imagen: el objeto solo y entero, de frente o a tres cuartos, fondo liso, luz pareja, sin texto, con el estilo, el material y los detalles que pidió.
2. Generarla con su generador de imágenes (Gemini o Flow) desde su Chrome. Gasta de su cupo: decirlo.
3. Mostrarla y esperar su OK o sus cambios. Recién aprobada, sigue como una foto (sección 3); se pueden generar también las otras vistas (sección 1).

Hunyuan también genera desde un texto (la otra pestaña de la misma página): es más directo, pero el resultado se ve recién en 3D y cada intento gasta puntos. Con la imagen antes, el usuario decide el diseño sin gastar puntos de Hunyuan.

## 3. Generar en Hunyuan

1. **Subir la foto.** Claude in Chrome sube solo archivos de esta sesión. Lo probado: guardar la foto en la carpeta de la pieza en la PC (`device_commit_files`), traerla de vuelta con `device_stage_files` y subir esa ruta (`/mnt/user-data/uploads/<carpeta>/…`) con `file_upload` al campo de archivo oculto de la página. Hasta 3,8 MB por archivo: achicarla antes si pesa más. Así la foto queda además en la carpeta de la pieza.
2. **Elegir.** En https://3d.hunyuan.tencent.com/creation (si no abre, desde la portada: «Creación 3D» y el botón de empezar): la pestaña de imagen, «Imagen única» o «Imágenes múltiples» (cada foto en su lugar). El modelo más nuevo de la lista. Caras: 500 mil por defecto, que alcanza para imprimir; 1,5 millones si importa el detalle fino. La página está en chino y Chrome la traduce: buscar los controles con `find` o `read_page` por lo que hacen, no por un texto exacto, que cambia con la traducción.
3. **Generar** y esperar: tarda unos 3 o 4 minutos (primero la forma y después la textura). Mirar cada 30 a 60 segundos hasta que aparezca el modelo con el botón de descarga.
4. **Bajar el STL:** la flechita del botón de descarga abre los formatos; elegir STL. Mirar la carpeta de descargas con `device_list_dir` y traer **solo** el archivo nuevo (el `.stl` más reciente, con un nombre como `10aa5261….stl`). Descargas tiene archivos personales: no abrir ni nombrar ningún otro. Si en vez del `.stl` hay un `.com.google.Chrome.XXXX`, Chrome está esperando que el usuario elija dónde guardarlo: sirve igual si pesa exactamente 84 + 50 × triángulos bytes (un STL binario completo; los triángulos están en los bytes 80 a 83). Avisarle que puede cancelar esa ventana o guardarlo.
5. **Guardar el original** en `<carpeta de la pieza>/hunyuan/<nombre>-original.stl`, sin tocarlo.

## 4. Dejarlo imprimible

1. **Escala:** el STL viene sin unidades (mide menos de 1). Preguntar el alto o el ancho final, si no lo dijo, y escalar parejo: `revisar_stl.py original.stl --alto <mm> --salida <nombre>.stl` (o `--escala`).
2. **Pared:** la revisión avisa «es una cáscara de X mm de pared», lo normal en máscaras y figuras huecas (la máscara salió con 0,85 mm). Engrosarla:
   ```bash
   python3 -I engrosar_stl.py --stl <nombre>.stl --salida <nombre>.stl --pared 2
   ```
   Mueve hacia el hueco solo la superficie de adentro, así el detalle de afuera queda (informa cuánto se movió, que tiene que ser casi nada), rehace la malla con voxels y saca las sobras. Necesita `bpy`, como las fotos de producto. Tarda alrededor de un minuto. Volver a revisar.
3. **Mostrar:** `render_producto.py` con las tomas `tienda,frente`; si es hueca, también el dorso (girarla con `revisar_stl.py --rotar 0,0,180 --salida`). Mirarlas al lado de la foto y decir con franqueza qué copió bien y qué perdió: los grabados finos de una foto de frente suelen quedar en la textura de Hunyuan y no en el relieve, que es lo que se imprime.
4. **Imprimir:** una máscara o una figura parada lleva soportes tipo árbol; decirlo. Si es más grande que la cama, escalarla o partirla.

## 5. Pieza compuesta: lo generado y lo diseñado

Pedidos como «la máscara con un soporte para ponerla en la mesa» o «la figura sobre una base con su nombre»:

1. **Partir el pedido** y elegir la herramienta de cada parte (`references/modelado.md`):
   - lo que sale de la foto, con IA;
   - lo que tiene que encastrar o aguantar, con código y medidas;
   - lo que se describe por cómo se ve, según la forma: geométrico (escalones, grecas, letras sobre planos), con código; orgánico o estilizado con curvas libres, con Blender por código.
2. **Decir el plan en el cuestionario, antes de gastar puntos:** «La máscara: desde tu foto, con Hunyuan. El soporte: una base escalonada por código, con una greca del estilo de la máscara. Van separadas: la máscara entra en un hueco con su forma».
3. **Primero lo generado** (escalado y engrosado) y **después lo demás, medido sobre su STL**. El encastre: `hueco_para(pieza, profundidad, holgura)` de `cad.py` da el hueco con la sombra de los últimos milímetros de la pieza, sin trabas, así la pieza entra de arriba en su posición natural. Ver dónde cae el centro de gravedad: tiene que quedar bien adentro de la base.
4. **Separadas por defecto:** cada una se imprime en su mejor orientación (la base plana y sin soportes; lo generado con los suyos) y se encastran. Si va en una sola pieza: `importar_stl` y `unir`, y la revisión confirma que no quedan partes sueltas.
5. **Mostrar el conjunto** (`Manifold.compose([base, pieza])` exportado para el render) y cada parte.

Ejemplo: la máscara de piedra. La máscara salió de una foto con Hunyuan, a 18 cm de alto y engrosada a 2 mm. La base es `base.py`: dos escalones con esquinas tipo chakana, una greca escalonada tallada y un hueco de 10 mm con la forma del borde de la máscara, con 0,3 mm de holgura.

## 6. Para vender

- **Lo que genera Hunyuan:** antes de vender, confirmar que su acuerdo de servicio permite el uso comercial de lo generado (https://rule.tencent.com/rule/202501080004). Al 22/11/2026 esa página no cargaba y queda pendiente de leer: hasta entonces, decirle al usuario que lo confirme antes de publicar.
- **El objeto de la foto:** si es de otro (una obra, una artesanía ajena, una pieza de museo), copiarlo para vender puede no estar permitido: preguntarlo. Lo propio o del dominio público, sí.
