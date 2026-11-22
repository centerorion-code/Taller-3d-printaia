#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
# Desinstalador de taller-3d para Linux.
#
# Quita solo lo que anotó instalar.sh en ~/.local/state/taller-3d/instalado.txt:
# el AppImage de Orca, el acceso directo, el lanzador, orca-mcp y la entrada en la app de Claude.
# Todo va a la papelera (se puede recuperar). La carpeta de trabajo (tus piezas, respaldos y
# configuración) y tus perfiles de Orca NO se tocan, salvo que pases --todo y lo confirmes.
#
# Uso:
#   bash desinstalar.sh [--prueba] [--todo]
set -euo pipefail

PRUEBA=0
TODO=0
for a in "$@"; do
  case "$a" in
    --prueba) PRUEBA=1 ;;
    --todo) TODO=1 ;;
    -h|--help) sed -n '4,12p' "$0"; exit 0 ;;
    *) echo "Opción desconocida: $a" >&2; exit 2 ;;
  esac
done

MANIFIESTO="$HOME/.local/state/taller-3d/instalado.txt"
[ -f "$MANIFIESTO" ] || { echo "No encontré $MANIFIESTO: no hay nada instalado por instalar.sh."; exit 0; }
QUITADOS="$HOME/taller-3d-quitado-$(date +%Y%m%d-%H%M%S)"

# Solo se quitan rutas dentro de tu carpeta personal, nunca la carpeta personal entera ni los datos de Orca.
ruta_segura() {
  local r
  r="$(realpath -m -- "$1" 2>/dev/null)" || return 1
  case "$r/" in
    "$HOME/"|"$HOME/.config/OrcaSlicer/"*|"$HOME/.var/app/"*) return 1 ;;
    "$HOME/"*) return 0 ;;
    *) return 1 ;;
  esac
}

# A la papelera; si no hay papelera (o el archivo está en otro disco), a una carpeta en tu casa.
a_papelera() {
  if command -v gio >/dev/null 2>&1 && gio trash -- "$1" 2>/dev/null; then
    echo "A la papelera: $1"
  elif command -v trash-put >/dev/null 2>&1 && trash-put -- "$1" 2>/dev/null; then
    echo "A la papelera: $1"
  else
    mkdir -p "$QUITADOS"
    mv -- "$1" "$QUITADOS/" && echo "Movido a $QUITADOS: $1"
  fi
}

# La app de Claude reescribe su configuración al cerrarse: hay que tocarla con la app cerrada.
app_de_claude_abierta() {
  pgrep -u "$(id -u)" -f '(^|/)(claude-desktop|Claude)( |$)' >/dev/null 2>&1 \
    || pgrep -u "$(id -u)" -x 'claude-desktop|Claude' >/dev/null 2>&1
}

echo "== Esto es lo que instaló taller-3d:"
PAQUETES=()
while IFS=$'\t' read -r tipo valor <&3; do
  [ -n "$tipo" ] || continue
  case "$tipo" in
    carpeta) [ "$TODO" -eq 1 ] && echo "   carpeta de trabajo (con --todo): $valor" || echo "   (se conserva) carpeta de trabajo: $valor" ;;
    carpeta-usada) echo "   (se conserva) carpeta de trabajo que ya tenías: $valor" ;;
    apt) PAQUETES+=("$valor") ;;
    *) echo "   $tipo: $valor" ;;
  esac
done 3< "$MANIFIESTO"
if [ "${#PAQUETES[@]}" -gt 0 ]; then
  echo "   (se conservan) paquetes del sistema que instaló: ${PAQUETES[*]}"
  echo "   Otros programas pueden usarlos; si querés sacarlos: sudo apt remove ${PAQUETES[*]}"
fi

if [ "$PRUEBA" -eq 1 ]; then echo "Modo prueba: no cambié nada."; exit 0; fi
read -r -p "¿Lo quito? Va todo a la papelera. Escribí QUITAR para confirmar: " r
[ "$r" = "QUITAR" ] || { echo "No cambié nada."; exit 0; }

