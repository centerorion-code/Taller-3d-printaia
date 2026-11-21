# Diseñar piezas para imprimir con `cad.py`

`cad.py` arma sólidos cerrados (manifold) con medidas exactas. Usarlo para piezas funcionales: soportes, cajas, tapas, adaptadores, plantillas, ganchos, separadores. Para formas orgánicas o decorativas usar Blender o un modelo existente.

## Reglas de diseño para FDM (boquilla 0,4)

- **Paredes:** mínimo 1,2 mm (3 líneas); 2 mm o más en piezas que trabajan.
- **Voladizos:** hasta 45° desde la vertical sin soporte. Cambiar techos planos por chaflanes a 45° o forma de gota en agujeros horizontales.
- **Puentes:** hasta 10-20 mm según el material y el ventilador; más largos llevan soporte.
- **Agujeros verticales:** salen ~0,1-0,2 mm más chicos: usar las medidas de `TORNILLOS` (ya tienen holgura) o sumar holgura.
- **Encastres:** holgura por lado según `holgura(tipo, material)`; calibrar con el test de tolerancia y anotar el resultado en `aprendizajes.md`.
- **Base:** chaflán de 0,4-0,6 mm abajo (`chaflan_inferior`) contra la pata de elefante.
- **Esquinas internas:** redondeos o chaflanes reducen la concentración de tensión.
- **Resistencia:** la pieza es más débil entre capas; orientar para que la carga quede en el plano de las capas.
- **Texto en relieve o bajo relieve:** mínimo 5 mm de alto y 0,6 mm de profundidad (`cad.py` no hace texto: usar Blender).
- **Piezas más grandes que la cama:** partir con encastres o tornillos.

## API

```python
import sys
sys.path.insert(0, "<scripts>")
from cad import *

caja(x, y, z, radio=0, centrada=False)      # aristas verticales redondeadas con radio
cilindro(d, h, d_arriba=None)               # eje en el origen, base en Z=0
cono(d_base, h, d_punta=0); esfera(d); tubo(d_ext, d_int, h)
prisma([(x, y), ...], h)                    # polígono extruido
ranura(largo, ancho, h)                     # agujero chino a lo largo de X
revolucion([(r, z), ...], grados=360)       # perfil girado alrededor de Z
hexagono(entre_caras, h)
agujero(d, h, holgura_mm=0)                 # para restar
agujero_tornillo("M3", largo, tipo="pasante"|"rosca_plastico", cabeza=None|"cilindrica"|"avellanada")
alojamiento_tuerca("M3", profundidad=None)
agujero_inserto("M3", profundidad)          # insertos de latón con calor
chaflan_inferior(solido, mm=0.4)
unir(a, b, ...); restar(base, r1, r2, ...); intersectar(a, b)
mover(s, x, y, z); rotar(s, x, y, z); espejar(s, "x"); escalar(s, f)
apoyar(s); centrar(s, impresora=datos)  # o centrar(s, x, y); medidas(s)
exportar_stl(s, "pieza.stl")                # valida, limpia y apoya en Z=0
holgura("presion"|"justo"|"deslizante"|"giratorio", "PETG")
TORNILLOS["M4"]["pasante"]                  # medidas de tornillos y tuercas
```

## Plantilla de `pieza.py`

Cada pieza se guarda como script editable al lado del STL, con los parámetros arriba:

```python
#!/usr/bin/env python3
"""<Nombre de la pieza>: <para qué sirve>. Generado por taller-3d.

Editá PARAMETROS y corré:  python3 pieza.py pieza.stl
"""
import sys
from pathlib import Path

sys.path.insert(0, "<scripts>")
from cad import *

PARAMETROS = dict(
    ancho=60.0,       # mm
    fondo=30.0,
    espesor=5.0,
    material="PETG",
)


def construir(p):
    base = caja(p["ancho"], p["fondo"], p["espesor"], radio=3)
    ...
    return chaflan_inferior(base, 0.4)


if __name__ == "__main__":
    salida = Path(sys.argv[1] if len(sys.argv) > 1 else "pieza.stl")
    print(exportar_stl(construir(PARAMETROS), salida))
```

## Verificar siempre

1. `revisar_stl.py pieza.stl --material <m> --esperado <AxBxC>`: cerrada, medidas, entra en la cama, apoyo y voladizos.
2. `vista_previa.py pieza.stl vista.png --titulo "<nombre>"` y mostrarla antes de laminar.
3. Si es un encastre, comparar con las medidas reales que dio el usuario (no inventar medidas: si falta una, preguntarla).
