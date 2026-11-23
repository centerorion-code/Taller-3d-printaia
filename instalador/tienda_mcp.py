#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
"""taller3d-tienda: servidor MCP local (stdio, solo biblioteca estándar) que carga productos en la tienda WooCommerce
del usuario, SIEMPRE como borrador.

Herramientas:
  cargar_borrador(carpeta)  lee <carpeta de la pieza>/producto/publicacion.json (lo arma /publicar), sube sus fotos y
                            crea o actualiza el producto como borrador. Un producto que ya está publicado no se toca.
  estado_tienda()           dice si la tienda está conectada y responde. No cambia nada.

Nunca publica, no borra, no toca pedidos, clientes ni otros productos. Habla solo con la tienda guardada (https) y no
sigue redirecciones (no le manda la contraseña a otro sitio).

Lo arranca la app de escritorio de Claude (entrada "taller3d-tienda" de claude_desktop_config.json, que escribe el
instalador). La configuración sale solo de esa entrada y del archivo de credenciales, nunca de la herramienta:
  TALLER3D_CARPETA       carpeta de trabajo (ruta absoluta).
  TALLER3D_CREDENCIALES  (opcional) el archivo con la tienda, el usuario y la contraseña de aplicación. Por defecto
                         ~/.config/taller-3d/credenciales-tienda.json (Windows: %APPDATA%\\taller-3d\\...).

La contraseña de aplicación (se crea en WordPress: Usuarios → Perfil → Contraseñas de aplicación) la guarda el
usuario una vez, en una terminal, con:  python3 tienda_mcp.py configurar
Nunca pasa por el chat. El archivo queda solo para su usuario (permisos 600).

Escribe un solo archivo: <carpeta de la pieza>/producto/tienda.json (número del producto, enlaces y las fotos ya
subidas, para no subirlas dos veces). Sin la contraseña.
"""
from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

NOMBRE = "taller3d-tienda"
VERSION = "0.1.0"
INFO = {"name": NOMBRE, "title": "Taller 3D: cargar en la tienda", "version": VERSION}
VERSIONES_MODERNAS = ("2026-07-28",)
VERSIONES_LEGADAS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
META_VERSION = "io.modelcontextprotocol/protocolVersion"
META_CAPACIDADES = "io.modelcontextprotocol/clientCapabilities"
META_SERVIDOR = "io.modelcontextprotocol/serverInfo"

ARCHIVO_CREDENCIALES = "credenciales-tienda.json"
ESTADO = "tienda.json"                 # en <pieza>/producto/
MAX_RUTA = 1024
MAX_PUBLICACION = 2 * 1024 * 1024
MAX_CREDENCIALES = 64 * 1024
MAX_FOTO = 15 * 1024 * 1024
MAX_FOTOS = 10
MAX_ETIQUETAS = 10
MAX_RESPUESTA = 8 * 1024 * 1024
REPETIDO_S = 20.0
TIPOS_FOTO = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
ESTADOS = {"draft": "borrador", "publish": "publicado", "pending": "pendiente de revisión", "private": "privado",
           "future": "programado"}

SIN_CONECTAR = ("La tienda todavía no está conectada. Hacelo una sola vez, en una terminal de la PC: "
                "python3 ~/.local/share/taller-3d/tienda_mcp.py configurar (te pide la dirección de la tienda, tu "
                "usuario de WordPress y una contraseña de aplicación).")

INSTRUCCIONES = (
    "Servidor local del taller 3D (plugin taller-3d) para la tienda WooCommerce del usuario. cargar_borrador carga "
    "como BORRADOR, con sus fotos, la publicación que /publicar armó en <carpeta de la pieza>/producto/"
    "publicacion.json; si el producto ya está publicado, no lo toca. Usala cuando el usuario pida cargar una "
    "publicación en su tienda, también desde el panel. estado_tienda dice si la tienda está conectada. Nunca "
    "publica: publicar es siempre del usuario, desde su tienda.")