APP_ABIERTA=0
if grep -qE $'^mcp-app(-orca)?\t' "$MANIFIESTO"; then
  while app_de_claude_abierta; do
    read -r -p "Cerrá la app de Claude del todo (Salir desde el ícono de la bandeja) y apretá Enter, o escribí SALTEAR: " r
    [ "$r" = "SALTEAR" ] && break
  done
  app_de_claude_abierta && APP_ABIERTA=1
fi

while IFS=$'\t' read -r tipo valor <&3; do
  [ -n "$tipo" ] || continue
  case "$tipo" in
    archivo)
      if ! ruta_segura "$valor"; then echo "No toco '$valor': está fuera de tu carpeta personal."
      elif [ -e "$valor" ] || [ -L "$valor" ]; then a_papelera "$valor" || echo "No pude quitar $valor."
      fi ;;
    uv)
      if command -v uv >/dev/null && uv tool uninstall "$valor" >/dev/null 2>&1; then echo "Quitado: $valor"
      else echo "No pude quitar $valor con uv (quizás ya no estaba)."; fi ;;
    pipx)
      if command -v pipx >/dev/null && pipx uninstall "$valor" >/dev/null 2>&1; then echo "Quitado: $valor"
      else echo "No pude quitar $valor con pipx (quizás ya no estaba)."; fi ;;
    flatpak-permiso)
      IFS='|' read -r id carpeta <<<"$valor"
      if command -v flatpak >/dev/null && flatpak override --user --nofilesystem="$carpeta" "$id"; then
        echo "Quitado el permiso de $id para $carpeta"
      fi ;;
    mcp-app|mcp-app-orca)
      # mcp-app: la entrada orca-mcp; mcp-app-orca: la de taller3d-orca (abrir Orca desde Claude y el panel)
      if [ "$tipo" = mcp-app ]; then entrada=orca-mcp; else entrada=taller3d-orca; fi
      if ! ruta_segura "$valor"; then echo "No toco '$valor': está fuera de tu carpeta personal."
      elif [ "$APP_ABIERTA" -eq 1 ]; then
        echo "No toqué la configuración de la app (seguía abierta): con la app cerrada, sacá a mano la entrada \"$entrada\" de $valor."
      elif [ -f "$valor" ]; then
        cp -- "$valor" "$valor.respaldo-$(date +%Y%m%d-%H%M%S)"
        if python3 - "$valor" "$entrada" <<'EOF_PY'
import json, sys
ruta, entrada = sys.argv[1], sys.argv[2]
with open(ruta, encoding="utf-8") as f:
    datos = json.load(f)
servidores = datos.get("mcpServers") if isinstance(datos, dict) else None
if isinstance(servidores, dict):
    servidores.pop(entrada, None)
with open(ruta, "w", encoding="utf-8") as f:
    json.dump(datos, f, ensure_ascii=False, indent=2)
EOF_PY
        then echo "Quitado $entrada de la app de Claude (respaldo al lado). Abrí la app de nuevo."
        else echo "No pude editar $valor: sacá a mano la entrada \"$entrada\" (hay un respaldo al lado)."; fi
      fi ;;
    carpeta)
      if [ "$TODO" -eq 1 ] && [ -d "$valor" ]; then
        if ! ruta_segura "$valor"; then echo "No toco '$valor': está fuera de tu carpeta personal."
        else
          read -r -p "¿Mando también la carpeta de trabajo '$valor' a la papelera? Escribí SI: " s
          if [ "$s" = "SI" ]; then a_papelera "$valor" || echo "No pude quitar $valor."; fi
        fi
      fi ;;
  esac
done 3< "$MANIFIESTO"

a_papelera "$MANIFIESTO" >/dev/null 2>&1 || true
echo "Listo. Tus perfiles de Orca (~/.config/OrcaSlicer) quedaron como estaban."
echo "El plugin se quita desde la configuración de plugins de la app de Claude."
