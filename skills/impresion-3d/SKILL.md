---
name: impresion-3d
description: Base de conocimiento y reglas de seguridad del taller 3D (OrcaSlicer 2.5.1, materiales, calibración, CAD por código). Se usa cuando el usuario quiere imprimir algo en 3D, pregunta por un ajuste o parámetro de Orca ("qué es seam_gap", "qué velocidad uso", "cuántas paredes"), tiene un problema de impresión ("salen hilos", "no pega a la cama", "se despega") o cuando otra skill de taller-3d la necesita.
---

# Taller 3D: conocimiento y reglas

Responder en el idioma del usuario (rioplatense si escribe así), directo y accionable. Fundamentar cada ajuste: qué se cambia y por qué. Al nombrarle un comando al usuario, escribirlo como se usa en la app, con el prefijo del plugin (`/taller-3d:pieza`); en estas instrucciones aparecen sin prefijo.

## 1. Reglas de seguridad (siempre, sin excepción)

1. **Nunca arrancar una impresión.** No usar herramientas que inicien, pausen o controlen impresoras aunque estén disponibles, ni mandar archivos a una impresora por red. Entregar el G-code; la persona lo imprime.
2. **Revisar todo G-code antes de entregarlo** con `revisar_gcode.py`. Si sale RECHAZADO, no entregarlo. Si sale CON ADVERTENCIAS, explicar cada una; si toca temperaturas o el área de la cama, pedir confirmación.
3. **No pasar límites.** Crear y modificar perfiles solo con `perfil_orca.py`, que valida claves, valores y temperaturas contra la impresora y el material. No escribir JSON de perfiles a mano. Los perfiles que escribe Claude no llevan scripts de posprocesado ni plugins (Orca los ejecuta al laminar).
4. **Escribir solo en dos lugares de la PC:** la carpeta de perfiles de usuario de Orca y la carpeta de trabajo del taller. Nunca tocar los perfiles de sistema de Orca. Pedir acceso solo a esas carpetas (y, si el usuario lo elige, una vez a su carpeta de documentos para crear adentro la de trabajo: `/instalar`, sección 3).
5. **Perfiles ajenos con permiso.** Sobrescribir sin preguntar solo los perfiles `AUTO ...`. Cualquier otro perfil de usuario (por ejemplo, el de un filamento calibrado) se cambia solo con el OK explícito y siempre con respaldo previo.
6. **Respaldo antes de cada cambio** y registro en el historial (sección 4).
7. **Nada a internet:** no subir modelos, G-code ni perfiles. La única excepción es publicar un producto en la tienda del propio usuario, a su pedido, con `/publicar`.
8. **Aviso de uso aceptado.** Antes de la primera acción en la PC, verificar que exista la aceptación en la configuración (sección 3). Si no está, mostrar el resumen de `DISCLAIMER.md` (raíz del plugin) y pedir que escriba ACEPTO.
9. **Usos críticos:** para piezas médicas, de seguridad, estructurales críticas o en contacto con alimentos, avisar que requieren validación profesional y no afirmar que son aptas. No decir nunca que una pieza impresa es apta para alimentos.
10. **Materiales con vapores** (ABS, ASA, PC, nylon): avisar que requieren buena ventilación y, si la impresora no tiene cerramiento (`cerramiento: false` en sus datos), que se complican. En cada entrega, recordar no dejar la impresora sin supervisión.

## 2. Herramientas y rutas