HERRAMIENTAS = [
    {
        "name": "cargar_borrador",
        "title": "Cargar un producto en la tienda, como borrador",
        "description": (
            "Carga en la tienda WooCommerce del usuario, como BORRADOR, el producto que /publicar armó para una "
            "pieza: lee <carpeta>/producto/publicacion.json, sube sus fotos y crea el producto o actualiza el "
            "borrador que ya tenga el mismo SKU. Si ese producto ya está publicado, no lo toca. Nunca publica. "
            "`carpeta`: la de la pieza, relativa a la carpeta de trabajo del taller (por ejemplo "
            "impresiones/2026-11-22_kit-escuadras-melamina-18-mm_ender-3-v3-plus)."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "carpeta": {"type": "string", "minLength": 1, "maxLength": MAX_RUTA,
                            "description": "La carpeta de la pieza, relativa a la carpeta de trabajo."},
            },
            "required": ["carpeta"],
            "additionalProperties": False,
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "cargado": {"type": "boolean", "description": "Si el producto quedó cargado (o actualizado) como borrador."},
                "mensaje": {"type": "string", "description": "Qué pasó, para mostrarle al usuario."},
                "accion": {"type": "string", "enum": ["creado", "actualizado", "ya_publicado"]},
                "id": {"type": "integer", "description": "El número del producto en la tienda."},
                "estado": {"type": "string", "description": "Cómo quedó en la tienda: borrador, publicado, ..."},
                "fotos": {"type": "integer", "description": "Fotos que tiene el producto."},
                "enlace_admin": {"type": "string", "description": "El producto en el administrador de la tienda."},
                "enlace_vista_previa": {"type": "string", "description": "La vista previa del borrador en la tienda."},
                "avisos": {"type": "array", "items": {"type": "string"}},
                "repetido": {"type": "boolean", "description": "El mismo pedido llegó hace un momento: no se repitió."},
            },
            "required": ["cargado", "mensaje"],
        },
        # Crea o cambia un borrador en otro sistema (la tienda): no es de solo lectura, pero no borra ni publica.
        "annotations": {"title": "Cargar en la tienda (borrador)", "readOnlyHint": False, "destructiveHint": False,
                        "idempotentHint": True, "openWorldHint": True},
    },
    {
        "name": "estado_tienda",
        "title": "Ver si la tienda está conectada",
        "description": ("Dice si la tienda WooCommerce del usuario está conectada y responde (dirección y usuario). "
                        "No cambia nada."),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "outputSchema": {
            "type": "object",
            "properties": {
                "conectada": {"type": "boolean"},
                "mensaje": {"type": "string"},
                "tienda": {"type": "string"},
                "usuario": {"type": "string"},
            },
            "required": ["conectada", "mensaje"],
        },
        "annotations": {"title": "Estado de la tienda", "readOnlyHint": True, "destructiveHint": False,
                        "idempotentHint": True, "openWorldHint": True},
    },
]


class Rechazo(Exception):
    """Un motivo para no seguir, que se le cuenta a quien pidió."""


def registrar(texto: str) -> None:
    """Registro en stderr (la app de Claude lo guarda en el log del servidor). stdout es solo para MCP.
    Nunca lleva la contraseña ni el encabezado de autorización."""
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {NOMBRE}: {texto}", file=sys.stderr, flush=True)


# --- Rutas ------------------------------------------------------------------------------------------------------

def dentro_de(ruta: str, raiz: str, o_igual: bool = False) -> bool:
    r, b = os.path.normcase(ruta), os.path.normcase(raiz)
    try:
        return (o_igual or r != b) and os.path.commonpath([r, b]) == b
    except ValueError:                                     # otra unidad de disco en Windows
        return False


def _con_control(texto: str) -> bool:
    return any(ord(c) < 32 or ord(c) == 127 for c in texto)


def carpeta_de_trabajo(entorno) -> str:
    raiz = (entorno.get("TALLER3D_CARPETA") or "").strip()
    if not raiz or not os.path.isabs(raiz):
        raise Rechazo("Falta la carpeta de trabajo del taller en la configuración de la app (TALLER3D_CARPETA): "
                      "corré de nuevo el instalador.")
    real = os.path.realpath(raiz)
    if not os.path.isdir(real):
        raise Rechazo(f"No existe la carpeta de trabajo {raiz}.")
    return real


def validar_carpeta(pedida, raiz: str) -> str:
    """La ruta real de la carpeta de la pieza (dentro de la de trabajo); si no, Rechazo con el motivo."""
    if not isinstance(pedida, str) or not pedida.strip():
        raise Rechazo("Falta `carpeta`: la carpeta de la pieza, relativa a la carpeta de trabajo.")
    if len(pedida) > MAX_RUTA or _con_control(pedida) or "://" in pedida:
        raise Rechazo("`carpeta` tiene que ser la ruta de la carpeta de la pieza (sin enlaces ni caracteres raros).")
    pedida = pedida.strip().replace("\\", "/") if os.sep == "/" else pedida.strip()
    ruta = pedida if os.path.isabs(pedida) else os.path.join(raiz, pedida)
    real = os.path.realpath(ruta)
    if not dentro_de(real, raiz):
        raise Rechazo("Solo cargo piezas de la carpeta de trabajo del taller.")
    if not os.path.isdir(real):
        raise Rechazo(f"No existe la carpeta {pedida} en la carpeta de trabajo.")
    return real


def _leer_json(ruta: str, maximo: int, que: str):
    try:
        if os.path.getsize(ruta) > maximo:
            raise Rechazo(f"{que} es demasiado grande.")
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError, UnicodeDecodeError) as error:
        raise Rechazo(f"No pude leer {que}: {error}") from None


def leer_publicacion(carpeta: str) -> dict:
    ruta = os.path.realpath(os.path.join(carpeta, "producto", "publicacion.json"))
    if not dentro_de(ruta, carpeta) or not os.path.isfile(ruta):
        raise Rechazo("Esta pieza no tiene la publicación armada (producto/publicacion.json): pedile a Claude que la "
                      "arme con /publicar y que te muestre la vista previa.")
    datos = _leer_json(ruta, MAX_PUBLICACION, "publicacion.json")
    if not isinstance(datos, dict) or not isinstance(datos.get("producto"), dict):
        raise Rechazo("publicacion.json no tiene el producto: pedile a Claude que arme de nuevo la publicación.")
    return datos


# --- El producto ------------------------------------------------------------------------------------------------

def _texto(valor, largo: int, que: str, obligatorio: bool = True) -> str:
    if valor is None and not obligatorio:
        return ""
    if not isinstance(valor, str) or (obligatorio and not valor.strip()):
        raise Rechazo(f"Falta {que} en la publicación.")
    if len(valor) > largo:
        raise Rechazo(f"{que[0].upper()}{que[1:]} es demasiado largo.")
    return valor.strip()


