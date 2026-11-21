# Materiales

Rangos de temperatura que usa el revisor: `datos/materiales.json`. Siempre manda la ficha del fabricante del rollo.

## PETG (con fundamento)

- **Rugosidad en paredes:** en PETG, el flujo explica el 43,7 % de la variación y la velocidad el 16,8 %; entre 240-250 °C y 0,16-0,24 mm de capa, ni la temperatura ni la capa fueron significativas (Barrios y Romero, 2019). Por eso: calibrar flujo primero y bajar la velocidad de pared externa para calidad.
- **Cara superior:** pesa la aceleración: 2000 mm/s² o menos para caras visibles.
- **Óptimo de rugosidad y error dimensional** en un estudio: 50 mm/s, capa 0,1 mm, 230 °C, ancho 0,6 mm (Mishra y otros, 2023).
- **Resistencia:** más temperatura y menos ventilador dan mejor unión entre capas; capas de 0,12-0,20 también ayudan (Tunçel y otros, 2024, en flexión).
- **Práctico:** absorbe humedad (secar a 65 °C 4-6 h si hay hilos o burbujas); ventilador 30-50 %, 0 en las primeras 3 capas; se pega de más al PEI liso (usar pegamento en barra como separador).

## PLA

- Fácil, detallado, rígido. Se ablanda desde ~55 °C: nunca para autos, sol ni cerca de calor.
- Ventilador alto. Cama 55-60 °C.

## TPU (flexible)

- Lento, retracción corta y lenta, sin z-hop. Absorbe humedad.
- En extrusor directo se imprime bien a 20-35 mm/s.

## ABS y ASA

- Más resistencia al calor (ABS ~85 °C, ASA similar y además resiste el sol).
- Emiten vapores: imprimir solo con buena ventilación.
- Sin cerramiento se agrietan y despegan: en impresoras abiertas, piezas chicas, brim y sin corrientes de aire.

## PC y nylon (PA)

- Necesitan cerramiento, cama alta y filamento muy seco. No recomendados en impresoras abiertas.

## Con fibra de carbono (PLA-CF, PETG-CF)

- Abrasivos: requieren boquilla endurecida. Más rígidos y con terminación mate.

## Uso alimentario

Ninguna pieza impresa por FDM se considera apta para alimentos sin un proceso y material certificados: las líneas de capa acumulan bacterias y los pigmentos o aditivos pueden no ser aptos. No afirmarlo nunca.