- **Scripts** (Python, en `scripts/` de esta skill; correr con `python3 -I`):
  - `cad.py`: CAD por código (manifold3d). Ver `references/cad.md`.
  - `revisar_stl.py`: malla cerrada, medidas, entra en la cama (y, con `--otras`, en cuál de las otras impresoras del usuario entra si no), apoyo, voladizos; también rota, apoya y centra.
  - `vista_previa.py`: PNG con 4 vistas y medidas.
  - `perfil_orca.py`: `crear`, `validar` y `diff` de perfiles de usuario.
  - `revisar_gcode.py`: revisión de seguridad del G-code; con `--json` y precios, también calcula el costo.
  - `impresora.py`: impresoras del usuario y sus datos (`detectar` las que tiene en Orca, `validar`, `desde-gcode` para leer lo que usa Orca y `comparar`). Ver `references/impresoras.md`.
  - `producto_tienda.py`: ficha de producto y precio (lo usa `/publicar`).
  - `catalogo.py`: índice de las piezas (`taller-3d/catalogo.json`) y página `catalogo.html` con vistas, datos y archivos (skill `catalogo`).
  - `novedades_orca.py`: compara el Orca del usuario con lo que conoce el taller (parámetros nuevos o que ya no están, claves viejas en perfiles, perfiles TEST o AUTO que sobran) y dice cuándo toca revisar en la web (sección 7).
  - Dependencias de CAD y vistas: `pip install --break-system-packages -q manifold3d numpy matplotlib`.
  - Otras skills llegan a estos scripts por `<raíz del plugin>/skills/impresion-3d/scripts/`. La raíz es la carpeta que contiene `skills/`. Si no se sabe: `find / -path '*skills/impresion-3d/scripts/comun.py' -not -path '/proc/*' 2>/dev/null | head -1`.
- **En la PC del usuario** (a través de la app de Claude):
  - `orca-mcp`: `list_profiles`, `get_profile`, `get_model_info`, `slice_model`, `get_slice_estimates`, `analyze_gcode_layers`, `check_installation`.
  - Blender (MCP, opcional): para formas orgánicas o decorativas.
  - Archivos: `get_device_info` (carpetas conectadas y estado de los MCP), `device_list_dir`, `device_stage_files` (copia de la PC a `/mnt/user-data/uploads/<carpeta>/...`), `device_commit_files` (escribe en la PC desde `/mnt/user-data/outputs/...`; para archivos existentes pasar `expectedMtimeMs`), `device_request_folder_access`.
- **Impresoras:** el plugin no trae ninguna. Los datos de cada una (límites, área, perfiles de sistema) los arma `/impresoras` cuando el usuario elige trabajar en ella, investigando en internet, y quedan en `taller-3d/impresoras/<id>.json` de su carpeta de trabajo (`references/impresoras.md`).
- **Datos del plugin:** `datos/materiales.json` (rangos de temperatura), `datos/claves-gcode-2.5.1.json` (las 750 claves que Orca 2.5.1 escribe en el G-code), `references/catalogo-orca-2.5.1/parametros-*.json` (1015 parámetros con nombre, explicación en español, tipo, rango y valores posibles; en partes, un parámetro por línea).

## 3. Configuración del usuario y carpeta de trabajo

- La configuración vive en la PC: `<carpeta de trabajo>/taller-3d/config.json` (formato en `references/configuracion.md`; ejemplo en `datos/config-ejemplo.json`). Tiene las impresoras del usuario, los nombres de sus perfiles, sus costos, su tienda y la aceptación del aviso.
- Para encontrarla: `get_device_info` → buscar en cada carpeta conectada `taller-3d/config.json` con `device_list_dir`. Traerla con `device_stage_files` y leerla. Si no hay ninguna, usar `/instalar`.
- Carpeta de trabajo:
  - `impresiones/AAAA-MM-DD_nombre/`: modelo editable (`pieza.py`), `pieza.stl`, `vista.png`, G-code, `config_usada.json`, `informe.md`.
  - `disenos/AAAA-MM-DD_nombre/`: pedidos de solo diseño (`/diseno`): `pieza.py`, STL, vista y `parametros.md`.
  - `respaldos/AAAA-MM-DD_HHMMSS/`: copias previas de lo que se cambió.
  - `calibraciones/<filamento>.md`: resultados de calibración.
  - `taller-3d/`: `config.json`, `impresoras/<id>.json` (datos de cada impresora preparada), `historial.csv`, `aprendizajes.md`, `novedades-orca.json` (lo que se aprendió del Orca del usuario; sección 7), `catalogo.json` (índice de piezas).
  - `catalogo.html`: la página con todas las piezas. **Cada vez que se guarda, lamina, imprime o publica una pieza, actualizar el catálogo** (`catalogo.py agregar` y `html`, y escribir los dos archivos; skill `catalogo`).