def _numero(valor, que: str) -> str:
    if isinstance(valor, bool) or valor is None or valor == "":
        raise Rechazo(f"Falta {que} en la publicación.")
    t = str(valor).strip().replace(",", ".")
    if not re.fullmatch(r"\d{1,9}(\.\d{1,4})?", t):
        raise Rechazo(f"{que[0].upper()}{que[1:]} no es un número: {valor!r}.")
    return t


def _nombres(lista, maximo: int) -> list[str]:
    salida = []
    for x in lista if isinstance(lista, list) else []:
        n = x.get("name") if isinstance(x, dict) else x
        if isinstance(n, str) and n.strip() and len(n) <= 100 and not _con_control(n):
            n = n.strip()
            if n.casefold() not in {s.casefold() for s in salida}:
                salida.append(n)
    return salida[:maximo]


def armar_producto(pub: dict) -> tuple[dict, list[str], list[str]]:
    """(datos del producto para WooCommerce, nombres de categorías, nombres de etiquetas). Siempre borrador."""
    p = pub["producto"]
    if p.get("type") not in (None, "", "simple"):
        raise Rechazo("Solo cargo productos simples.")
    datos = {
        "name": _texto(p.get("name"), 200, "el nombre"),
        "type": "simple",
        "status": "draft",
        "sku": _texto(p.get("sku"), 100, "el SKU"),
        "regular_price": _numero(p.get("regular_price"), "el precio"),
        "description": _texto(p.get("description"), 100_000, "la descripción", obligatorio=False),
        "short_description": _texto(p.get("short_description"), 5_000, "la descripción corta", obligatorio=False),
        "manage_stock": bool(p.get("manage_stock") or False),
    }
    if p.get("weight") not in (None, ""):
        datos["weight"] = _numero(p.get("weight"), "el peso")
    medidas = p.get("dimensions") if isinstance(p.get("dimensions"), dict) else {}
    if medidas:
        datos["dimensions"] = {k: _numero(medidas.get(k), f"la medida «{k}»") for k in ("length", "width", "height")
                               if medidas.get(k) not in (None, "")}
    return datos, _nombres(p.get("categories"), 5), _nombres(p.get("tags"), MAX_ETIQUETAS)


def rutas_fotos(pub: dict, carpeta: str) -> tuple[list[str], list[str]]:
    """Las fotos de la publicación (relativas a producto/), en su orden: solo imágenes de la carpeta de la pieza."""
    base = os.path.join(carpeta, "producto")
    fotos, avisos = [], []
    for nombre in pub.get("fotos") if isinstance(pub.get("fotos"), list) else []:
        if not isinstance(nombre, str) or not nombre.strip() or _con_control(nombre) or "://" in nombre:
            continue
        real = os.path.realpath(os.path.join(base, nombre))
        extension = os.path.splitext(real)[1].lower()
        if not dentro_de(real, carpeta) or extension not in TIPOS_FOTO:
            avisos.append(f"Salteé la foto {nombre}: no es una imagen de la carpeta de la pieza.")
        elif not os.path.isfile(real):
            avisos.append(f"No encontré la foto {nombre}: la salteé.")
        elif os.path.getsize(real) > MAX_FOTO:
            avisos.append(f"La foto {nombre} pesa más de {MAX_FOTO // (1024 * 1024)} MB: la salteé.")
        elif real not in fotos:
            fotos.append(real)
    if len(fotos) > MAX_FOTOS:
        avisos.append(f"Subí las primeras {MAX_FOTOS} fotos.")
    return fotos[:MAX_FOTOS], avisos


def _slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:60] or "producto"


# --- La tienda --------------------------------------------------------------------------------------------------

def validar_url(url) -> str:
    if not isinstance(url, str) or not url.strip() or _con_control(url):
        raise Rechazo("Falta la dirección de la tienda.")
    u = urllib.parse.urlsplit(url.strip())
    local = u.hostname in ("localhost", "127.0.0.1")
    if not u.hostname or not (u.scheme == "https" or (u.scheme == "http" and local)):
        raise Rechazo("La dirección de la tienda tiene que empezar con https:// (por ejemplo https://mitienda.com.ar).")
    if u.username or u.password or u.query or u.fragment:
        raise Rechazo("Guardá solo la dirección de la tienda, sin usuario ni nada después de ? o #.")
    return f"{u.scheme}://{u.netloc}{u.path.rstrip('/')}"


def ruta_credenciales(entorno) -> str:
    propia = (entorno.get("TALLER3D_CREDENCIALES") or "").strip()
    if propia:
        return os.path.expanduser(propia)
    if os.name == "nt" and entorno.get("APPDATA"):
        return os.path.join(entorno["APPDATA"], "taller-3d", ARCHIVO_CREDENCIALES)
    base = entorno.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "taller-3d", ARCHIVO_CREDENCIALES)


