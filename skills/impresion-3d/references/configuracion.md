# Configuración del usuario (`taller-3d/config.json`)

Vive en la PC del usuario, dentro de la carpeta de trabajo. El plugin no guarda datos personales: todo lo propio del usuario está acá. Ejemplo completo en `datos/config-ejemplo.json`.

```json
{
  "version": 1,
  "carpeta_trabajo": "/home/usuario/Documentos/Taller 3D",
  "aceptacion": {"fecha": "2026-11-21T10:00:00-03:00", "version_plugin": "0.1.12", "texto": "ACEPTO", "medio": "instalar.sh"},
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
      "filamentos": {"PETG": "…", "PLA": "…"}
    }
  ],
  "costos": {"moneda": "ARS", "precio_kwh": 150, "consumo_w": 180,
             "filamentos": {"PETG": {"precio_kg": 25000}}},
  "tienda": {"plataforma": "woocommerce", "url": "https://mitienda.com", "margen_pct": 60,
             "costo_hora_maquina": 300, "embalaje": 400, "redondeo": 100, "demora_dias": 3,
             "peso_embalaje_g": 50, "categoria_por_defecto": "Piezas a medida"}
}
```

## Campos

- `orca`: qué Orca usa el taller. `origen`: `oficial` (lo instaló el instalador), `appimage`, `flatpak`, `sistema`, `instalado` (Windows), `portable` o `indicado` (lo pasó el usuario con `--orca`/`-Orca`). `carpeta_usuario`: carpeta de sus perfiles; en Windows queda fuera de AppData (`C:\Users\<usuario>\OrcaSlicer\user\default`).
- `impresoras`: solo las que el usuario eligió para trabajar (no todas las de Orca). `impresora_por_defecto`: la última usada; se ofrece primera cuando hay varias.
- `datos`: ruta, relativa a la carpeta de trabajo, al JSON con los datos de la impresora en `taller-3d/impresoras/`. Lo arma `/impresoras` investigando en internet (formato en `references/impresoras.md`); el plugin no trae impresoras.
- `cama`: tipo de cama que usa, con el nombre de Orca ("Textured PEI Plate", "High Temp Plate", "Cool Plate"…). El taller copia sus temperaturas al `AUTO filamento` (ver perfiles-orca.md, tipo de cama).
- `procesos` y `filamentos`: nombres de los perfiles de usuario de Orca (las claves son libres; las de `filamentos` conviene que sean el material).
- `costos.filamentos`: precio por kg por material (PETG) o por nombre de perfil de filamento.
- `consumo_w`: consumo promedio de la impresora mientras imprime (180 W es una estimación; medirlo con un medidor mejora el costo).
- `tienda.plataforma`: `woocommerce`, `tiendanube`, `shopify`, `mercadolibre`, `otra` o null.

## Reglas

- Los valores `null` se preguntan la primera vez que hacen falta y se guardan.
- Cambiar la configuración con el procedimiento de escritura (respaldo + `expectedMtimeMs`).
- No guardar contraseñas ni claves en este archivo.

## Novedades de Orca (`taller-3d/novedades-orca.json`)

Lo escribe `novedades_orca.py` (skill `impresion-3d`, sección 7): versión de Orca vista en los G-code, parámetros nuevos o que ya no están (con la fecha en que aparecieron), fecha de la última revisión en la web y notas cortas de esa revisión. No tiene datos personales. Si se borra, se vuelve a armar en el próximo laminado.