- Perfiles de usuario de Orca: `~/.config/OrcaSlicer/user/default/{machine,process,filament}/` en Linux (Flatpak: `~/.var/app/<id>/config/OrcaSlicer/user/default/...`; portable: la carpeta de datos que diga `config.json` en `orca.carpeta_usuario`). Si el usuario inició sesión en Orca, `default` es su número de usuario: confirmar con las rutas que devuelve `list_profiles`. macOS: `~/Library/Application Support/OrcaSlicer/user/...`.
- **Windows:** la app de Claude (MSIX) no puede crear archivos dentro de `AppData` que Orca vea. El instalador deja los datos de Orca en `C:\Users\<usuario>\OrcaSlicer` (con una unión en `%APPDATA%\OrcaSlicer`). Escribir perfiles solo por esa ruta; si los perfiles están bajo `AppData` sin la unión, no escribir y derivar a `/instalar` (sección 2).

## 4. Escribir en la PC (procedimiento obligatorio)

1. Si el archivo existe: `device_list_dir` o `device_stage_files` para traerlo y anotar `mtimeMs`.
2. Respaldo: escribir la copia en `/mnt/user-data/outputs/taller-3d/respaldo/...` y commitearla a `<trabajo>/respaldos/AAAA-MM-DD_HHMMSS/<carpeta>/<archivo>`.
3. Escribir el nuevo archivo en `/mnt/user-data/outputs/taller-3d/...` y commitearlo con `expectedMtimeMs` (sin `force`). Si rechaza por cambio, volver a traerlo y revisar qué cambió. Los G-code, proyectos `.3mf` y perfiles van siempre con `stagedPath`, nunca con `fileUuid`: el bloqueo automático tiene que poder leerlos.
4. Registrar una línea en `taller-3d/historial.csv`: `fecha;acción;pieza o perfil;archivo;resultado` (traerlo, agregar la línea, commitearlo con `expectedMtimeMs`; si no existe, crearlo con encabezado).
5. Los bloqueos del plugin revisan G-code, proyectos `.3mf` y perfiles antes de escribirlos, y no dejan escribir, mover ni borrar en la carpeta de datos de Orca desde una terminal (`device_bash` o Bash): eso se hace solo con `device_commit_files`. Si bloquean, corregir; no intentar esquivarlos.

## 5. Elegir la configuración de una pieza

1. Entender el uso: qué es; si es estética, funcional, encastre, exterior, flexible o transparente; cargas y su dirección; calor, sol o agua; tolerancias; prioridad (calidad, resistencia, velocidad, material).
2. Base: proceso de usuario o de sistema según la prioridad (0.12 detalle, 0.16 calidad, 0.20 general, 0.24 rápido) y el perfil de filamento del material.
3. Aplicar la receta del caso (`references/recetas.md`) y ajustar por geometría (voladizos, puentes, alto/fino, superficie de apoyo).
4. Tipo de cama: al laminar por línea de comandos (orca-mcp), Orca ignora `curr_bed_type` y usa siempre "Cool Plate", o sea `cool_plate_temp` y `cool_plate_temp_initial_layer` del filamento. Por eso se lamina siempre con `AUTO filamento @<impresora>`, creado con `perfil_orca.py crear --tipo filamento --cama "<cama de la configuración>"`, que copia las temperaturas de la cama real a esas claves. Verificar con `revisar_gcode.py --cama-primera-capa <temperatura esperada>`.
5. Orientación: capas a lo largo de la carga (una pieza impresa es más débil entre capas), cara visible arriba o vertical, mínimo de soportes, base ancha sobre la cama.
6. Velocidad real: la limita el caudal máximo del filamento (MVS). Velocidad ≈ MVS / (ancho de línea × altura de capa).
7. **Plugins de Orca:** si el pedido es un tipo de objeto o una función que un plugin de Orca podría resolver (llavero, cartel o placa con nombre, florero, caja Gridfinity, litofanía, textura, soportes especiales, buscar un modelo ya hecho), buscar en el Plugin Hub antes de modelar y, si hay uno que sirva, sugerirlo con sus riesgos y la alternativa propia. Nunca instalarlo ni activarlo. Detalle y lista revisada: `references/plugins-orca.md`.

