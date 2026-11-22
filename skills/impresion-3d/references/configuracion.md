# Configuración del usuario (`taller-3d/config.json`)

Vive en la PC del usuario, dentro de la carpeta de trabajo. El plugin no guarda datos personales: todo lo propio del usuario está acá. Ejemplo completo en `datos/config-ejemplo.json`.

```json
{
  "version": 1,
  "carpeta_trabajo": "/home/usuario/Documentos/Taller 3D",
  "aceptacion": {"fecha": "2026-11-21T10:00:00-03:00", "version_plugin": "0.1.30", "texto": "ACEPTO", "medio": "instalar.sh"},
  "orca": {"version": "2.5.1", "ejecutable": "/home/usuario/Aplicaciones/OrcaSlicer_Linux_AppImage_Ubuntu2404_V2.5.1.AppImage",
           "origen": "oficial", "carpeta_usuario": "/home/usuario/.config/OrcaSlicer/user/default"},
  "impresora_por_defecto": "marca-modelo",
  "impresoras": [
    {
      "id": "marca-modelo",
      "nombre": "Mi Marca Modelo",
      "datos": "taller-3d/impresoras/marca-modelo.json",
      "perfil_maquina": "Mi Modelo 0.4 nozzle",
      "cama": "Textured PEI Plate",
      "proceso_auto": "AUTO proceso @Modelo",
      "filamento_auto": "AUTO filamento @Modelo",
      "procesos": {"calidad": "…", "eficiente": "…", "estandar": "…"},
      "filamentos": {"PETG": "…", "PLA": "…"},
      "costo": {"precio": 600000, "vida_horas": 4000, "mantenimiento_pct": 5, "consumo_w": 145,
                "consumo_fuente": "estimado: cama de 300 × 300 mm, imprimiendo PLA; potencia nominal 350 W (https://…)",
                "consumo_fecha": "2026-11-22", "potencia_nominal_w": 350, "calentamiento_min": 5}
    }
  ],
  "costos": {"moneda": "ARS",
             "luz": {"precio_kwh": 152.9, "metodo": "marginal", "cargo_variable": 120.5, "impuestos_pct": 26.9,
                     "kwh": 310, "total": 53072, "cargos_fijos": 4800, "periodo": "2026-10", "empresa": "EDET",
                     "cargado": "2026-11-21"},
             "precio_kwh": 152.9,
             "fallas_pct": 10,
             "mano_de_obra": {"precio_hora": 6000, "minutos_por_pieza": 10},
             "filamentos": {"PETG": {"precio_kg": 25000}}},
  "tienda": {"plataforma": "mercadolibre", "url": "https://mitienda.com", "margen_precio_pct": 40,
             "canales": {"tienda": {"nombre": "Tu tienda", "comision_pct": 0},
                         "mercadolibre": {"nombre": "Mercado Libre", "comision_pct": 15, "iva_comision": true,
                                          "cargo_fijo": 1000, "cargo_fijo_hasta": 20000}},
             "embalaje": 400, "redondeo": 100, "demora_dias": 3, "peso_embalaje_g": 50,
             "categoria_por_defecto": "Piezas a medida"},
  "impuestos": {"condicion": "monotributo", "ingresos_brutos_pct": 3.5},
  "generadores_ia": {"hunyuan": true, "imagenes": "gemini", "textos": "gemini"}
}
```

## Campos