def leer_credenciales(entorno) -> tuple[str, str, str]:
    ruta = ruta_credenciales(entorno)
    if not os.path.isfile(ruta):
        raise Rechazo(SIN_CONECTAR)
    if os.name == "posix" and os.stat(ruta).st_mode & 0o077:
        raise Rechazo(f"El archivo con la conexión de tu tienda ({ruta}) lo pueden leer otros usuarios de la PC: "
                      f"corré chmod 600 \"{ruta}\" y probá de nuevo.")
    datos = _leer_json(ruta, MAX_CREDENCIALES, "el archivo de la tienda")
    if not isinstance(datos, dict):
        raise Rechazo(SIN_CONECTAR)
    usuario, clave = datos.get("usuario"), datos.get("contrasena")
    if not isinstance(usuario, str) or not usuario.strip() or not isinstance(clave, str) or not clave.strip():
        raise Rechazo(SIN_CONECTAR)
    return validar_url(datos.get("tienda")), usuario.strip(), clave.strip()


def guardar_credenciales(ruta: str, tienda: str, usuario: str, clave: str) -> None:
    carpeta = os.path.dirname(ruta)
    os.makedirs(carpeta, mode=0o700, exist_ok=True)
    temporal = ruta + ".tmp"
    if os.path.lexists(temporal):
        os.remove(temporal)
    fd = os.open(temporal, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"tienda": tienda, "usuario": usuario, "contrasena": clave}, f, ensure_ascii=False, indent=2)
    os.replace(temporal, ruta)
    if os.name == "posix":
        os.chmod(ruta, 0o600)