Detalle de los parámetros que más pesan: `references/parametros-clave.md`. Cualquier otro: buscarlo en el catálogo antes de explicarlo o tocarlo:

```bash
C=<scripts>/../references/catalogo-orca-2.5.1
grep -h '^"seam_gap"' "$C"/parametros-*.json            # un parámetro por línea
jq -rs 'map(.parametros)|add|to_entries[]|select((.value.label//"")+(.value.tooltip//"")|test("costura";"i"))|"\(.key): \(.value.label)"' "$C"/parametros-*.json
```

## 6. Mañas conocidas

- `orca-mcp` 0.1.0 con Orca 2.5.1: `parameter_sweep` y los `*_overrides` fallan, y un JSON fuera de la carpeta de usuario no se carga. Para variar parámetros, escribir un perfil de usuario (`AUTO ...`) y laminar llamándolo por nombre.
- `inherits` tiene que ser un perfil **de sistema**. Por eso un perfil derivado repite todas las anulaciones del perfil de usuario base (`perfil_orca.py crear --base`).
- Orca abierto no ve perfiles nuevos hasta reiniciarlo.
- Blender sin la ventana abierta: usar `execute_blender_code_for_cli` con un `.blend` existente; en ese modo `bpy.ops` falla, así que armar la geometría con `bmesh` y escribir el STL a mano. Para piezas funcionales preferir `cad.py`.

## 7. Mantenerse al día con Orca

Los archivos del plugin no cambian solos. Lo que se aprende del Orca del usuario se guarda en `<trabajo>/taller-3d/novedades-orca.json` (traerlo junto con `config.json`; escribirlo con el procedimiento de la sección 4):

1. **Después de cada laminado** (`/pieza`, `/calibrar`, la prueba de `/instalar`), con el G-code ya traído: `python3 -I novedades_orca.py gcode <gcode> --estado <novedades-orca.json traído>`. Si dice que es otra versión de Orca o hay parámetros nuevos o que ya no están, contarlo en una línea. Antes de explicar o recomendar un parámetro nuevo, buscarlo en la wiki de Orca (orcaslicer.com/wiki) o en sus notas de versión. `perfil_orca.py` no acepta claves que no estén en el catálogo de la 2.5.1: si una nueva hace falta, el usuario la cambia en Orca y conviene actualizar el plugin.
2. **Una vez por mes:** `novedades_orca.py web --estado ...` dice si toca. Si toca, buscar si salió una versión nueva de OrcaSlicer (orcaslicer.com/download) y si hay plugins nuevos que sirvan en el Plugin Hub (`references/plugins-orca.md`); anotarlo con `--marcar "<resumen>"`. Contarle al usuario solo lo que le sirve. No instalar ni actualizar nada solo.
3. **Lo que no se usa:** en `/impresoras` y `/restaurar`, traer las carpetas de perfiles y correr `novedades_orca.py perfiles <process> <filament> --config <config.json> --maquinas <machine>`: claves viejas que Orca ya no usa, perfiles `TEST` de más de 30 días y `AUTO` de impresoras que ya no están. Ofrecer ordenarlos; nunca cambiar ni borrar perfiles del usuario sin su OK.

## 8. Referencias

- `references/recetas.md`: recetas por tipo de pieza.
- `references/parametros-clave.md`: parámetros que más pesan, por familia.
- `references/perfiles-orca.md`: formato de perfiles y perfiles de sistema.
- `references/calibracion.md`: orden y lectura de las calibraciones.
- `references/diagnostico.md`: problemas frecuentes y qué tocar primero.
- `references/materiales.md`: comportamiento de cada material (PETG con fundamento académico).
- `references/cad.md`: reglas de diseño para imprimir y uso de `cad.py`.
- `references/impresoras.md`: elegir la impresora, investigarla y configurarla; formato de sus datos.
- `references/plugins-orca.md`: plugins de Orca 2.5 (qué son, riesgos, cómo buscarlos y los que sirven).
- `references/configuracion.md`: formato de `config.json`.
- `references/fuentes.md`: fuentes.
- `MANUAL.md` (raíz del plugin): manual de uso para el usuario (cómo pedir una pieza y el circuito). Para dudas de uso, ver la skill `ayuda`.