- `orca`: qué Orca usa el taller. `origen`: `oficial` (lo instaló el instalador), `appimage`, `flatpak`, `sistema`, `instalado` (Windows), `portable` o `indicado` (lo pasó el usuario con `--orca`/`-Orca`). `carpeta_usuario`: carpeta de sus perfiles; en Windows queda fuera de AppData (`C:\Users\<usuario>\OrcaSlicer\user\default`).
- `impresoras`: solo las que el usuario eligió para trabajar (no todas las de Orca). `impresora_por_defecto`: la última usada; se ofrece primera cuando hay varias y es la que queda elegida en el selector "Imprimir en" del panel. El selector suma las impresoras de Orca que no están en `impresoras` (`impresora.py detectar`): se preparan la primera vez que se eligen para una pieza.
- `datos`: ruta, relativa a la carpeta de trabajo, al JSON con los datos de la impresora en `taller-3d/impresoras/`. Lo arma `/impresoras` investigando en internet (formato en `references/impresoras.md`); el plugin no trae impresoras.
- `cama`: tipo de cama que usa, con el nombre de Orca ("Textured PEI Plate", "High Temp Plate", "Cool Plate"…). El taller copia sus temperaturas al `AUTO filamento` (ver perfiles-orca.md, tipo de cama).
- `procesos` y `filamentos`: nombres de los perfiles de usuario de Orca (las claves son libres; las de `filamentos` conviene que sean el material).
- `impresoras[].costo`: lo de cada impresora para el costo (precio, vida en horas, mantenimiento %, consumo promedio en W, minutos de calentamiento). El consumo lo guarda `costos.py consumo`: `consumo_fuente` empieza con de dónde salió (`medido`, `oficial`, `prueba publicada`, `usuario` o `estimado`) y sigue con el enlace o el detalle; `consumo_fecha` y `potencia_nominal_w` (la de la ficha, que es el máximo) son para referencia. Detalle en `references/costos.md`.
- `costos.luz`: los números de la tarifa de la boleta de luz, que guarda `costos.py luz` (solo números, nada personal). `costos.precio_kwh` queda igual que `luz.precio_kwh` para los scripts viejos.
- `costos.filamentos`: precio por kg por material (PETG) o por nombre de perfil de filamento.
- `costos.fallas_pct` y `costos.mano_de_obra`: el porcentaje de impresiones que salen mal y lo que vale tu hora.
- `costos.consumo_w` (de antes de la 0.1.14): consumo general si una impresora no tiene el suyo.
- `tienda.plataforma`: `woocommerce`, `tiendanube`, `shopify`, `mercadolibre`, `otra` o null.
- `tienda.margen_precio_pct`: el margen habitual sobre el precio. El `margen_pct` de antes era un recargo sobre el costo: `costos.py` lo convierte y avisa.
- `tienda.canales`: comisión, cuotas, IVA sobre la comisión y cargo fijo de cada canal de venta (`references/costos.md`).
- `tienda.costo_hora_maquina` (de antes de la 0.1.14): se usa solo si la impresora no tiene precio.
- `tienda.margen_escalones` (opcional): margen según el costo de la pieza, `[{"hasta": 5000, "margen_pct": 60}, {"hasta": 20000, "margen_pct": 50}, {"margen_pct": 40}]` (el último sin `hasta` cubre lo más caro). `tienda.precio_minimo_pieza` (opcional): el precio mínimo de cualquier pieza. Los guarda `costos.py margen`.
- `impuestos`: cómo factura y qué paga por cada venta (`references/costos.md`, «Impuestos de la venta»). `condicion`: `monotributo`, `responsable_inscripto`, `exento` o `sin_facturar`. `ingresos_brutos_pct` y `otros_pct`: % sobre la venta (sin IVA). Solo responsable inscripto: `iva_pct` (21 si falta) e `iva_descontable` (lista de `material`, `maquina`, `embalaje`, `luz`: las compras cuyo IVA descuenta). Lo guarda `costos.py impuestos`.
- `generadores_ia` (opcional): para hacer piezas desde una foto (`references/foto-a-3d.md`). `hunyuan`: si tiene cuenta en Hunyuan 3D (la sesión queda en su Chrome; acá no se guarda nada de la cuenta). `imagenes`: con qué genera imágenes cuando no hay foto o faltan ángulos, `gemini`, `flow` o null. `textos`: quién escribe los textos de venta en `/publicar`, `gemini` (su Gemini gratis, revisado por Claude: `references/textos-con-gemini.md`) o `claude` (lo mismo si falta). Si falta algo, se pregunta la primera vez que hace falta.
- `vista_previa_claude` (opcional): la página de claude.ai donde `/publicar` muestra la vista previa de la publicación (`{"slug": "…", "url": "…"}`); se reusa en cada producto.

## Reglas

- Los valores `null` se preguntan la primera vez que hacen falta y se guardan.
- Cambiar la configuración con el procedimiento de escritura (respaldo + `expectedMtimeMs`).
- No guardar contraseñas ni claves en este archivo.

## Novedades de Orca (`taller-3d/novedades-orca.json`)

Lo escribe `novedades_orca.py` (skill `impresion-3d`, sección 7): versión de Orca vista en los G-code, parámetros nuevos o que ya no están (con la fecha en que aparecieron), fecha de la última revisión en la web y notas cortas de esa revisión. No tiene datos personales. Si se borra, se vuelve a armar en el próximo laminado.
