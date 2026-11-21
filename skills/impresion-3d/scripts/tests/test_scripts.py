# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Leo y colaboradores de taller-3d
"""Pruebas de los scripts de taller-3d.

Correr desde la carpeta scripts:  python3 -m unittest discover -s tests -v
Requiere manifold3d y numpy para las pruebas de CAD y STL.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
RAIZ = SCRIPTS.parent.parent.parent
sys.path.insert(0, str(SCRIPTS))

import comun  # noqa: E402
import perfil_orca  # noqa: E402
import revisar_gcode  # noqa: E402

# Impresora inventada para las pruebas: el plugin no trae impresoras.
IMPRESORA_PRUEBA = Path(__file__).resolve().parent / "datos" / "impresora-prueba.json"
IMP = comun.cargar_impresora(IMPRESORA_PRUEBA)

CABECERA = """; HEADER_BLOCK_START
; total layer number: 2
; HEADER_BLOCK_END
"""
CONFIG = """; filament_type = {mat}
; printer_model = Marca Prueba 300
; printer_settings_id = Mi Prueba 300 0.4 nozzle
; printable_area = 0x0,300x0,300x300,0x300
; total filament used [g] = 1.50
; estimated printing time (normal mode) = 5m 10s
"""


def gcode(cuerpo: str, mat: str = "PETG", fin: str = "END_PRINT\n") -> Path:
    tmp = Path(tempfile.mkdtemp()) / "prueba.gcode"
    tmp.write_text(CABECERA + "M140 S0\nM104 S0\nSTART_PRINT EXTRUDER_TEMP=240 BED_TEMP=75\nG90\nM83\n"
                   + cuerpo + fin + CONFIG.format(mat=mat), encoding="utf-8")
    return tmp


BUENO = "G1 Z0.2 F600\nG1 X100 Y100 F6000\nG1 X120 Y100 E1.2\nG1 X120 Y120 E1.2\n"


class TestGcode(unittest.TestCase):
    def revisar(self, ruta, material=None):
        return revisar_gcode.revisar(ruta, revisar_gcode.detectar_impresora(ruta, candidatas=[IMP]), material)

    def mensajes(self, r):
        return " | ".join(h["mensaje"] for h in r["hallazgos"])

    def test_bueno(self):
        r = self.revisar(gcode(BUENO))
        self.assertEqual(r["estado"], comun.APROBADO, self.mensajes(r))
        self.assertEqual(r["impresora"], "prueba")
        self.assertEqual(r["estimaciones"]["gramos"], 1.5)

    def test_temperatura_excesiva(self):
        r = self.revisar(gcode("M104 S320\n" + BUENO))
        self.assertEqual(r["estado"], comun.RECHAZO)
        self.assertIn("máximo de la impresora", self.mensajes(r))

    def test_tope_material(self):
        r = self.revisar(gcode("M104 S260\n" + BUENO, mat="PLA"))
        self.assertEqual(r["estado"], comun.RECHAZO)
        self.assertIn("tope para PLA", self.mensajes(r))

    def test_fuera_de_rango_recomendado(self):
        r = self.revisar(gcode("M104 S265\n" + BUENO))
        self.assertEqual(r["estado"], comun.ADVERTENCIA)

    def test_fuera_de_cama(self):
        r = self.revisar(gcode(BUENO + "G1 X400 Y100 E1\n"))
        self.assertEqual(r["estado"], comun.RECHAZO)
        self.assertIn("fuera del área", self.mensajes(r))

    def test_z_negativa(self):
        r = self.revisar(gcode(BUENO + "G1 Z-1\n"))
        self.assertEqual(r["estado"], comun.RECHAZO)

    def test_comandos_peligrosos(self):
        for cmd in ("M500", "SAVE_CONFIG", "M302 S0", "M211 S0", "RUN_SHELL_COMMAND CMD=x"):
            r = self.revisar(gcode(BUENO + cmd + "\n"))
            self.assertEqual(r["estado"], comun.RECHAZO, cmd)

    def test_variable_sin_reemplazar(self):
        r = self.revisar(gcode("M104 S[nozzle_temperature]\n" + BUENO))
        self.assertEqual(r["estado"], comun.RECHAZO)

    def test_no_apaga(self):
        r = self.revisar(gcode(BUENO, fin=""))
        self.assertEqual(r["estado"], comun.ADVERTENCIA)
        self.assertIn("apague", self.mensajes(r))

    def test_cama_esperada(self):
        ruta = gcode(BUENO)
        r = revisar_gcode.revisar(ruta, revisar_gcode.detectar_impresora(ruta, candidatas=[IMP]), None, None, 80)
        self.assertEqual(r["estado"], comun.ADVERTENCIA)
        r = revisar_gcode.revisar(ruta, revisar_gcode.detectar_impresora(ruta, candidatas=[IMP]), None, None, 75)
        self.assertEqual(r["estado"], comun.APROBADO)

    def test_relativo(self):
        r = self.revisar(gcode(BUENO + "G91\nG1 Z2\nG90\n"))
        self.assertEqual(r["estado"], comun.APROBADO, self.mensajes(r))

    def test_formas_que_acepta_el_firmware(self):
        # Número de línea con suma de control, comandos pegados y letras repetidas: el firmware los ejecuta
        for linea in ("N10 M104 S400*45", "M104S400", "m109s400", "M104 S200 S400", "M109 R400", "M140 S 150"):
            r = self.revisar(gcode(linea + "\n" + BUENO))
            self.assertEqual(r["estado"], comun.RECHAZO, linea)
        r = self.revisar(gcode("M302P1\n" + BUENO))
        self.assertIn("M302", self.mensajes(r))

    def test_comandos_nuevos(self):
        for linea, estado in (("G92 Z0", comun.RECHAZO), ("M149 K", comun.RECHAZO), ("M301 P10 I1 D50", comun.RECHAZO),
                              ("M221 S900", comun.RECHAZO), ("M221 S150", comun.ADVERTENCIA), ("M81", comun.ADVERTENCIA)):
            r = self.revisar(gcode(BUENO + linea + "\n"))
            self.assertEqual(r["estado"], estado, f"{linea}: {self.mensajes(r)}")
        r = self.revisar(gcode("G92 E0\nM221 S100\n" + BUENO))
        self.assertEqual(r["estado"], comun.APROBADO, self.mensajes(r))

    def test_fragmento_de_perfil(self):
        G = revisar_gcode.IMPRESORA_GENERICA
        def estado(texto):
            return revisar_gcode.revisar(None, G, None, texto=texto, fragmento=True)["estado"]
        self.assertEqual(estado("G28\nM104 S[nozzle_temperature_initial_layer]\n{if x}M106 S255{endif}\nT[next_extruder]"),
                         comun.APROBADO)
        self.assertEqual(estado("{if bed_temperature[0] > 60}M104 S400{endif}"), comun.RECHAZO)
        self.assertEqual(estado("{if x}\nSAVE_CONFIG\n{endif}"), comun.RECHAZO)
        self.assertEqual(estado("M104 S{nozzle_temperature[0]+50}"), comun.ADVERTENCIA)
        self.assertEqual(estado("M104 S{nozzle_temperature_initial_layer[0]-50}"), comun.APROBADO)
        self.assertEqual(estado("G1 Z-0.3"), comun.ADVERTENCIA)
        self.assertEqual(estado("G1 Z-5"), comun.RECHAZO)

    def test_impresora_desconocida(self):
        ruta = gcode(BUENO.replace("X120", "X400"))
        ruta.write_text(ruta.read_text().replace("Mi Prueba 300 0.4 nozzle", "Otra impresora")
                        .replace("Marca Prueba 300", "Otra marca"))
        r = self.revisar(ruta)
        self.assertEqual(r["impresora"], "generica")
        self.assertEqual(r["estado"], comun.APROBADO, self.mensajes(r))


class TestPerfil(unittest.TestCase):
    def setUp(self):
        self.imp = comun.cargar_impresora(IMPRESORA_PRUEBA)
        self.cat = comun.cargar_catalogo()

    def crear(self, tipo, hereda, cambios):
        return perfil_orca.construir(tipo, "AUTO prueba", hereda, None, cambios, [], self.cat)

    def estado(self, perfil, tipo, material=None):
        usuarios = perfil_orca.perfiles_de_usuario({"impresoras": [{"procesos": {
            "calidad": "PETG Calidad 0.16 @Prueba 300"}}]})
        h = perfil_orca.validar(perfil, tipo, self.imp, material, self.cat, usuarios)
        return comun.peor(*(x["gravedad"] for x in h)) if h else comun.APROBADO, h

    def test_proceso_valido(self):
        p = self.crear("proceso", "0.20mm Standard @Marca Prueba 300",
                       {"wall_loops": "4", "sparse_infill_density": "30", "curr_bed_type": "Textured PEI Plate"})
        self.assertEqual(p["sparse_infill_density"], "30%")
        self.assertEqual(self.estado(p, "proceso")[0], comun.APROBADO)

    def test_clave_inexistente(self):
        p = self.crear("proceso", "0.20mm Standard @Marca Prueba 300", {"wal_loops": "4"})
        self.assertEqual(self.estado(p, "proceso")[0], comun.RECHAZO)

    def test_hereda_de_usuario(self):
        p = self.crear("proceso", "PETG Calidad 0.16 @Prueba 300", {})
        self.assertEqual(self.estado(p, "proceso")[0], comun.RECHAZO)

    def test_filamento_lista_y_temperatura(self):
        p = self.crear("filamento", "Generic PETG @Prueba 300-all", {"nozzle_temperature": "310"})
        self.assertEqual(p["nozzle_temperature"], ["310"])
        self.assertEqual(self.estado(p, "filamento", "PETG")[0], comun.RECHAZO)

    def test_hereda_de_auto(self):
        p = self.crear("proceso", "AUTO proceso @Prueba 300", {})
        self.assertEqual(self.estado(p, "proceso")[0], comun.RECHAZO)

    def test_cama_a_cool_plate(self):
        imp = self.imp
        otras, primera = perfil_orca.temperaturas_para_cama(
            {"textured_plate_temp": ["75"], "textured_plate_temp_initial_layer": ["80"]}, "Textured PEI Plate", imp, "PETG")
        self.assertEqual((otras, primera), ("75", "80"))
        otras, primera = perfil_orca.temperaturas_para_cama({}, "Textured PEI Plate", imp, "PLA")
        self.assertEqual((otras, primera), ("65", "65"))

    def test_enum_invalido(self):
        p = self.crear("proceso", "0.20mm Standard @Marca Prueba 300", {"sparse_infill_pattern": "giroide"})
        self.assertEqual(self.estado(p, "proceso")[0], comun.RECHAZO)

    def test_scripts_y_plugins_rechazados(self):
        for clave, valor in (("post_process", "/tmp/x.sh"), ("slicing_pipeline_plugin", "Support Fins"),
                             ("plugins", "Support Fins;abc;SlicingPipeline")):
            p = self.crear("proceso", "0.20mm Standard @Marca Prueba 300", {clave: valor})
            self.assertEqual(self.estado(p, "proceso")[0], comun.RECHAZO, clave)
        p = self.crear("proceso", "0.20mm Standard @Marca Prueba 300", {"post_process": ""})
        self.assertEqual(self.estado(p, "proceso")[0], comun.APROBADO)

    def test_temperaturas_con_espacios_y_otras_claves(self):
        imp = comun.cargar_impresora(IMPRESORA_PRUEBA)
        base = {"name": "AUTO filamento @Prueba 300", "inherits": "Generic PETG @Prueba 300-all",
                "from": "User", "filament_type": ["PETG"]}
        def rechazos(**cambios):
            h = perfil_orca.validar({**base, **cambios}, "filamento", imp)
            return [x["mensaje"] for x in h if x["gravedad"] == comun.RECHAZO]
        self.assertTrue(rechazos(nozzle_temperature=["400 "]))
        self.assertTrue(rechazos(idle_temperature=["350"]))
        self.assertEqual(rechazos(nozzle_temperature=["240 "], filament_retraction_length=["nil"]), [])

    def test_gcode_dentro_del_perfil(self):
        imp = comun.cargar_impresora(IMPRESORA_PRUEBA)
        p = {"name": "AUTO filamento @Prueba 300", "inherits": "Generic PETG @Prueba 300-all",
             "from": "User", "filament_start_gcode": ["; inicio\nM104 S400\nM500"]}
        mensajes = " | ".join(h["mensaje"] for h in perfil_orca.validar(p, "filamento", imp)
                              if h["gravedad"] == comun.RECHAZO)
        self.assertIn("filament_start_gcode", mensajes)
        self.assertIn("M500", mensajes)
        p["filament_start_gcode"] = ["; inicio\nM106 S255"]
        self.assertFalse([h for h in perfil_orca.validar(p, "filamento", imp) if h["gravedad"] == comun.RECHAZO])

    def test_crear_quita_scripts_de_la_base(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d) / "base.json"
            base.write_text(json.dumps({"name": "Mi proceso", "inherits": "0.20mm Standard @Marca Prueba 300",
                                        "from": "User", "wall_loops": "3", "post_process": "/home/x/thumb.py",
                                        "slicing_pipeline_plugin": "Support Fins"}), encoding="utf-8")
            r = subprocess.run([sys.executable, str(SCRIPTS / "perfil_orca.py"), "crear", "--tipo", "proceso",
                                "--nombre", "AUTO proceso @Prueba 300",
                                "--hereda", "0.20mm Standard @Marca Prueba 300", "--base", str(base),
                                "--salida", d], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("Quité por seguridad", r.stdout)
            hecho = json.loads((Path(d) / "AUTO proceso @Prueba 300.json").read_text(encoding="utf-8"))
            self.assertNotIn("post_process", hecho)
            self.assertNotIn("slicing_pipeline_plugin", hecho)
            self.assertEqual(hecho["wall_loops"], "3")


class TestNovedades(unittest.TestCase):
    def test_gcode_con_cambios(self):
        import novedades_orca
        base = comun.cargar_json(novedades_orca.BASE_GCODE)["claves"]
        bloque = "".join(f"; {c} = 1\n" for c in base if c != "wall_loops") + "; clave_de_orca_nueva = 3\n"
        with tempfile.TemporaryDirectory() as d:
            g = Path(d) / "x.gcode"
            g.write_text("; HEADER_BLOCK_START\n; generated by OrcaSlicer 2.6.0 on hoy\nG1 X1\n"
                         f"; CONFIG_BLOCK_START\n{bloque}; CONFIG_BLOCK_END\n", encoding="utf-8")
            estado = {}
            r = novedades_orca.revisar_gcode(g, estado)
            self.assertTrue(r["otra_version"])
            self.assertEqual(r["claves_nuevas"], ["clave_de_orca_nueva"])
            self.assertEqual(r["claves_quitadas"], ["wall_loops"])
            r2 = novedades_orca.revisar_gcode(g, estado)
            self.assertEqual(r2["nuevas_desde_la_ultima_vez"], [])

    def test_perfiles(self):
        import novedades_orca
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.json").write_text(json.dumps({"name": "Mi PETG", "inherits": "x", "from": "User",
                                                        "clave_vieja": "1", "wall_loops": "3"}), encoding="utf-8")
            (Path(d) / "b.json").write_text(json.dumps({"name": "AUTO proceso @Prueba 300", "inherits": "x",
                                                        "from": "User"}), encoding="utf-8")
            config = {"impresoras": [{"perfil_maquina": "Mi Prueba 300 0.4 nozzle"}]}
            r = novedades_orca.revisar_perfiles([Path(d)], config)
            self.assertEqual(r["claves_que_orca_no_usa"], {"Mi PETG": ["clave_vieja"]})
            self.assertEqual(r["auto_sin_impresora"], [])


class TestCadYStl(unittest.TestCase):
    def test_pieza_cerrada_y_medidas(self):
        import numpy as np  # noqa: F401
        from cad import agujero_tornillo, caja, chaflan_inferior, exportar_stl, mover, restar

        import revisar_stl
        pieza = restar(caja(40, 20, 5, radio=2), mover(agujero_tornillo("M3", 5), x=10, y=10))
        pieza = chaflan_inferior(pieza, 0.4)
        ruta = Path(tempfile.mkdtemp()) / "p.stl"
        info = exportar_stl(pieza, ruta)
        self.assertEqual(info["medidas_mm"], (40.0, 20.0, 5.0))
        r = revisar_stl.analizar(revisar_stl.leer_stl(ruta), comun.cargar_impresora(IMPRESORA_PRUEBA), "PETG", [40, 20, 5])
        self.assertTrue(r["cerrada"])
        self.assertEqual(r["estado"], comun.APROBADO, r["hallazgos"])

    def test_sugiere_otra_impresora(self):
        import revisar_stl
        grande = {**IMP, "id": "grande", "nombre": "Marca Grande 400",
                  "area": {"x_min": 0, "x_max": 400, "y_min": 0, "y_max": 400, "z_max": 400}}
        chica = {**IMP, "id": "chica", "nombre": "Marca Chica 180",
                 "area": {"x_min": 0, "x_max": 180, "y_min": 0, "y_max": 180, "z_max": 180}}
        self.assertEqual(revisar_stl.entra_en([350, 20, 5], IMP), None)
        self.assertEqual(revisar_stl.entra_en([20, 20, 320], IMP), "tal cual")
        self.assertEqual(revisar_stl.entra_en([320, 20, 5], IMP), "girándola")
        otras = revisar_stl.otras_donde_entra([350, 20, 5], [IMP, grande, chica], IMP)
        self.assertEqual([(o["id"], o["como"]) for o in otras], [("grande", "tal cual")])
        from cad import caja, exportar_stl
        with tempfile.TemporaryDirectory() as d:
            carpeta = Path(d) / "impresoras"
            carpeta.mkdir()
            for datos in (IMP, grande, chica):
                (carpeta / f"{datos['id']}.json").write_text(json.dumps(datos), encoding="utf-8")
            stl = Path(d) / "larga.stl"
            exportar_stl(caja(350, 20, 5), stl)
            r = subprocess.run([sys.executable, str(SCRIPTS / "revisar_stl.py"), str(stl), "--impresora",
                                str(IMPRESORA_PRUEBA), "--otras", str(carpeta)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("Entra en otra impresora tuya: Marca Grande 400 (tal cual)", r.stdout)

    def test_malla_abierta_y_grande(self):
        import numpy as np

        import revisar_stl
        tri = np.array([[[0, 0, 0], [400, 0, 0], [0, 10, 0]]], dtype=float)
        r = revisar_stl.analizar(tri, comun.cargar_impresora(IMPRESORA_PRUEBA), "PLA")
        self.assertEqual(r["estado"], comun.RECHAZO)


class TestProducto(unittest.TestCase):
    def test_precio_y_borrador(self):
        import producto_tienda
        config = {"costos": {"precio_kwh": 100, "consumo_w": 200, "filamentos": {"PETG": {"precio_kg": 20000}}},
                  "tienda": {"margen_pct": 50, "costo_hora_maquina": 0, "embalaje": 0, "redondeo": 10}}
        p = producto_tienda.calcular_precio(100, 3600, "PETG", config)
        self.assertEqual(p["material"], 2000)
        self.assertEqual(p["luz"], 20)
        self.assertEqual(p["precio_sugerido"], 3030)
        self.assertEqual(p["faltan_datos"], [])


class TestCatalogo(unittest.TestCase):
    def test_agregar_listado_y_pagina(self):
        import catalogo as cat
        c = {"version": 1, "piezas": []}
        nuevas = cat.desde_listado(c, {"entries": [
            {"name": "impresiones/2026-09-15_llavero/foto.jpg", "type": "file"},
            {"name": "impresiones/2026-09-15_llavero/vista.png", "type": "file"},
            {"name": "impresiones/2026-11-21_soporte/pieza-1/plate_1.gcode", "type": "file"},
            {"name": "disenos/2026-10-02_caja/vista.png", "type": "file"},
            {"name": "taller-3d/config.json", "type": "file"}]})
        self.assertEqual(len(nuevas), 3)
        estados = {p["carpeta"]: p["estado"] for p in c["piezas"]}
        self.assertEqual(estados["impresiones/2026-11-21_soporte"], "laminada")
        self.assertEqual(estados["disenos/2026-10-02_caja"], "disenada")
        llavero = next(p for p in c["piezas"] if "llavero" in p["carpeta"])
        self.assertEqual(cat.imagen_de(llavero), "foto.jpg")  # la foto real va antes que la vista
        extra = cat.datos_de_informes(
            {"estado": "aprobado", "material": "PETG", "estimaciones": {"segundos": 3600, "gramos": 10},
             "costo": {"moneda": "ARS", "total": 500}}, {"medidas_mm": [10, 20, 30]}, {})
        pieza = cat.agregar(c, "impresiones/2026-11-21_soporte", nombre='<script>alert(1)</script>',
                            url_tienda="javascript:alert(1)", **extra)
        self.assertEqual(pieza["tiempo"], "1 h 00 min")
        self.assertNotIn("url_tienda", pieza)
        pagina = cat.generar_html(c)
        self.assertNotIn("<script>alert", pagina)
        self.assertNotIn("javascript:", pagina)
        self.assertIn("&lt;script&gt;", pagina)
        self.assertLess(pagina.index("noviembre 2026"), pagina.index("septiembre 2026"))
        with self.assertRaises(SystemExit):
            cat.agregar(c, "../afuera")


class TestImpresora(unittest.TestCase):
    """El plugin no trae impresoras: los datos se arman para la que elige el usuario."""

    CONFIG_ORCA = ("; printer_model = Marca Prueba 300\n; printer_settings_id = Mi Prueba 300 0.4 nozzle\n"
                   "; printable_area = 0x0,300x0,300x300,0x300\n; printable_height = 330\n"
                   "; gcode_flavor = klipper\n; nozzle_diameter = 0.4\n; machine_max_speed_x = 600,200\n"
                   "; machine_max_acceleration_x = 20000,1000\n; printer_structure = corexy\n")

    def gcode_orca(self, config):
        ruta = Path(tempfile.mkdtemp()) / "cubo.gcode"
        ruta.write_text("G1 X10 Y10\n; CONFIG_BLOCK_START\n" + config + "; CONFIG_BLOCK_END\n", encoding="utf-8")
        return ruta

    def test_sin_impresoras_del_plugin(self):
        self.assertFalse((SCRIPTS.parent / "datos" / "impresoras").exists())
        with self.assertRaises(SystemExit) as error:
            comun.cargar_impresora("ender-3-v3-plus")
        self.assertIn("no trae impresoras", str(error.exception))

    def test_datos_incompletos_o_raros(self):
        datos = json.loads(IMPRESORA_PRUEBA.read_text(encoding="utf-8"))
        self.assertEqual(comun.problemas_impresora(datos), [])
        sin_cama = {**datos, "limites": {"boquilla_max_c": 300}}
        self.assertTrue(any("cama_max_c" in p for p in comun.problemas_impresora(sin_cama)))
        self.assertTrue(comun.problemas_impresora({**datos, "limites": {"boquilla_max_c": 900, "cama_max_c": 100}}))
        self.assertTrue(comun.problemas_impresora({**datos, "fuentes": []}))
        self.assertTrue(comun.problemas_impresora({**datos, "area": {"x_min": 0, "x_max": 0, "y_min": 0,
                                                                    "y_max": 300, "z_max": 330}}))
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "x.json"
            ruta.write_text(json.dumps(sin_cama), encoding="utf-8")
            with self.assertRaises(SystemExit):
                comun.cargar_impresora(ruta)
            self.assertEqual(comun.impresoras_en([d]), [])

    def test_desde_gcode_y_comparar(self):
        import impresora
        ruta = self.gcode_orca(self.CONFIG_ORCA)
        borrador = impresora.desde_gcode(ruta)
        self.assertEqual(borrador["area"], {"x_min": 0.0, "x_max": 300.0, "y_min": 0.0, "y_max": 300.0, "z_max": 330.0})
        self.assertEqual((borrador["firmware"], borrador["boquilla_mm"], borrador["patron_perfiles"]),
                         ("klipper", 0.4, "Prueba 300"))
        self.assertIsNone(borrador["limites"]["boquilla_max_c"])
        self.assertTrue(any("boquilla_max_c" in x for x in borrador["pendiente"]))
        self.assertTrue(comun.problemas_impresora(borrador))  # sin límites del fabricante no sirve
        self.assertEqual(impresora.comparar(IMP, impresora.leer_configuracion(ruta)), [])
        otra = self.gcode_orca(self.CONFIG_ORCA.replace("300x300", "350x350").replace("klipper", "marlin2"))
        difs = impresora.comparar(IMP, impresora.leer_configuracion(otra))
        self.assertTrue(any("area.x_max" in d for d in difs) and any("firmware" in d for d in difs))
        r = subprocess.run([sys.executable, str(SCRIPTS / "impresora.py"), "validar", str(IMPRESORA_PRUEBA)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_elegir_entre_varias(self):
        plus = {**IMP, "id": "plus", "nombre": "Marca Prueba 300 Plus", "patron_perfiles": "Prueba 300 Plus",
                "perfiles_maquina": ["Mi Prueba 300 Plus 0.4 nozzle"]}
        elegir = revisar_gcode.elegir_impresora
        self.assertEqual(elegir("", "Mi Prueba 300 Plus 0.4 nozzle", [IMP, plus])["id"], "plus")
        self.assertEqual(elegir("", "AUTO filamento @Prueba 300 Plus", [IMP, plus])["id"], "plus")
        self.assertEqual(elegir("", "AUTO filamento @Prueba 300", [IMP, plus])["id"], "prueba")
        self.assertEqual(elegir("Marca Prueba 300", "otro nombre", [plus, IMP])["id"], "prueba")
        self.assertIsNone(elegir("Otra", "Otra impresora", [IMP, plus]))

    def test_guardia_usa_los_datos_del_usuario(self):
        sys.path.insert(0, str(RAIZ / "hooks"))
        import guardia
        anteriores = guardia.RAICES_DATOS
        try:
            with tempfile.TemporaryDirectory() as d:
                carpeta = Path(d) / "OrcaSlicer Claude" / "taller-3d" / "impresoras"
                carpeta.mkdir(parents=True)
                guardia.RAICES_DATOS = [Path(d)]
                # ABS con la cama a 105 °C: lo acepta el límite genérico (120) pero no esta impresora (100)
                texto = gcode("M140 S105\n" + BUENO, mat="ABS").read_text()
                self.assertEqual(guardia._impresora_para("Marca Prueba 300", "Mi Prueba 300 0.4 nozzle")["id"],
                                 "generica")
                self.assertEqual(guardia._revisar_gcode(texto), [])
                (carpeta / "prueba.json").write_text(IMPRESORA_PRUEBA.read_text(encoding="utf-8"), encoding="utf-8")
                self.assertEqual(guardia._impresora_para("Marca Prueba 300", "Mi Prueba 300 0.4 nozzle")["id"],
                                 "prueba")
                self.assertTrue(guardia._revisar_gcode(texto))
        finally:
            guardia.RAICES_DATOS = anteriores


class TestVariasImpresoras(unittest.TestCase):
    """Impresoras sin copia de usuario, OrcaSlicer.conf y perfiles AUTO de impresoras presentes."""

    def escribir(self, carpeta, nombre, datos):
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / nombre).write_text(json.dumps(datos), encoding="utf-8")

    def test_detectar_todas(self):
        import impresora
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self.escribir(d / "machine", "Mi Ender-3 V3 Plus 0.4 nozzle.json",
                          {"name": "Mi Ender-3 V3 Plus 0.4 nozzle", "inherits": "Creality Ender-3 V3 Plus 0.4 nozzle"})
            self.escribir(d / "filament", "Creality Generic PETG @Hi-all - Copy.json",
                          {"name": "Creality Generic PETG @Hi-all - Copy", "inherits": "Creality Generic PETG @Hi-all",
                           "compatible_printers": ["Creality Hi 0.6 nozzle", "Creality Hi 0.4 nozzle"]})
            self.escribir(d / "process", "Mi proceso.json",
                          {"name": "Mi proceso", "compatible_printers": ["Mi Ender-3 V3 Plus 0.4 nozzle"]})
            orca = {"models": [{"vendor": "Creality", "model": "Creality Hi", "nozzle_diameter": "0.4;0.6"},
                               {"vendor": "Creality", "model": "Creality K1C", "nozzle_diameter": "0.4"}],
                    "machine": "Creality Hi 0.4 nozzle"}
            lista = impresora.detectar([d / "machine"], [d / "process", d / "filament"], orca)
        por_modelo = {e["modelo"]: e for e in lista}
        self.assertEqual(lista[0]["modelo"], "Creality Hi")
        self.assertTrue(lista[0]["seleccionada"])
        self.assertEqual(lista[0]["copias_usuario"], [])
        self.assertEqual(lista[0]["boquillas"], ["0.4", "0.6"])
        self.assertIn("perfiles del usuario", lista[0]["fuentes"])
        self.assertEqual(por_modelo["Creality Ender-3 V3 Plus"]["copias_usuario"], ["Mi Ender-3 V3 Plus 0.4 nozzle"])
        self.assertIn("Creality K1C", por_modelo)
        self.assertNotIn("Mi Ender-3 V3 Plus", por_modelo)  # la copia nombrada en un perfil no es otra impresora
        sin_nada = impresora.detectar([], [], None)
        self.assertEqual(sin_nada, [])

    def test_patron_sin_ambiguedad(self):
        import impresora
        self.assertEqual(impresora.patron_de("Creality Hi"), "Creality Hi")
        self.assertEqual(impresora.patron_de("Creality Ender-3 V3 Plus"), "Ender-3 V3 Plus")
        self.assertFalse(revisar_gcode.contiene_palabra("Generic PLA High Flow @Otra", "Hi"))
        self.assertTrue(revisar_gcode.contiene_palabra("Generic PETG @Creality Hi-all", "Creality Hi"))
        hi = {**IMP, "id": "hi", "nombre": "Creality Hi", "patron_perfiles": "Hi", "perfiles_maquina": []}
        self.assertIsNone(revisar_gcode.elegir_impresora("", "Generic PLA High Flow @Otra", [hi]))
        _, _, avisos = impresora.validar(hi)
        self.assertTrue(any("muy corto" in a for a in avisos))

    def test_conf_de_orca_no_se_trae(self):
        def correr(modo, entrada):
            return subprocess.run([sys.executable, str(RAIZ / "hooks" / "guardia.py"), modo],
                                  input=json.dumps({"tool_input": entrada}), capture_output=True, text=True)
        r = correr("pre-stage", {"paths": ["/home/leo/.config/OrcaSlicer/OrcaSlicer.conf"]})
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("código de acceso", r.stderr)
        self.assertEqual(correr("pre-stage", {"paths": [r"C:\Users\leo\OrcaSlicer\orcaslicer.conf"]}).returncode, 2)
        self.assertEqual(correr("pre-stage", {"paths": ["/home/leo/Documentos/Taller 3D/taller-3d/config.json"]}).returncode, 0)
        self.assertEqual(correr("pre-bash", {"command": "cat ~/.config/OrcaSlicer/OrcaSlicer.conf"}).returncode, 2)
        self.assertEqual(correr("pre-bash", {"command": "grep machine ~/.config/OrcaSlicer/OrcaSlicer.conf"}).returncode, 2)
        filtrado = ("python3 -c 'import json,sys; c=json.load(open(sys.argv[1], encoding=\"utf-8\")); "
                    "print(json.dumps({\"models\": c.get(\"models\", []), \"machine\": (c.get(\"presets\") or {}).get(\"machine\")}))' "
                    "~/.config/OrcaSlicer/OrcaSlicer.conf")
        self.assertEqual(correr("pre-bash", {"command": filtrado}).returncode, 0)
        self.assertEqual(correr("pre-bash", {"command": filtrado.replace("models", "local_machines")}).returncode, 2)
        ps = (r'$c = Get-Content -Raw -Encoding UTF8 "C:\Users\leo\AppData\Roaming\OrcaSlicer\OrcaSlicer.conf" '
              r'| ConvertFrom-Json; @{models = $c.models; machine = $c.presets.machine} | ConvertTo-Json -Depth 5 -Compress')
        self.assertEqual(correr("pre-bash", {"command": ps}).returncode, 0)
        self.assertEqual(correr("pre-bash", {"command": r'type "C:\Users\leo\AppData\Roaming\OrcaSlicer\OrcaSlicer.conf"'}).returncode, 2)

    def test_auto_de_impresora_con_copia_no_es_huerfano(self):
        import novedades_orca
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self.escribir(d / "process", "AUTO proceso @Prueba 300.json", {"name": "AUTO proceso @Prueba 300"})
            self.escribir(d / "machine", "Mi Prueba 300 0.4 nozzle.json",
                          {"name": "Mi Prueba 300 0.4 nozzle", "inherits": "Marca Prueba 300 0.4 nozzle"})
            config = {"impresoras": [{"id": "otra", "perfil_maquina": "Mi Otra 0.4 nozzle"}]}
            sin = novedades_orca.revisar_perfiles([d / "process"], config)
            con = novedades_orca.revisar_perfiles([d / "process"], config, [d / "machine"])
        self.assertEqual(sin["auto_sin_impresora"], ["AUTO proceso @Prueba 300"])
        self.assertEqual(con["auto_sin_impresora"], [])

    def test_crear_copia_de_maquina(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, str(SCRIPTS / "perfil_orca.py"), "crear", "--tipo", "maquina",
                                "--nombre", "Mi Prueba 300 0.4 nozzle", "--hereda", "Marca Prueba 300 0.4 nozzle",
                                "--impresora", str(IMPRESORA_PRUEBA), "--salida", d],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            perfil = json.loads((Path(d) / "Mi Prueba 300 0.4 nozzle.json").read_text(encoding="utf-8"))
            info = (Path(d) / "Mi Prueba 300 0.4 nozzle.info").read_text(encoding="utf-8")
        self.assertEqual(perfil["inherits"], "Marca Prueba 300 0.4 nozzle")
        self.assertEqual(perfil["printer_settings_id"], "Mi Prueba 300 0.4 nozzle")
        self.assertIn("base_id = prueba-maquina", info)


class TestGuardia(unittest.TestCase):
    def correr(self, modo, datos):
        return subprocess.run([sys.executable, str(RAIZ / "hooks" / "guardia.py"), modo],
                              input=json.dumps(datos), capture_output=True, text=True)

    def test_commit_gcode_peligroso(self):
        ruta = gcode("M104 S330\n" + BUENO)
        r = self.correr("pre-commit", {"tool_input": {"files": [
            {"devicePath": "/home/leo/Documentos/x/pieza.gcode", "stagedPath": str(ruta)}]}})
        self.assertEqual(r.returncode, 2, r.stderr)

    def test_commit_gcode_bueno(self):
        r = self.correr("pre-commit", {"tool_input": {"files": [
            {"devicePath": "/home/leo/Documentos/x/pieza.gcode", "stagedPath": str(gcode(BUENO))}]}})
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_commit_perfil_malo(self):
        tmp = Path(tempfile.mkdtemp()) / "p.json"
        tmp.write_text(json.dumps({"from": "User", "name": "AUTO filamento @Prueba 300",
                                   "inherits": "Generic PETG @Prueba 300-all",
                                   "filament_settings_id": ["AUTO filamento @Prueba 300"],
                                   "nozzle_temperature": ["320"]}))
        r = self.correr("pre-commit", {"tool_input": {"files": [
            {"devicePath": "/home/leo/.config/OrcaSlicer/user/default/filament/x.json", "stagedPath": str(tmp)}]}})
        self.assertEqual(r.returncode, 2, r.stderr)
        # Windows (datos movidos fuera de AppData) y Orca portable con data_dir
        for destino in (r"C:\Users\leo\OrcaSlicer\user\default\filament\x.json",
                        r"D:\Orca\data_dir\user\default\filament\x.json"):
            r = self.correr("pre-commit", {"tool_input": {"files": [{"devicePath": destino, "stagedPath": str(tmp)}]}})
            self.assertEqual(r.returncode, 2, destino)

    def test_commit_perfil_con_script(self):
        tmp = Path(tempfile.mkdtemp()) / "p.json"
        tmp.write_text(json.dumps({"from": "User", "name": "AUTO proceso @Prueba 300",
                                   "inherits": "0.20mm Standard @Marca Prueba 300",
                                   "print_settings_id": "AUTO proceso @Prueba 300",
                                   "post_process": "/home/leo/x.sh"}))
        r = self.correr("pre-commit", {"tool_input": {"files": [
            {"devicePath": "/home/leo/.config/OrcaSlicer/user/default/process/x.json", "stagedPath": str(tmp)}]}})
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("post_process", r.stderr)

    def test_commit_sistema(self):
        r = self.correr("pre-commit", {"tool_input": {"files": [
            {"devicePath": "/home/leo/.config/OrcaSlicer/system/Creality.json", "stagedPath": "/no/existe"}]}})
        self.assertEqual(r.returncode, 2)

    def test_commit_ajeno(self):
        r = self.correr("pre-commit", {"tool_input": {"files": [
            {"devicePath": "/home/leo/Documentos/odoo/factura.pdf", "stagedPath": "/no/existe"}]}})
        self.assertEqual(r.returncode, 0)

    def test_bash(self):
        self.assertEqual(self.correr("pre-bash", {"tool_input": {"command":
            "curl -X POST http://192.168.0.50:7125/printer/print/start?filename=x.gcode"}}).returncode, 2)
        self.assertEqual(self.correr("pre-bash", {"tool_input": {"command":
            "curl -F file=@/mnt/user-data/uploads/pieza.stl https://ejemplo.com/subir"}}).returncode, 2)
        self.assertEqual(self.correr("pre-bash", {"tool_input": {"command":
            "python3 revisar_gcode.py pieza.gcode"}}).returncode, 0)
        self.assertEqual(self.correr("pre-bash", {"tool_input": {"command":
            "cp pieza.stl /mnt/user-data/outputs/"}}).returncode, 0)

    def commit(self, destino, **archivo):
        return self.correr("pre-commit", {"tool_input": {"files": [{"devicePath": destino, **archivo}]}})

    def test_commit_sin_stagedpath(self):
        bueno = str(gcode(BUENO))
        self.assertEqual(self.commit("/home/leo/x/pieza.gcode", fileUuid="abc").returncode, 2)
        self.assertEqual(self.commit("/home/leo/x/pieza.gcode", fileUuid="abc", stagedPath=bueno).returncode, 2)
        self.assertEqual(self.commit("/home/leo/x/pieza.gcode", stagedPath="/no/existe.gcode").returncode, 2)
        self.assertEqual(self.commit("/home/leo/x/pieza.bgcode", stagedPath=bueno).returncode, 2)
        self.assertEqual(self.commit("/home/leo/x/foto.png", fileUuid="abc").returncode, 0)

    def test_commit_zonas_de_orca(self):
        ruta = str(gcode(BUENO))
        for destino in (r"C:\Users\leo\OrcaSlicer\user\..\system\Creality.json",
                        r"C:\Users\leo\OrcaSlicer\orca_plugins\x.py", r"C:\Users\leo\OrcaSlicer\OrcaSlicer.conf",
                        "C:/Program Files/OrcaSlicer/resources/profiles/Creality.json"):
            self.assertEqual(self.commit(destino, stagedPath=ruta).returncode, 2, destino)

    def test_commit_perfil_json_roto(self):
        tmp = Path(tempfile.mkdtemp()) / "p.json"
        tmp.write_text("{no es json")
        r = self.commit("/home/leo/.config/OrcaSlicer/user/default/process/x.json", stagedPath=str(tmp))
        self.assertEqual(r.returncode, 2)

    def test_commit_3mf(self):
        import zipfile
        def proyecto(nombre, ajustes, gcode_adentro=None):
            ruta = Path(tempfile.mkdtemp()) / nombre
            with zipfile.ZipFile(ruta, "w") as z:
                z.writestr("Metadata/project_settings.config", json.dumps(ajustes))
                if gcode_adentro:
                    z.writestr("Metadata/plate_1.gcode", gcode_adentro)
            return str(ruta)
        self.assertEqual(self.commit("/x/p.3mf", stagedPath=proyecto("a.3mf", {"post_process": ["/x.sh"]})).returncode, 2)
        self.assertEqual(self.commit("/x/p.3mf", stagedPath=proyecto("b.3mf", {"nozzle_temperature": ["nil", "420"]})).returncode, 2)
        self.assertEqual(self.commit("/x/p.3mf", stagedPath=proyecto("c.3mf", {"nozzle_temperature": ["240"],
                         "machine_start_gcode": "G28\nM104 S[nozzle_temperature_initial_layer]"})).returncode, 0)
        malo = gcode("M109S400\n" + BUENO).read_text()
        self.assertEqual(self.commit("/x/p.gcode.3mf", stagedPath=proyecto("d.gcode.3mf", {}, malo)).returncode, 2)
        self.assertEqual(self.commit("/x/p.3mf", stagedPath=str(gcode(BUENO))).returncode, 2)  # no es zip

    def test_write_y_edit(self):
        bueno = gcode(BUENO)
        self.assertEqual(self.correr("pre-write", {"tool_input": {"file_path": "/tmp/n.gcode",
                         "content": "M104 S400\n" + BUENO}}).returncode, 2)
        self.assertEqual(self.correr("pre-write", {"tool_input": {"file_path": str(bueno),
                         "old_string": "G1 X120 Y100 E1.2", "new_string": "M104 S400\nG1 X120 Y100 E1.2"}}).returncode, 2)
        self.assertEqual(self.correr("pre-write", {"tool_input": {"file_path": str(bueno),
                         "old_string": "G1 X120 Y120", "new_string": "G1 X121 Y120"}}).returncode, 0)
        self.assertEqual(self.correr("pre-write", {"tool_input": {"file_path": "/tmp/gramatica.g",
                         "content": "grammar Expr;\nexpr: term;\n"}}).returncode, 0)
        self.assertEqual(self.correr("pre-write", {"tool_input": {"file_path":
                         "/home/u/.config/OrcaSlicer/system/Creality.json", "content": "{}"}}).returncode, 2)

    def test_bash_mas_casos(self):
        casos = {
            "curl -sF file=@pieza.stl https://x.com/up": 2,
            "curl -f -o pieza.stl https://x.com/pieza.stl": 0,
            "rclone copy pieza.3mf drive:": 2,
            "lftp -e 'put pieza.gcode' host": 2,
            "git log --grep=ftp -- pieza.stl": 0,
            "find ~ -path '*OrcaSlicer/user*' -name '*.json' 2>/dev/null | head": 0,
            "ls ~/.config/OrcaSlicer/user/default/process > /tmp/lista.txt": 0,
            "cat x.json > ~/.config/OrcaSlicer/user/default/process/x.json": 2,
            'cp /tmp/x.json "$HOME/Library/Application Support/OrcaSlicer/user/default/process/"': 2,
            "cp ~/.config/OrcaSlicer/user/default/process/x.json ~/respaldo/": 0,
            "Copy-Item x.json -Destination C:\\Users\\leo\\OrcaSlicer\\user\\default\\process\\": 2,
            "sed -i 's/240/400/' ~/.config/OrcaSlicer/user/default/filament/x.json": 2,
        }
        for comando, esperado in casos.items():
            self.assertEqual(self.correr("pre-bash", {"tool_input": {"command": comando}}).returncode, esperado, comando)

    def test_entrada_rota(self):
        r = subprocess.run([sys.executable, str(RAIZ / "hooks" / "guardia.py"), "pre-commit"],
                           input="no es json", capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