class SinRedirecciones(urllib.request.HTTPRedirectHandler):
    """Una redirección podría llevar la contraseña a otro sitio: no se sigue."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Rechazo(f"La tienda contestó con una redirección a {newurl}. Guardá esa dirección (por ejemplo, con o "
                      "sin www) con: python3 tienda_mcp.py configurar")


def _json(datos: bytes):
    if len(datos) > MAX_RESPUESTA:
        raise Rechazo("La tienda contestó algo demasiado grande.")
    try:
        return json.loads(datos.decode("utf-8")) if datos.strip() else None
    except (UnicodeDecodeError, ValueError):
        return None


def _explicar(codigo: int, cuerpo, ruta: str) -> str:
    c = cuerpo.get("code", "") if isinstance(cuerpo, dict) else ""
    m = cuerpo.get("message", "") if isinstance(cuerpo, dict) else ""
    m = re.sub(r"<[^>]+>", "", html.unescape(m if isinstance(m, str) else ""))[:300].strip()
    if codigo == 401:
        if c in ("incorrect_password", "invalid_username", "invalid_email", "application_passwords_disabled"):
            return ("La tienda no aceptó el usuario o la contraseña de aplicación. Creá otra en tu WordPress "
                    "(Usuarios → Perfil → Contraseñas de aplicación) y guardala con: python3 tienda_mcp.py configurar")
        return ("La tienda no reconoció la conexión: o la contraseña de aplicación ya no existe, o el servidor no le "
                "pasa a WordPress el encabezado de autorización. Probá creando otra contraseña de aplicación y "
                "guardándola con: python3 tienda_mcp.py configurar")
    if codigo == 403:
        que = "subir imágenes" if ruta.startswith("/wp/v2/media") else "cargar productos"
        return (f"Tu usuario de WordPress no tiene permiso para {que}: tiene que ser Administrador o Gestor de la "
                "tienda." + (f" ({m})" if m else ""))
    if codigo == 404 and c == "rest_no_route":
        return ("La tienda no tiene la conexión de WooCommerce (/wp-json/wc/v3): revisá que WooCommerce esté activo y "
                "que los enlaces permanentes no estén en «Simple».")
    if codigo == 400:
        return "La tienda no aceptó los datos del producto" + (f": {m}" if m else ".")
    if codigo >= 500:
        return f"La tienda tuvo un error ({codigo})" + (f": {m}" if m else "") + ". Probá de nuevo en un rato."
    return f"La tienda contestó {codigo}" + (f": {m}" if m else ".")


class Tienda:
    """La API de WordPress y WooCommerce de la tienda, con la contraseña de aplicación del usuario."""

    def __init__(self, base: str, usuario: str, clave: str, tiempo: float = 45.0, abridor=None):
        self.base = validar_url(base)
        self._autorizacion = "Basic " + base64.b64encode(f"{usuario}:{clave}".encode("utf-8")).decode("ascii")
        self.tiempo = tiempo
        self.abridor = abridor or urllib.request.build_opener(SinRedirecciones())

    def pedir(self, metodo: str, ruta: str, datos=None, params=None, cuerpo: bytes | None = None,
              tipo: str | None = None, archivo: str | None = None, admitir=()):
        url = f"{self.base}/wp-json{ruta}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
        encabezados = {"Authorization": self._autorizacion, "Accept": "application/json",
                       "User-Agent": f"{NOMBRE}/{VERSION}"}
        if datos is not None:
            cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
            encabezados["Content-Type"] = "application/json; charset=utf-8"
        elif cuerpo is not None:
            encabezados["Content-Type"] = tipo or "application/octet-stream"
            encabezados["Content-Disposition"] = f'attachment; filename="{archivo or "foto"}"'
        pedido = urllib.request.Request(url, data=cuerpo, headers=encabezados, method=metodo)
        try:
            with self.abridor.open(pedido, timeout=self.tiempo) as r:
                return r.status, _json(r.read(MAX_RESPUESTA + 1))
        except urllib.error.HTTPError as error:
            respuesta = _json(error.read(MAX_RESPUESTA + 1) or b"")
            if error.code in admitir:
                return error.code, respuesta
            raise Rechazo(_explicar(error.code, respuesta, ruta)) from None
        except urllib.error.URLError as error:
            raise Rechazo(f"No pude conectarme con la tienda ({self.base}): {error.reason}. Revisá que la PC tenga "
                          "internet y que la dirección esté bien.") from None
        except TimeoutError:
            raise Rechazo("La tienda tardó demasiado en contestar: probá de nuevo en un rato.") from None

    # Enlaces
    def enlace_admin(self, pid: int) -> str:
        return f"{self.base}/wp-admin/post.php?post={pid}&action=edit"

    def enlace_vista_previa(self, pid: int) -> str:
        return f"{self.base}/?post_type=product&p={pid}&preview=true"


def _lista(valor) -> list[dict]:
    return [x for x in valor if isinstance(x, dict)] if isinstance(valor, list) else []


def buscar_existente(tienda: Tienda, sku: str, id_previo) -> dict | None:
    """El producto de esta pieza en la tienda: el que se cargó antes (tienda.json) o el que tiene su SKU."""
    if isinstance(id_previo, int) and id_previo > 0:
        codigo, p = tienda.pedir("GET", f"/wc/v3/products/{id_previo}", admitir=(404, 410))
        if codigo == 200 and isinstance(p, dict) and p.get("status") != "trash":
            return p
    _, lista = tienda.pedir("GET", "/wc/v3/products", params={"sku": sku, "status": "any", "per_page": 10})
    return next((p for p in _lista(lista) if p.get("sku") == sku and p.get("status") != "trash"), None)


def _mismo_nombre(a, b: str) -> bool:
    return isinstance(a, str) and html.unescape(a).strip().casefold() == b.strip().casefold()


def ids_categorias(tienda: Tienda, nombres: list[str], avisos: list[str]) -> list[dict]:
    """Solo categorías que ya existen en la tienda: las que no, se avisan (no se crean)."""
    ids = []
    for n in nombres:
        _, lista = tienda.pedir("GET", "/wc/v3/products/categories", params={"search": n, "per_page": 100})
        hallada = next((c for c in _lista(lista) if _mismo_nombre(c.get("name"), n)), None)
        if hallada and isinstance(hallada.get("id"), int):
            ids.append({"id": hallada["id"]})
        else:
            avisos.append(f"En tu tienda no hay una categoría «{n}»: el producto quedó sin ella (creala en "
                          "Productos → Categorías y elegila en el borrador).")
    return ids


def ids_etiquetas(tienda: Tienda, nombres: list[str], avisos: list[str]) -> list[dict]:
    ids = []
    for n in nombres:
        _, lista = tienda.pedir("GET", "/wc/v3/products/tags", params={"search": n, "per_page": 100})
        hallada = next((t for t in _lista(lista) if _mismo_nombre(t.get("name"), n)), None)
        if hallada and isinstance(hallada.get("id"), int):
            ids.append({"id": hallada["id"]})
            continue
        codigo, nueva = tienda.pedir("POST", "/wc/v3/products/tags", {"name": n}, admitir=(400,))
        datos = nueva.get("data") if isinstance(nueva, dict) and isinstance(nueva.get("data"), dict) else {}
        if codigo in (200, 201) and isinstance(nueva, dict) and isinstance(nueva.get("id"), int):
            ids.append({"id": nueva["id"]})
        elif isinstance(datos.get("resource_id"), int):            # term_exists: ya estaba
            ids.append({"id": datos["resource_id"]})
        else:
            avisos.append(f"No pude agregar la etiqueta «{n}».")
    return ids


def subir_fotos(tienda: Tienda, fotos: list[str], previas: dict, nombre: str, sku: str) -> tuple[list[int], dict]:
    """Sube las fotos a la biblioteca de medios (las que ya se subieron antes, iguales, no se suben de nuevo)."""
    ids, mapa = [], {}
    for i, ruta in enumerate(fotos, 1):
        with open(ruta, "rb") as f:
            datos = f.read(MAX_FOTO + 1)
        huella = hashlib.sha256(datos).hexdigest()
        mid = previas.get(huella) if isinstance(previas, dict) else None
        if isinstance(mid, int) and mid > 0:
            codigo, _ = tienda.pedir("GET", f"/wp/v2/media/{mid}", params={"context": "edit"}, admitir=(404, 410))
            mid = mid if codigo == 200 else None
        else:
            mid = None
        if mid is None:
            extension = os.path.splitext(ruta)[1].lower()
            _, media = tienda.pedir("POST", "/wp/v2/media", cuerpo=datos, tipo=TIPOS_FOTO[extension],
                                    archivo=f"{_slug(sku)}-{i}{extension}")
            if not isinstance(media, dict) or not isinstance(media.get("id"), int):
                raise Rechazo("La tienda no devolvió el número de la foto que subí.")
            mid = media["id"]
            try:                                           # el texto alternativo es un extra: si falla, se sigue
                tienda.pedir("POST", f"/wp/v2/media/{mid}", {"alt_text": nombre, "title": nombre})
            except Rechazo:
                pass
        ids.append(mid)
        mapa[huella] = mid
    return ids, mapa


def leer_estado(ruta: str, base: str) -> dict:
    if not os.path.isfile(ruta) or os.path.islink(ruta):
        return {}
    try:
        datos = _leer_json(ruta, MAX_CREDENCIALES, "tienda.json")
    except Rechazo:
        return {}
    return datos if isinstance(datos, dict) and datos.get("tienda") == base else {}


def guardar_estado(ruta: str, datos: dict) -> bool:
    if os.path.islink(ruta) or not os.path.isdir(os.path.dirname(ruta)):
        return False
    temporal = ruta + ".tmp"
    try:
        with open(temporal, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(temporal, ruta)
        return True
    except OSError:
        return False


# --- Las herramientas -------------------------------------------------------------------------------------------

class Servidor:
    def __init__(self, entorno=None, abridor=None):
        self.entorno = dict(os.environ if entorno is None else entorno)
        self.abridor = abridor
        self.legada: str | None = None
        self.recientes: dict[str, tuple[float, dict]] = {}

    def tienda(self) -> Tienda:
        base, usuario, clave = leer_credenciales(self.entorno)
        return Tienda(base, usuario, clave, abridor=self.abridor)

    def cargar(self, argumentos: dict) -> tuple[dict, bool]:
        """(structuredContent, isError)."""
        pedida = argumentos.get("carpeta")
        try:
            extra = sorted(set(argumentos) - {"carpeta"})
            if extra:
                raise Rechazo(f"Solo acepto `carpeta` (sobra: {', '.join(map(str, extra))}).")
            raiz = carpeta_de_trabajo(self.entorno)
            carpeta = validar_carpeta(pedida, raiz)
            relativa = os.path.relpath(carpeta, raiz).replace(os.sep, "/")
            ahora = time.monotonic()
            previo = self.recientes.get(carpeta)
            if previo and ahora - previo[0] < REPETIDO_S:
                registrar(f"repetido: {relativa}")
                return {**previo[1], "repetido": True,
                        "mensaje": f"Ya lo hice hace {ahora - previo[0]:.0f} s. " + previo[1]["mensaje"]}, False
            pub = leer_publicacion(carpeta)
            datos, categorias, etiquetas = armar_producto(pub)
            fotos, avisos = rutas_fotos(pub, carpeta)
            tienda = self.tienda()
            archivo_estado = os.path.join(carpeta, "producto", ESTADO)
            estado = leer_estado(archivo_estado, tienda.base)
            existente = buscar_existente(tienda, datos["sku"], estado.get("id"))
            nombre = datos["name"]
            if existente and existente.get("status") != "draft":
                pid = int(existente["id"])
                como = ESTADOS.get(existente.get("status"), str(existente.get("status")))
                salida = {"cargado": False, "accion": "ya_publicado", "id": pid, "estado": como,
                          "enlace_admin": tienda.enlace_admin(pid), "avisos": avisos,
                          "mensaje": f"«{nombre}» ya está en tu tienda como {como} (producto {pid}): no lo toqué. Si "
                                     "querés cambiarle el precio o el texto, pedíselo a Claude."}
                registrar(f"ya publicado, sin tocar: {relativa} → {pid}")
                return salida, False
            datos["categories"] = ids_categorias(tienda, categorias, avisos)
            datos["tags"] = ids_etiquetas(tienda, etiquetas, avisos)
            imagenes, mapa = subir_fotos(tienda, fotos, estado.get("fotos") or {}, nombre, datos["sku"])
            datos["images"] = [{"id": i} for i in imagenes]
            if existente:
                _, producto = tienda.pedir("PUT", f"/wc/v3/products/{int(existente['id'])}", datos)
                accion = "actualizado"
            else:
                _, producto = tienda.pedir("POST", "/wc/v3/products", datos)
                accion = "creado"
            if not isinstance(producto, dict) or not isinstance(producto.get("id"), int):
                raise Rechazo("La tienda no devolvió el número del producto.")
            pid = producto["id"]
            _, visto = tienda.pedir("GET", f"/wc/v3/products/{pid}")
            visto = visto if isinstance(visto, dict) else {}
            if visto.get("status") != "draft":            # nunca debería pasar: se vuelve a borrador y se avisa
                tienda.pedir("PUT", f"/wc/v3/products/{pid}", {"status": "draft"})
                avisos.append("La tienda lo había dejado publicado: lo pasé a borrador.")
                _, visto = tienda.pedir("GET", f"/wc/v3/products/{pid}")
                visto = visto if isinstance(visto, dict) else {}
                if visto.get("status") != "draft":
                    raise Rechazo(f"El producto {pid} no quedó como borrador: revisalo en tu tienda ya mismo.")
            if visto.get("sku") != datos["sku"]:
                avisos.append(f"La tienda le dejó otro SKU («{visto.get('sku')}»): revisalo en el borrador.")
            if str(visto.get("regular_price")) != datos["regular_price"]:
                avisos.append(f"El precio quedó en {visto.get('regular_price')} en vez de {datos['regular_price']}: "
                              "revisalo en el borrador.")
            salida = {"cargado": True, "accion": accion, "id": pid, "estado": "borrador",
                      "fotos": len(_lista(visto.get("images"))) or len(imagenes),
                      "enlace_admin": tienda.enlace_admin(pid), "enlace_vista_previa": tienda.enlace_vista_previa(pid),
                      "avisos": avisos}
            fotos_txt = {0: "sin fotos", 1: "con 1 foto"}.get(salida["fotos"], f"con {salida['fotos']} fotos")
            hecho = "quedó como borrador" if accion == "creado" else "se actualizó (sigue como borrador)"
            salida["mensaje"] = (f"Listo: «{nombre}» {hecho} en tu tienda (producto {pid}), {fotos_txt}. Revisalo y "
                                 "publicalo vos desde la tienda.")
            if avisos:
                salida["mensaje"] += " Ojo: " + " ".join(avisos)
            guardar_estado(archivo_estado, {
                "tienda": tienda.base, "id": pid, "sku": datos["sku"], "estado": "borrador",
                "enlace_admin": salida["enlace_admin"], "enlace_vista_previa": salida["enlace_vista_previa"],
                "actualizado": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "fotos": mapa})
            self.recientes = {k: v for k, v in self.recientes.items() if ahora - v[0] < REPETIDO_S}
            self.recientes[carpeta] = (ahora, salida)
            registrar(f"{accion}: {relativa} → {pid} ({len(imagenes)} fotos)")
            return salida, False
        except Rechazo as motivo:
            registrar(f"rechazado: {pedida!r}: {motivo}")
            return {"cargado": False, "mensaje": str(motivo)}, True

    def estado(self, argumentos: dict) -> tuple[dict, bool]:
        try:
            if argumentos:
                raise Rechazo("estado_tienda no lleva datos.")
            tienda = self.tienda()
            _, yo = tienda.pedir("GET", "/wp/v2/users/me", params={"context": "edit"})
            tienda.pedir("GET", "/wc/v3/products", params={"per_page": 1})
            usuario = (yo or {}).get("name") or (yo or {}).get("slug") or ""
            return {"conectada": True, "tienda": tienda.base, "usuario": str(usuario),
                    "mensaje": f"La tienda {tienda.base} está conectada" + (f" (usuario {usuario})" if usuario else "")
                               + ". Los productos se cargan siempre como borrador."}, False
        except Rechazo as motivo:
            return {"conectada": False, "mensaje": str(motivo)}, False


# --- MCP por stdio (igual que taller3d-orca) ---------------------------------------------------------------------

def _error(ident, codigo: int, mensaje: str, datos=None) -> dict:
    e = {"code": codigo, "message": mensaje}
    if datos is not None:
        e["data"] = datos
    return {"jsonrpc": "2.0", "id": ident, "error": e}


def _resultado_herramienta(salida: dict, es_error: bool) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(salida, ensure_ascii=False)}],
            "structuredContent": salida, "isError": es_error}


def procesar(servidor: Servidor, m) -> dict | None:
    if not isinstance(m, dict):
        return _error(None, -32600, "Invalid Request")
    if "method" not in m and ("result" in m or "error" in m):
        return None
    ident = m.get("id")
    es_pedido = "id" in m
    if m.get("jsonrpc") != "2.0" or not isinstance(m.get("method"), str):
        return _error(ident if isinstance(ident, (str, int)) else None, -32600, "Invalid Request")
    if es_pedido and (isinstance(ident, bool) or not isinstance(ident, (str, int))):
        return _error(None, -32600, "Invalid Request: id tiene que ser texto o número entero")
    if not es_pedido:
        return None
    metodo, params = m["method"], m.get("params")
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return _error(ident, -32602, "Invalid params")
    meta = params.get("_meta") if isinstance(params.get("_meta"), dict) else {}
    version = meta.get(META_VERSION)
    if metodo == "initialize":
        pedida = params.get("protocolVersion")
        servidor.legada = pedida if pedida in VERSIONES_LEGADAS else VERSIONES_LEGADAS[0]
        return {"jsonrpc": "2.0", "id": ident, "result": {
            "protocolVersion": servidor.legada, "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": INFO, "instructions": INSTRUCCIONES}}
    if version is not None and not (servidor.legada and version in VERSIONES_LEGADAS):
        if version not in VERSIONES_MODERNAS:
            return _error(ident, -32022, "Unsupported protocol version",
                          {"supported": list(VERSIONES_MODERNAS), "requested": version})
        if not isinstance(meta.get(META_CAPACIDADES), dict):
            return _error(ident, -32602, f"Invalid params: falta _meta[{META_CAPACIDADES!r}]")
        moderno = True
    elif servidor.legada or metodo == "ping":
        moderno = False
    else:
        return _error(ident, -32602, f"Invalid params: falta _meta[{META_VERSION!r}] o el saludo initialize")
    try:
        return _atender(servidor, ident, metodo, params, moderno)
    except Exception as error:
        registrar(f"error interno en {metodo}: {type(error).__name__}: {error}")
        return _error(ident, -32603, "Internal error")


def _atender(servidor: Servidor, ident, metodo: str, params: dict, moderno: bool) -> dict:
    if metodo == "server/discover":
        resultado = {"supportedVersions": list(VERSIONES_MODERNAS), "capabilities": {"tools": {"listChanged": False}},
                     "instructions": INSTRUCCIONES}
    elif metodo == "ping":
        resultado = {}
    elif metodo == "tools/list":
        resultado = {"tools": HERRAMIENTAS}
    elif metodo in ("resources/list", "resources/templates/list", "prompts/list"):
        resultado = {{"resources/list": "resources", "resources/templates/list": "resourceTemplates",
                      "prompts/list": "prompts"}[metodo]: []}
    elif metodo == "tools/call":
        nombre, argumentos = params.get("name"), params.get("arguments")
        if argumentos is None:
            argumentos = {}
        if not isinstance(argumentos, dict):
            return _error(ident, -32602, "Invalid params: arguments tiene que ser un objeto")
        if nombre == "cargar_borrador":
            resultado = _resultado_herramienta(*servidor.cargar(argumentos))
        elif nombre == "estado_tienda":
            resultado = _resultado_herramienta(*servidor.estado(argumentos))
        else:
            return _error(ident, -32602, f"Unknown tool: {nombre}")
    else:
        return _error(ident, -32601, f"Method not found: {metodo}")
    if moderno:
        resultado = {"resultType": "complete", **resultado, "_meta": {META_SERVIDOR: INFO}}
    return {"jsonrpc": "2.0", "id": ident, "result": resultado}


def procesar_linea(servidor: Servidor, linea: bytes):
    try:
        mensaje = json.loads(linea.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return _error(None, -32700, "Parse error")
    if isinstance(mensaje, list):
        if not mensaje:
            return _error(None, -32600, "Invalid Request")
        respuestas = [r for r in (procesar(servidor, x) for x in mensaje) if r is not None]
        return respuestas or None
    return procesar(servidor, mensaje)


def servir() -> None:
    servidor = Servidor()
    entrada, salida = sys.stdin.buffer, sys.stdout.buffer
    registrar(f"{VERSION} listo")
    while True:
        linea = entrada.readline()
        if not linea:
            break
        if not linea.strip():
            continue
        try:
            respuesta = procesar_linea(servidor, linea)
        except Exception as error:
            registrar(f"error interno: {type(error).__name__}: {error}")
            respuesta = _error(None, -32603, "Internal error")
        if respuesta is not None:
            salida.write(json.dumps(respuesta, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n")
            salida.flush()


# --- Configurar desde una terminal (lo hace el usuario, una vez) -------------------------------------------------

def _preguntar(texto: str, defecto: str = "") -> str:
    r = input(f"   {texto}" + (f" [{defecto}]" if defecto else "") + ": ").strip()
    return r or defecto


def configurar(argumentos) -> int:
    ap = argparse.ArgumentParser(prog="tienda_mcp.py configurar",
                                 description="Guarda la conexión con tu tienda WooCommerce (una sola vez).")
    ap.add_argument("--tienda", help="dirección de la tienda (https://...)")
    ap.add_argument("--usuario", help="tu usuario de WordPress")
    a = ap.parse_args(argumentos)
    ruta = ruta_credenciales(os.environ)
    anterior = {}
    if os.path.isfile(ruta):
        try:
            anterior = _leer_json(ruta, MAX_CREDENCIALES, "el archivo de la tienda") or {}
        except Rechazo:
            anterior = {}
    print("Conectar el taller 3D con tu tienda WooCommerce (los productos se cargan siempre como borrador).")
    print("Antes, creá una contraseña de aplicación en tu WordPress: Usuarios → Perfil → Contraseñas de aplicación,")
    print("con el nombre «Taller 3D» → Añadir. WordPress la muestra una sola vez: copiala.")
    try:
        tienda = a.tienda or _preguntar("Dirección de tu tienda", str(anterior.get("tienda") or ""))
        if tienda and "://" not in tienda:
            tienda = "https://" + tienda
        tienda = validar_url(tienda)
        usuario = a.usuario or _preguntar("Tu usuario de WordPress", str(anterior.get("usuario") or ""))
        clave = getpass.getpass("   Contraseña de aplicación (no se ve mientras la escribís): ").strip()
    except Rechazo as motivo:
        print(f"   {motivo}")
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\n   No guardé nada.")
        return 1
    if not usuario or not clave:
        print("   Faltan el usuario o la contraseña: no guardé nada.")
        return 1
    t = Tienda(tienda, usuario, clave)
    try:
        _, yo = t.pedir("GET", "/wp/v2/users/me", params={"context": "edit"})
        t.pedir("GET", "/wc/v3/products", params={"per_page": 1})
    except Rechazo as motivo:
        print(f"   No pude conectarme: {motivo}")
        print("   No guardé nada. Revisá los datos y corré de nuevo: python3 tienda_mcp.py configurar")
        return 1
    guardar_credenciales(ruta, tienda, usuario, clave)
    nombre = (yo or {}).get("name") if isinstance(yo, dict) else None
    print(f"   Listo: la tienda {tienda} quedó conectada" + (f" (usuario {nombre})" if nombre else "") + ".")
    print(f"   La conexión quedó en {ruta}, que solo puede leer tu usuario.")
    return 0


def probar() -> int:
    salida, _ = Servidor().estado({})
    print(f"   {salida['mensaje']}")
    return 0 if salida.get("conectada") else 1


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "configurar":
        sys.exit(configurar(sys.argv[2:]))
    if len(sys.argv) > 1 and sys.argv[1] == "probar":
        sys.exit(probar())
    if len(sys.argv) > 1:
        sys.exit("Uso: tienda_mcp.py [configurar | probar] (sin nada, atiende a la app de Claude por MCP).")
    servir()


if __name__ == "__main__":
    main()
