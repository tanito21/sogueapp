"""pruebas unitarias de logica_login (ejecutar: python -m unittest -v)."""

import base64
import datetime
import hashlib
import os
import sqlite3
import struct
import sys
import tempfile
import unittest

import icono_sogue
import logica_login

BD_PRUEBA = "test_soguebase.db"


class PruebasLoginYRoles(unittest.TestCase):

    def setUp(self):
        # usamos una base temporal y pocas iteraciones para que las pruebas sean rápidas
        self.bd_original = logica_login.nombre_bd
        self.iteraciones_original = logica_login.ITERACIONES
        logica_login.nombre_bd = BD_PRUEBA
        logica_login.ITERACIONES = 1000
        if os.path.exists(BD_PRUEBA):
            os.remove(BD_PRUEBA)
        logica_login.inicializar_db()
        self.pregunta = "¿Cuál es tu comida favorita?"
        self.respuesta = "Milanesa"

    def tearDown(self):
        # borramos la base de prueba y dejamos el módulo como estaba
        logica_login.nombre_bd = self.bd_original
        logica_login.ITERACIONES = self.iteraciones_original
        if os.path.exists(BD_PRUEBA):
            os.remove(BD_PRUEBA)

    def _crear(self, nombre, rol="completo", creado_por=None):
        """crea un usuario de prueba con clave Clave123."""
        return logica_login.crear_usuario(
            nombre, "Clave123", self.pregunta, self.respuesta, rol, creado_por)

    #creación e inicio de sesión

    def test_crear_y_verificar_usuario(self):
        """un usuario se crea bien y puede iniciar sesión."""
        self.assertTrue(logica_login.crear_usuario(
            "admin_prueba", "Clave123", self.pregunta, self.respuesta))
        self.assertTrue(logica_login.verificar_usuario("admin_prueba", "Clave123"))
        self.assertFalse(logica_login.verificar_usuario("admin_prueba", "clavemala"))

    def test_no_permite_usuario_duplicado(self):
        """no se puede crear dos veces el mismo usuario."""
        logica_login.crear_usuario("repetido", "Clave123", self.pregunta, self.respuesta)
        self.assertFalse(logica_login.crear_usuario(
            "repetido", "OtraClave1", self.pregunta, self.respuesta))

    def test_duplicado_ignora_mayusculas(self):
        """'Ana' y 'ana' cuentan como el mismo usuario."""
        logica_login.crear_usuario("Ana", "Clave123", self.pregunta, self.respuesta)
        self.assertFalse(logica_login.crear_usuario(
            "ana", "Clave123", self.pregunta, self.respuesta))
        self.assertTrue(logica_login.verificar_usuario("ANA", "Clave123"))

    def test_no_crea_usuario_con_datos_vacios(self):
        """no se crea el usuario si falta nombre, pregunta o respuesta."""
        self.assertFalse(logica_login.crear_usuario("", "Clave123", self.pregunta, self.respuesta))
        self.assertFalse(logica_login.crear_usuario("sin_resp", "Clave123", self.pregunta, "  "))
        self.assertFalse(logica_login.crear_usuario("sin_preg", "Clave123", "", self.respuesta))

    def test_login_con_campos_vacios_o_inexistente(self):
        """el login falla con campos vacíos o con un usuario que no existe."""
        self.assertFalse(logica_login.verificar_usuario("", ""))
        self.assertFalse(logica_login.verificar_usuario("fantasma", "Clave123"))

    def test_clave_se_guarda_como_hash(self):
        """la contraseña nunca queda guardada en texto plano."""
        logica_login.crear_usuario("hash_test", "Clave123", self.pregunta, self.respuesta)
        con = sqlite3.connect(BD_PRUEBA)
        clave, respuesta = con.execute(
            "SELECT clave, respuesta FROM usuarios WHERE usuario='hash_test'").fetchone()
        con.close()
        self.assertNotIn("Clave123", clave)
        self.assertTrue(clave.startswith("pbkdf2_sha256$"))
        self.assertNotIn("milanesa", respuesta.lower())

    #reglas de la contraseña

    def test_clave_es_segura(self):
        """reglas de seguridad de la contraseña."""
        self.assertFalse(logica_login.clave_es_segura("corta1A")[0])         # muy corta
        self.assertFalse(logica_login.clave_es_segura("clavesinnumero")[0])  # sin número
        self.assertFalse(logica_login.clave_es_segura("clavesinmayus1")[0])  # sin mayúscula
        self.assertFalse(logica_login.clave_es_segura("CLAVESINMINUS1")[0])  # sin minúscula
        self.assertTrue(logica_login.clave_es_segura("Clave123")[0])         # cumple todo

    def test_clave_insegura_devuelve_motivo(self):
        """cuando la clave no cumple, se devuelve un motivo para mostrar."""
        ok, motivo = logica_login.clave_es_segura("abc")
        self.assertFalse(ok)
        self.assertTrue(motivo)
        self.assertEqual(logica_login.clave_es_segura("Clave123"), (True, ""))
        self.assertFalse(logica_login.clave_es_segura(None)[0])

    def test_no_crea_usuario_con_clave_insegura(self):
        """no se crea el usuario si la contraseña no es segura."""
        self.assertFalse(logica_login.crear_usuario(
            "usuario_debil", "abc", self.pregunta, self.respuesta))
        self.assertFalse(logica_login.usuario_existe("usuario_debil"))

    #recuperación de contraseña

    def test_recuperar_clave_con_respuesta_correcta(self):
        """flujo completo de recuperación de contraseña."""
        logica_login.crear_usuario("con_recuperacion", "Clave123", self.pregunta, self.respuesta)

        # la pregunta guardada coincide con la registrada
        self.assertEqual(
            logica_login.obtener_pregunta_secreta("con_recuperacion"), self.pregunta)

        # la respuesta correcta (sin importar espacios ni mayúsculas) valida
        self.assertTrue(logica_login.verificar_respuesta_secreta("con_recuperacion", "  milanesa  "))

        # cambiamos la clave y comprobamos el acceso con la nueva
        self.assertTrue(logica_login.cambiar_clave("con_recuperacion", "NuevaClave1"))
        self.assertTrue(logica_login.verificar_usuario("con_recuperacion", "NuevaClave1"))
        self.assertFalse(logica_login.verificar_usuario("con_recuperacion", "Clave123"))

    def test_recuperar_clave_con_respuesta_incorrecta(self):
        """una respuesta secreta incorrecta se rechaza."""
        logica_login.crear_usuario("con_recuperacion2", "Clave123", self.pregunta, self.respuesta)
        self.assertFalse(logica_login.verificar_respuesta_secreta("con_recuperacion2", "pizza"))

    def test_cambiar_clave_no_permite_clave_insegura(self):
        """no se puede cambiar a una contraseña que incumpla las reglas."""
        logica_login.crear_usuario("con_recuperacion3", "Clave123", self.pregunta, self.respuesta)
        self.assertFalse(logica_login.cambiar_clave("con_recuperacion3", "abc"))
        # la clave anterior sigue funcionando
        self.assertTrue(logica_login.verificar_usuario("con_recuperacion3", "Clave123"))

    def test_recuperacion_con_usuario_inexistente(self):
        """con un usuario que no existe, todo devuelve vacío o falso."""
        self.assertIsNone(logica_login.obtener_pregunta_secreta("fantasma"))
        self.assertFalse(logica_login.verificar_respuesta_secreta("fantasma", "x"))
        self.assertFalse(logica_login.cambiar_clave("fantasma", "Clave123"))

    #roles

    def test_crear_usuario_con_rol(self):
        """el usuario se crea con un rol específico y se puede consultar."""
        self.assertTrue(logica_login.crear_usuario(
            "admin_test", "Clave123", self.pregunta, self.respuesta, rol="admin"))
        self.assertEqual(logica_login.obtener_rol_usuario("admin_test"), "admin")

    def test_rol_por_defecto(self):
        """si no se indica rol, se asigna 'completo'."""
        logica_login.crear_usuario("user_normal", "Clave123", self.pregunta, self.respuesta)
        self.assertEqual(logica_login.obtener_rol_usuario("user_normal"), "completo")

    def test_roles_de_la_interfaz(self):
        """los tres roles comunes del registro se pueden guardar."""
        for rol in ("completo", "presupuesto", "ahorro"):
            nombre = f"user_{rol}"
            self.assertTrue(logica_login.crear_usuario(
                nombre, "Clave123", self.pregunta, self.respuesta, rol))
            self.assertEqual(logica_login.obtener_rol_usuario(nombre), rol)

    def test_rol_invalido_no_crea_usuario(self):
        """un rol que no existe se rechaza."""
        self.assertFalse(logica_login.crear_usuario(
            "rol_raro", "Clave123", self.pregunta, self.respuesta, rol="superdios"))
        self.assertFalse(logica_login.usuario_existe("rol_raro"))

    def test_rol_de_usuario_inexistente(self):
        """consultar el rol de alguien que no existe devuelve none."""
        self.assertIsNone(logica_login.obtener_rol_usuario("fantasma"))

    #administrador (ya no hay uno fijo)

    def test_no_hay_admin_automatico(self):
        """una base nueva no trae ningún administrador ni usuario."""
        self.assertFalse(logica_login.existe_admin())
        self.assertEqual(logica_login.obtener_todos_los_usuarios(), [])
        # repetir la inicialización tampoco crea nada
        logica_login.inicializar_db()
        self.assertEqual(logica_login.obtener_todos_los_usuarios(), [])

    def test_primer_admin_se_registra_libremente(self):
        """mientras no haya admin, cualquiera puede registrar el primero."""
        self.assertTrue(self._crear("jefe", "admin"))
        self.assertTrue(logica_login.existe_admin())
        self.assertTrue(logica_login.es_admin("JEFE"))
        self.assertFalse(logica_login.es_admin("fantasma"))

    def test_segundo_admin_solo_lo_crea_un_admin(self):
        """cuando ya hay admin, el registro común no puede crear otro."""
        self._crear("jefe", "admin")
        self._crear("ana")
        self.assertFalse(self._crear("intruso", "admin"))
        self.assertFalse(self._crear("intruso", "admin", creado_por="ana"))
        self.assertFalse(self._crear("intruso", "admin", creado_por="fantasma"))
        self.assertFalse(logica_login.usuario_existe("intruso"))
        self.assertTrue(self._crear("jefe2", "admin", creado_por="jefe"))
        self.assertEqual(logica_login.obtener_rol_usuario("jefe2"), "admin")

    def test_listado_de_usuarios(self):
        """el listado devuelve (id, usuario, rol) de todos los usuarios."""
        logica_login.crear_usuario("listado1", "Clave123", self.pregunta, self.respuesta, "ahorro")
        filas = logica_login.obtener_todos_los_usuarios()
        self.assertIn("listado1", [f[1] for f in filas])
        self.assertTrue(all(len(f) == 3 for f in filas))

    #funciones del administrador

    def _escenario_admin(self):
        """un admin (jefe) y dos usuarios con presupuesto."""
        self._crear("jefe", "admin")
        self._crear("ana")
        self._crear("beto")
        logica_login.generar_presupuesto("ana", 1000000)
        logica_login.generar_presupuesto("beto", 2000000)

    def test_admin_cambia_rol(self):
        """el admin cambia el rol de otro usuario, pero no el suyo ni a roles inválidos."""
        self._escenario_admin()
        self.assertEqual(logica_login.cambiar_rol_usuario("jefe", "ana", "ahorro"), (True, ""))
        self.assertEqual(logica_login.obtener_rol_usuario("ana"), "ahorro")
        self.assertFalse(logica_login.cambiar_rol_usuario("jefe", "jefe", "completo")[0])
        self.assertFalse(logica_login.cambiar_rol_usuario("jefe", "ana", "superdios")[0])
        self.assertFalse(logica_login.cambiar_rol_usuario("jefe", "fantasma", "ahorro")[0])
        self.assertEqual(logica_login.obtener_rol_usuario("jefe"), "admin")

    def test_usuario_comun_no_puede_administrar(self):
        """sin ser admin, ninguna acción de administración funciona."""
        self._escenario_admin()
        self.assertFalse(logica_login.cambiar_rol_usuario("ana", "beto", "admin")[0])
        self.assertFalse(logica_login.restablecer_clave_usuario("ana", "beto", "Nueva1234")[0])
        self.assertFalse(logica_login.eliminar_usuario("ana", "beto")[0])
        self.assertIsNone(logica_login.obtener_resumen_usuarios("ana"))
        self.assertTrue(logica_login.verificar_usuario("beto", "Clave123"))
        self.assertTrue(logica_login.usuario_existe("beto"))

    def test_admin_restablece_clave(self):
        """el admin le pone una clave nueva (segura) a un usuario."""
        self._escenario_admin()
        self.assertFalse(logica_login.restablecer_clave_usuario("jefe", "ana", "abc")[0])
        self.assertTrue(logica_login.verificar_usuario("ana", "Clave123"))
        self.assertEqual(
            logica_login.restablecer_clave_usuario("jefe", "ana", "Temporal99"), (True, ""))
        self.assertTrue(logica_login.verificar_usuario("ana", "Temporal99"))
        self.assertFalse(logica_login.verificar_usuario("ana", "Clave123"))
        self.assertFalse(logica_login.restablecer_clave_usuario("jefe", "fantasma", "Temporal99")[0])

    def test_admin_elimina_usuario_con_sus_datos(self):
        """eliminar un usuario borra su presupuesto, ingreso y gastos; no los de otros."""
        self._escenario_admin()
        logica_login.registrar_gasto("ana", "Deseos y Ocio", "cine", 50000)
        logica_login.registrar_gasto("beto", "Deseos y Ocio", "cine", 70000)
        self.assertEqual(logica_login.eliminar_usuario("jefe", "ana"), (True, ""))
        self.assertFalse(logica_login.usuario_existe("ana"))
        self.assertEqual(logica_login.obtener_categorias("ana"), [])
        con = sqlite3.connect(BD_PRUEBA)
        gastos = con.execute("SELECT COUNT(*) FROM gastos").fetchone()[0]
        ingresos = con.execute("SELECT COUNT(*) FROM ingresos").fetchone()[0]
        con.close()
        self.assertEqual(gastos, 1)
        self.assertEqual(ingresos, 1)
        self.assertEqual(len(logica_login.obtener_categorias("beto")), 3)

    def test_admin_no_se_elimina_a_si_mismo(self):
        """un admin no puede borrar su propia cuenta; usuarios inexistentes se rechazan."""
        self._escenario_admin()
        self.assertFalse(logica_login.eliminar_usuario("jefe", "jefe")[0])
        self.assertFalse(logica_login.eliminar_usuario("jefe", "fantasma")[0])
        self.assertTrue(logica_login.es_admin("jefe"))

    def test_resumen_de_usuarios_para_admin(self):
        """el admin ve cada cuenta con cantidad de categorías, presupuesto y gastado."""
        self._escenario_admin()
        logica_login.registrar_gasto("ana", "Deseos y Ocio", "cine", 50000)
        filas = {f[1]: f for f in logica_login.obtener_resumen_usuarios("jefe")}
        self.assertEqual(set(filas), {"jefe", "ana", "beto"})
        self.assertEqual(filas["jefe"][2:], ("admin", 0, 0, 0))
        self.assertEqual(filas["ana"][2:], ("completo", 3, 1000000.0, 50000.0))
        self.assertEqual(filas["beto"][2:], ("completo", 3, 2000000.0, 0.0))

    #presupuesto de cada usuario

    def _crear_dos_usuarios(self):
        """crea a ana y beto para las pruebas de presupuesto."""
        for nombre in ("ana", "beto"):
            logica_login.crear_usuario(nombre, "Clave123", self.pregunta, self.respuesta)

    def test_generar_presupuesto_50_30_20(self):
        """el ingreso se reparte 50/30/20 en tres categorías, en orden."""
        self._crear_dos_usuarios()
        self.assertTrue(logica_login.generar_presupuesto("ana", "1.000.000"))
        categorias = logica_login.obtener_categorias("ana")
        self.assertEqual([c[0] for c in categorias],
                         ["Necesidades Básicas", "Deseos y Ocio", "Ahorro e Inversión"])
        self.assertEqual([c[1] for c in categorias], [500000.0, 300000.0, 200000.0])
        self.assertTrue(all(c[2] == 0 for c in categorias))
        self.assertEqual(logica_login.obtener_ingreso("ana"), 1000000.0)

    def test_tres_plantillas_predeterminadas(self):
        """las tres plantillas suman el 100% del ingreso y se pueden generar."""
        self._crear_dos_usuarios()
        self.assertEqual(set(logica_login.PLANTILLAS_PRESUPUESTO),
                         {"50/30/20", "Objetivos", "Básico"})
        esperado = {"50/30/20": 3, "Objetivos": 5, "Básico": 3}
        for metodo, cantidad in esperado.items():
            self.assertTrue(logica_login.generar_presupuesto("ana", 2000000, metodo))
            categorias = logica_login.obtener_categorias("ana")
            self.assertEqual(len(categorias), cantidad)
            self.assertAlmostEqual(sum(c[1] for c in categorias), 2000000.0)
        basico = logica_login.PLANTILLAS_PRESUPUESTO["Básico"]
        self.assertEqual([n for n, _ in basico], ["Comidas", "Ahorro", "Ocio"])

    def test_metodo_desconocido_no_genera(self):
        """un método que no existe se rechaza y no borra el presupuesto."""
        self._crear_dos_usuarios()
        logica_login.generar_presupuesto("ana", 1000000)
        self.assertFalse(logica_login.generar_presupuesto("ana", 1000000, "inventado"))
        self.assertEqual(len(logica_login.obtener_categorias("ana")), 3)

    def test_presupuesto_personalizado(self):
        """el usuario arma su reparto con los porcentajes que quiera."""
        self._crear_dos_usuarios()
        reparto = [("Comidas", 40), ("Ahorro", "35"), ("Ocio", "25%")]
        self.assertTrue(logica_login.generar_presupuesto(
            "ana", 1000000, logica_login.METODO_PERSONALIZADO, reparto))
        self.assertEqual(
            logica_login.obtener_categorias("ana"),
            [("Comidas", 400000.0, 0.0), ("Ahorro", 350000.0, 0.0), ("Ocio", 250000.0, 0.0)])

    def test_presupuesto_personalizado_invalido(self):
        """repartos que no suman 100, repetidos o mal escritos no se aceptan ni borran nada."""
        self._crear_dos_usuarios()
        logica_login.generar_presupuesto("ana", 1000000)
        personalizado = logica_login.METODO_PERSONALIZADO
        invalidos = [
            None, [],
            [("Comidas", 50), ("Ocio", 40)],                 # suma 90
            [("Comidas", 60), ("Ocio", 60)],                 # suma 120
            [("Comidas", 50), ("comidas", 50)],              # repetida
            [("", 100)],                                     # sin nombre
            [("Comidas", "abc"), ("Ocio", 100)],             # porcentaje inválido
            [("Comidas", 0), ("Ocio", 100)],                 # porcentaje cero
            [("Comidas", -10), ("Ocio", 110)],               # negativo
            [("x" * 41, 100)],                               # nombre muy largo
        ]
        for reparto in invalidos:
            self.assertFalse(logica_login.generar_presupuesto(
                "ana", 1000000, personalizado, reparto), reparto)
        self.assertEqual(len(logica_login.obtener_categorias("ana")), 3)

    def test_validar_distribucion_devuelve_motivo(self):
        """validar_distribucion explica por qué no sirve y limpia los nombres."""
        ok, motivo, lista = logica_login.validar_distribucion([("Comidas", 50), ("Ocio", 40)])
        self.assertFalse(ok)
        self.assertIn("100", motivo)
        self.assertEqual(lista, [])
        ok, motivo, lista = logica_login.validar_distribucion(
            [("  Comidas   rápidas ", "33,3"), ("Ahorro", 66.7)])
        self.assertTrue(ok)
        self.assertEqual(lista[0], ("Comidas rápidas", 33.3))

    def test_convertir_porcentaje(self):
        """acepta 25, 12,5 y 30% y rechaza lo que no sirve."""
        self.assertEqual(logica_login.convertir_porcentaje("25"), 25.0)
        self.assertEqual(logica_login.convertir_porcentaje("12,5"), 12.5)
        self.assertEqual(logica_login.convertir_porcentaje(" 30% "), 30.0)
        self.assertEqual(logica_login.convertir_porcentaje(100), 100.0)
        for invalido in ("", "abc", "0", "-5", "101", "nan", "inf", None):
            self.assertIsNone(logica_login.convertir_porcentaje(invalido))

    def test_describir_plantilla(self):
        """cada método tiene una descripción para la interfaz."""
        self.assertIn("Necesidades Básicas 50%", logica_login.describir_plantilla("50/30/20"))
        self.assertIn("Comidas 50%", logica_login.describir_plantilla("Básico"))
        self.assertIn("100%", logica_login.describir_plantilla(logica_login.METODO_PERSONALIZADO))
        self.assertEqual(logica_login.describir_plantilla("inventado"), "")

    def test_presupuesto_es_individual(self):
        """cada usuario ve solo su presupuesto y regenerar no toca el de otro."""
        self._crear_dos_usuarios()
        logica_login.generar_presupuesto("ana", 1000000)
        self.assertEqual(logica_login.obtener_categorias("beto"), [])

        logica_login.generar_presupuesto("beto", 2000000)
        logica_login.generar_presupuesto("ana", 3000000)   # reemplaza solo el de ana
        self.assertEqual(logica_login.obtener_categorias("ana")[0][1], 1500000.0)
        self.assertEqual(len(logica_login.obtener_categorias("ana")), 3)
        self.assertEqual(logica_login.obtener_categorias("beto")[0][1], 1000000.0)

    def test_generar_presupuesto_borra_solo_gastos_propios(self):
        """al regenerar se borran los gastos de ese usuario, no los de otros."""
        self._crear_dos_usuarios()
        logica_login.generar_presupuesto("ana", 1000000)
        con = sqlite3.connect(BD_PRUEBA)
        ids = dict(con.execute("SELECT usuario, id FROM usuarios").fetchall())
        for nombre in ("ana", "beto"):
            con.execute("INSERT INTO gastos(categoria, concepto, monto, usuario_id) "
                        "VALUES('Deseos y Ocio','cine',50000,?)", (ids[nombre],))
        con.commit()
        con.close()

        logica_login.generar_presupuesto("ana", 1000000)

        con = sqlite3.connect(BD_PRUEBA)
        restantes = con.execute("SELECT usuario_id FROM gastos").fetchall()
        con.close()
        self.assertEqual(restantes, [(ids["beto"],)])

    def test_ingreso_invalido_no_borra_el_presupuesto(self):
        """si el ingreso no sirve, devuelve false y conserva lo que había."""
        self._crear_dos_usuarios()
        logica_login.generar_presupuesto("ana", 1000000)
        for invalido in ("", "abc", "0", "-5", "nan", "inf", None):
            self.assertFalse(logica_login.generar_presupuesto("ana", invalido))
        self.assertEqual(logica_login.obtener_categorias("ana")[0][1], 500000.0)

    def test_presupuesto_de_usuario_inexistente(self):
        """con un usuario que no existe no se crea ni se devuelve nada."""
        self.assertFalse(logica_login.generar_presupuesto("fantasma", 1000000))
        self.assertEqual(logica_login.obtener_categorias("fantasma"), [])
        self.assertIsNone(logica_login.obtener_ingreso("fantasma"))

    def test_convertir_monto(self):
        """acepta montos con separadores de miles y rechaza lo que no sirve."""
        self.assertEqual(logica_login.convertir_monto("1500000"), 1500000.0)
        self.assertEqual(logica_login.convertir_monto("1.500.000"), 1500000.0)
        self.assertEqual(logica_login.convertir_monto("1,500,000"), 1500000.0)
        self.assertEqual(logica_login.convertir_monto(" 2500.50 "), 2500.5)
        self.assertEqual(logica_login.convertir_monto(750000), 750000.0)
        for invalido in ("", "abc", "0", "-5", "nan", "inf", "1.2.3", None):
            self.assertIsNone(logica_login.convertir_monto(invalido))

    def test_formatear_gs(self):
        """los guaraníes se muestran con punto de miles."""
        self.assertEqual(logica_login.formatear_gs(1500000), "Gs. 1.500.000")
        self.assertEqual(logica_login.formatear_gs(0), "Gs. 0")
        self.assertEqual(logica_login.formatear_gs(250000.4), "Gs. 250.000")
        self.assertEqual(logica_login.formatear_gs(None), "Gs. 0")

    #categorías editables

    def _presupuesto_ana(self, ingreso=1000000, metodo="Básico"):
        """ana con presupuesto Básico: Comidas 50%, Ahorro 30%, Ocio 20%."""
        self._crear("ana")
        logica_login.generar_presupuesto("ana", ingreso, metodo)

    def test_agregar_categoria(self):
        """se puede agregar una categoría nueva dentro de lo que queda sin asignar."""
        self._presupuesto_ana()
        # se libera lugar bajando Ocio, para poder sumar streaming y movilidad
        self.assertEqual(logica_login.editar_categoria("ana", "Ocio", None, 100000), (True, ""))
        self.assertEqual(logica_login.agregar_categoria("ana", " Streaming ", "60.000"), (True, ""))
        self.assertEqual(logica_login.agregar_categoria("ana", "Movilidad", 40000), (True, ""))
        nombres = [c[0] for c in logica_login.obtener_categorias("ana")]
        self.assertEqual(nombres, ["Comidas", "Ahorro", "Ocio", "Streaming", "Movilidad"])

    def test_agregar_categoria_invalida(self):
        """se rechaza nombre vacío o repetido, monto malo y exceso sobre el ingreso."""
        self._presupuesto_ana()
        self.assertFalse(logica_login.agregar_categoria("ana", "", 1000)[0])
        self.assertFalse(logica_login.agregar_categoria("ana", "x" * 41, 1000)[0])
        self.assertFalse(logica_login.agregar_categoria("ana", "comidas", 1000)[0])   # repetida
        self.assertFalse(logica_login.agregar_categoria("ana", "Nueva", "abc")[0])
        self.assertFalse(logica_login.agregar_categoria("ana", "Nueva", 0)[0])
        # el ingreso ya está 100% asignado, no queda nada para una nueva
        ok, motivo = logica_login.agregar_categoria("ana", "Nueva", 1000)
        self.assertFalse(ok)
        self.assertIn("sin asignar", motivo)
        self.assertFalse(logica_login.agregar_categoria("fantasma", "Nueva", 1000)[0])
        self.assertEqual(len(logica_login.obtener_categorias("ana")), 3)

    def test_agregar_categoria_sin_presupuesto(self):
        """sin ingreso cargado no se pueden crear categorías sueltas."""
        self._crear("ana")
        ok, motivo = logica_login.agregar_categoria("ana", "Comidas", 1000)
        self.assertFalse(ok)
        self.assertIn("presupuesto", motivo)

    def test_editar_categoria_nombre_y_monto(self):
        """editar cambia nombre y monto, y los gastos pasan al nombre nuevo."""
        self._presupuesto_ana()
        logica_login.registrar_gasto("ana", "Ocio", "cine", 50000)
        self.assertEqual(
            logica_login.editar_categoria("ana", "ocio", "Salidas", 150000), (True, ""))
        categorias = {c[0]: c for c in logica_login.obtener_categorias("ana")}
        self.assertNotIn("Ocio", categorias)
        self.assertEqual(categorias["Salidas"][1:], (150000.0, 50000.0))
        self.assertEqual(logica_login.consultar_historial_reciente("ana")[0][1], "Salidas")
        # y se puede seguir cargando gastos con el nombre nuevo
        self.assertTrue(logica_login.registrar_gasto("ana", "Salidas", "bar", 10000)["ok"])

    def test_editar_categoria_invalida(self):
        """no deja repetir nombres, pasarse del ingreso ni editar lo que no existe."""
        self._presupuesto_ana()
        self.assertFalse(logica_login.editar_categoria("ana", "Ocio", "Comidas")[0])
        self.assertFalse(logica_login.editar_categoria("ana", "Ocio", None, 300000)[0])  # se pasa
        self.assertFalse(logica_login.editar_categoria("ana", "Ocio", "")[0])
        self.assertFalse(logica_login.editar_categoria("ana", "Ocio", None, "abc")[0])
        self.assertFalse(logica_login.editar_categoria("ana", "Inexistente", "X")[0])
        self.assertFalse(logica_login.editar_categoria("fantasma", "Ocio", "X")[0])
        # conserva lo que había
        self.assertEqual(logica_login.obtener_categorias("ana")[2], ("Ocio", 200000.0, 0.0))
        # renombrar solo cambiando mayúsculas sí se puede
        self.assertTrue(logica_login.editar_categoria("ana", "Ocio", "OCIO")[0])

    def test_eliminar_categoria(self):
        """eliminar una categoría borra también sus gastos y libera su monto."""
        self._presupuesto_ana()
        logica_login.registrar_gasto("ana", "Ocio", "cine", 50000)
        logica_login.registrar_gasto("ana", "Comidas", "super", 80000)
        self.assertEqual(logica_login.eliminar_categoria("ana", "Ocio"), (True, ""))
        self.assertEqual([c[0] for c in logica_login.obtener_categorias("ana")],
                         ["Comidas", "Ahorro"])
        historial = logica_login.consultar_historial_reciente("ana")
        self.assertEqual([h[1] for h in historial], ["Comidas"])
        self.assertEqual(logica_login.agregar_categoria("ana", "Streaming", 200000), (True, ""))
        self.assertFalse(logica_login.eliminar_categoria("ana", "Ocio")[0])

    def test_cambiar_ingreso(self):
        """el ingreso se puede subir, pero no bajar de lo ya asignado."""
        self._presupuesto_ana()
        self.assertFalse(logica_login.cambiar_ingreso("ana", 900000)[0])
        self.assertFalse(logica_login.cambiar_ingreso("ana", "abc")[0])
        self.assertFalse(logica_login.cambiar_ingreso("fantasma", 1000)[0])
        self.assertEqual(logica_login.cambiar_ingreso("ana", "1.200.000"), (True, ""))
        self.assertEqual(logica_login.obtener_ingreso("ana"), 1200000.0)
        # ahora quedan 200.000 sin asignar
        self.assertEqual(logica_login.agregar_categoria("ana", "Streaming", 200000), (True, ""))
        self.assertEqual(logica_login.consultar_resumen_categorias("ana")["sin_asignar"], 0.0)

    def test_categorias_son_individuales(self):
        """las categorías de un usuario no afectan a otro."""
        self._presupuesto_ana()
        self._crear("beto")
        logica_login.generar_presupuesto("beto", 500000, "Básico")
        logica_login.editar_categoria("ana", "Ocio", "Salidas")
        logica_login.eliminar_categoria("ana", "Ahorro")
        self.assertEqual([c[0] for c in logica_login.obtener_categorias("beto")],
                         ["Comidas", "Ahorro", "Ocio"])

    #módulo 4: registro de gastos

    def test_cu_08_01_consultar_categorias_activas(self):
        """CU.08.01: devuelve nombre, presupuesto, gastado y disponible."""
        self._presupuesto_ana()
        logica_login.registrar_gasto("ana", "Comidas", "super", 100000)
        activas = logica_login.consultar_categorias_activas("ana")
        self.assertEqual(activas[0], ("Comidas", 500000.0, 100000.0, 400000.0))
        self.assertEqual(len(activas), 3)
        self.assertEqual(logica_login.consultar_categorias_activas("fantasma"), [])

    def test_cu_08_02_validar_detalle_de_gasto(self):
        """CU.08.02: concepto obligatorio y monto mayor a 0."""
        self.assertEqual(logica_login.validar_detalle_gasto("McDonalds", "80.000"),
                         (True, "", 80000.0))
        for concepto, monto in (("", 1000), ("   ", 1000), ("x" * 101, 1000),
                                ("cine", "abc"), ("cine", 0), ("cine", -5), ("cine", None)):
            ok, motivo, valor = logica_login.validar_detalle_gasto(concepto, monto)
            self.assertFalse(ok)
            self.assertTrue(motivo)
            self.assertIsNone(valor)

    def test_ejemplo_del_enunciado(self):
        """viáticos 500.000: gasta 250.000 (quedan 250.000), luego 80.000 en mcdonalds."""
        self._crear("ana")
        logica_login.generar_presupuesto(
            "ana", 1000000, logica_login.METODO_PERSONALIZADO,
            [("Viáticos", 50), ("Ahorro", 50)])
        self.assertEqual(logica_login.consultar_categorias_activas("ana")[0],
                         ("Viáticos", 500000.0, 0.0, 500000.0))

        primero = logica_login.registrar_gasto("ana", "Viáticos", "pasajes", "250.000")
        self.assertTrue(primero["ok"])
        self.assertEqual((primero["gastado"], primero["disponible"]), (250000.0, 250000.0))
        self.assertEqual(primero["alerta"], "")

        segundo = logica_login.registrar_gasto("ana", "Viáticos", "McDonalds", 80000)
        self.assertTrue(segundo["ok"])
        self.assertEqual(segundo["categoria"], "Viáticos")
        self.assertEqual(segundo["presupuesto"], 500000.0)
        self.assertEqual((segundo["gastado"], segundo["disponible"]), (330000.0, 170000.0))
        self.assertEqual(segundo["alerta"], "")
        self.assertEqual(logica_login.obtener_categorias("ana")[0], ("Viáticos", 500000.0, 330000.0))

    def test_cu_08_03_saldo_acumulado_y_historial(self):
        """CU.08.03: cada gasto suma al acumulado y queda en el historial con fecha."""
        self._presupuesto_ana()
        logica_login.registrar_gasto("ana", "Comidas", "  almuerzo  ", 30000, fecha="01/11/2026")
        logica_login.registrar_gasto("ana", "comidas", "cena", 20000, fecha="02/11/2026")
        self.assertEqual(logica_login.obtener_categorias("ana")[0][2], 50000.0)
        self.assertEqual(
            logica_login.consultar_historial_reciente("ana"),
            [("02/11/2026", "Comidas", "cena", 20000.0),
             ("01/11/2026", "Comidas", "almuerzo", 30000.0)])

    def test_gasto_usa_fecha_de_hoy_por_defecto(self):
        """sin fecha indicada se guarda la de hoy en formato dd/mm/aaaa."""
        self._presupuesto_ana()
        logica_login.registrar_gasto("ana", "Comidas", "cafe", 5000)
        fecha = logica_login.consultar_historial_reciente("ana")[0][0]
        self.assertRegex(fecha, r"^\d{2}/\d{2}/\d{4}$")

    def test_cu_08_04_alerta_de_limite_superado(self):
        """CU.08.04: superar el presupuesto avisa, pero el gasto igual se registra."""
        self._presupuesto_ana()
        r1 = logica_login.registrar_gasto("ana", "Ocio", "recital", 200000)   # justo el límite
        self.assertEqual(r1["alerta"], "")
        r2 = logica_login.registrar_gasto("ana", "Ocio", "cena", 30000)
        self.assertTrue(r2["ok"])
        self.assertEqual(r2["disponible"], -30000.0)
        self.assertIn("Ocio", r2["alerta"])
        self.assertIn("Gs. 30.000", r2["alerta"])
        self.assertEqual(logica_login.obtener_categorias("ana")[2][2], 230000.0)

    def test_evaluar_alerta_limite(self):
        """la alerta solo aparece cuando lo gastado pasa del presupuesto."""
        self.assertEqual(logica_login.evaluar_alerta_limite("Ocio", 100, 100), "")
        self.assertEqual(logica_login.evaluar_alerta_limite("Ocio", 100, 50), "")
        self.assertIn("Gs. 20", logica_login.evaluar_alerta_limite("Ocio", 100, 120))

    def test_gasto_invalido_no_se_registra(self):
        """datos malos, categoría o usuario inexistente: no cambia nada."""
        self._presupuesto_ana()
        casos = [
            ("ana", "Comidas", "", 1000, "concepto"),
            ("ana", "Comidas", "cafe", "abc", "monto"),
            ("ana", "Comidas", "cafe", -5, "monto"),
            ("ana", "Inexistente", "cafe", 1000, "categoría"),
            ("fantasma", "Comidas", "cafe", 1000, "usuario"),
        ]
        for usuario, categoria, concepto, monto, _ in casos:
            resultado = logica_login.registrar_gasto(usuario, categoria, concepto, monto)
            self.assertFalse(resultado["ok"])
            self.assertTrue(resultado["motivo"])
        self.assertEqual(logica_login.obtener_categorias("ana")[0][2], 0.0)
        self.assertEqual(logica_login.consultar_historial_reciente("ana"), [])

    def test_gastos_son_individuales(self):
        """un usuario no puede cargar gastos en categorías de otro ni verlos."""
        self._presupuesto_ana()
        self._crear("beto")
        self.assertFalse(logica_login.registrar_gasto("beto", "Comidas", "cafe", 1000)["ok"])
        logica_login.generar_presupuesto("beto", 100000, "Básico")
        logica_login.registrar_gasto("ana", "Comidas", "super", 40000)
        logica_login.registrar_gasto("beto", "Comidas", "cafe", 1000)
        self.assertEqual(len(logica_login.consultar_historial_reciente("ana")), 1)
        self.assertEqual(logica_login.consultar_historial_reciente("beto")[0][2], "cafe")
        self.assertEqual(logica_login.obtener_categorias("beto")[0][2], 1000.0)

    #módulo 5: dashboard y reportes

    def test_cu_09_01_resumen_de_categorias(self):
        """CU.09.01: totales, sin asignar y estado de cada categoría."""
        self._presupuesto_ana()
        logica_login.registrar_gasto("ana", "Comidas", "super", 100000)    # 20% -> ok
        logica_login.registrar_gasto("ana", "Ahorro", "cuota", 270000)     # 90% -> precaución
        logica_login.registrar_gasto("ana", "Ocio", "viaje", 250000)       # 125% -> excedido
        resumen = logica_login.consultar_resumen_categorias("ana")

        self.assertEqual(resumen["ingreso"], 1000000.0)
        self.assertEqual(resumen["total_presupuestado"], 1000000.0)
        self.assertEqual(resumen["total_gastado"], 620000.0)
        self.assertEqual(resumen["total_disponible"], 380000.0)
        self.assertEqual(resumen["sin_asignar"], 0.0)
        self.assertAlmostEqual(resumen["porcentaje_usado"], 0.62)
        estados = {c["nombre"]: c["estado"] for c in resumen["categorias"]}
        self.assertEqual(estados, {"Comidas": "ok", "Ahorro": "precaucion", "Ocio": "excedido"})
        ocio = resumen["categorias"][2]
        self.assertEqual((ocio["presupuesto"], ocio["gastado"], ocio["disponible"]),
                         (200000.0, 250000.0, -50000.0))
        self.assertAlmostEqual(ocio["porcentaje"], 1.25)

    def test_resumen_sin_presupuesto(self):
        """sin presupuesto el resumen viene vacío, sin errores."""
        self._crear("ana")
        resumen = logica_login.consultar_resumen_categorias("ana")
        self.assertEqual(resumen["categorias"], [])
        self.assertEqual(resumen["total_presupuestado"], 0.0)
        self.assertEqual(resumen["porcentaje_usado"], 0.0)
        self.assertEqual(resumen["ingreso"], 0.0)
        vacio = logica_login.consultar_resumen_categorias("fantasma")
        self.assertEqual(vacio["categorias"], [])

    def test_resumen_muestra_lo_que_queda_sin_asignar(self):
        """si se sube el ingreso, la diferencia aparece como sin asignar."""
        self._presupuesto_ana()
        logica_login.cambiar_ingreso("ana", 1300000)
        resumen = logica_login.consultar_resumen_categorias("ana")
        self.assertEqual(resumen["sin_asignar"], 300000.0)

    def test_cu_09_02_historial_reciente(self):
        """CU.09.02: del más nuevo al más viejo, con límite configurable."""
        self._presupuesto_ana()
        for numero in range(1, 13):
            logica_login.registrar_gasto("ana", "Comidas", f"gasto {numero}", 1000,
                                         fecha=f"{numero:02d}/11/2026")
        historial = logica_login.consultar_historial_reciente("ana")
        self.assertEqual(len(historial), 10)                  # por defecto, 10
        self.assertEqual(historial[0][2], "gasto 12")
        self.assertEqual(historial[-1][2], "gasto 3")
        self.assertEqual(len(logica_login.consultar_historial_reciente("ana", 3)), 3)
        self.assertEqual(len(logica_login.consultar_historial_reciente("ana", 50)), 12)
        # límites raros: se usa el valor por defecto o el máximo
        self.assertEqual(len(logica_login.consultar_historial_reciente("ana", 0)), 10)
        self.assertEqual(len(logica_login.consultar_historial_reciente("ana", "abc")), 10)
        self.assertEqual(logica_login.consultar_historial_reciente("fantasma"), [])

    #ahorros: metas y aportes

    HOY = datetime.date(2026, 11, 12)   # fecha fija para que las pruebas no dependan del día

    def _meta_ana(self, nombre="Viaje", objetivo=1000000, fecha=None):
        """ana con una meta de ahorro."""
        self._crear("ana")
        return logica_login.crear_meta("ana", nombre, objetivo, fecha, hoy=self.HOY)

    def test_crear_meta(self):
        """una meta nueva empieza en 0, con su objetivo y sin fecha."""
        self.assertEqual(self._meta_ana("  Viaje   a  Brasil ", "1.000.000"), (True, ""))
        meta = logica_login.obtener_metas("ana", self.HOY)[0]
        self.assertEqual(meta["nombre"], "Viaje a Brasil")
        self.assertEqual((meta["objetivo"], meta["ahorrado"], meta["faltante"]),
                         (1000000.0, 0.0, 1000000.0))
        self.assertEqual(meta["porcentaje"], 0.0)
        self.assertFalse(meta["completada"])
        self.assertIsNone(meta["fecha_limite"])
        self.assertIsNone(meta["dias_restantes"])
        self.assertEqual(meta["estado"], "en_curso")

    def test_crear_meta_invalida(self):
        """se rechazan nombres vacíos o repetidos, objetivos malos y fechas inválidas."""
        self._meta_ana()
        hoy = self.HOY
        self.assertFalse(logica_login.crear_meta("ana", "", 1000, hoy=hoy)[0])
        self.assertFalse(logica_login.crear_meta("ana", "x" * 41, 1000, hoy=hoy)[0])
        self.assertFalse(logica_login.crear_meta("ana", "viaje", 1000, hoy=hoy)[0])    # repetida
        for objetivo in ("abc", 0, -5, None):
            self.assertFalse(logica_login.crear_meta("ana", "Otra", objetivo, hoy=hoy)[0])
        self.assertFalse(logica_login.crear_meta("ana", "Otra", 1000, "mañana", hoy=hoy)[0])
        self.assertFalse(logica_login.crear_meta("ana", "Otra", 1000, "31/02/2027", hoy=hoy)[0])
        ok, motivo = logica_login.crear_meta("ana", "Otra", 1000, "01/01/2020", hoy=hoy)
        self.assertFalse(ok)
        self.assertIn("pasado", motivo)
        self.assertFalse(logica_login.crear_meta("fantasma", "Otra", 1000, hoy=hoy)[0])
        self.assertEqual(len(logica_login.obtener_metas("ana", hoy)), 1)

    def test_meta_con_fecha_limite(self):
        """la fecha se normaliza y se calculan los días que faltan."""
        self._crear("ana")
        self.assertTrue(logica_login.crear_meta("ana", "Auto", 5000000, "5/12/2026", hoy=self.HOY)[0])
        self.assertTrue(logica_login.crear_meta("ana", "Hoy", 1000, "12/11/2026", hoy=self.HOY)[0])
        auto, hoy_meta = logica_login.obtener_metas("ana", self.HOY)
        self.assertEqual(auto["fecha_limite"], "05/12/2026")
        self.assertEqual(auto["dias_restantes"], 23)
        self.assertEqual(hoy_meta["dias_restantes"], 0)
        # pasado el tiempo sin completarla, queda vencida
        vencida = logica_login.obtener_metas("ana", datetime.date(2027, 1, 1))[0]
        self.assertEqual((vencida["estado"], vencida["dias_restantes"]), ("vencida", -27))

    def test_agregar_aporte_actualiza_totales(self):
        """cada aporte suma a lo ahorrado y recalcula faltante y porcentaje."""
        self._meta_ana("Viaje", 1000000)
        r1 = logica_login.agregar_aporte("ana", "Viaje", "250.000", "primer ahorro", hoy=self.HOY)
        self.assertTrue(r1["ok"])
        self.assertEqual((r1["ahorrado"], r1["faltante"], r1["porcentaje"]), (250000.0, 750000.0, 0.25))
        self.assertFalse(r1["completada"])
        self.assertFalse(r1["recien_completada"])
        r2 = logica_login.agregar_aporte("ana", "viaje", 150000, hoy=self.HOY)
        self.assertEqual((r2["ahorrado"], r2["faltante"], r2["porcentaje"]), (400000.0, 600000.0, 0.4))
        self.assertEqual(r2["nombre"], "Viaje")
        self.assertEqual(logica_login.obtener_metas("ana", self.HOY)[0]["ahorrado"], 400000.0)

    def test_meta_completada(self):
        """al llegar al objetivo la meta se completa; se puede pasar de 100%."""
        self._meta_ana("Celular", 800000)
        logica_login.agregar_aporte("ana", "Celular", 500000)
        final = logica_login.agregar_aporte("ana", "Celular", 300000)
        self.assertTrue(final["completada"])
        self.assertTrue(final["recien_completada"])
        self.assertEqual((final["faltante"], final["porcentaje"], final["estado"]),
                         (0.0, 1.0, "completada"))
        extra = logica_login.agregar_aporte("ana", "Celular", 100000)
        self.assertTrue(extra["ok"])
        self.assertFalse(extra["recien_completada"])           # ya estaba completa
        self.assertEqual((extra["faltante"], extra["porcentaje"]), (0.0, 1.125))

    def test_aporte_invalido(self):
        """monto malo, nota larga, meta o usuario inexistentes: no cambia nada."""
        self._meta_ana("Viaje", 1000000)
        for monto in ("abc", 0, -5, None, ""):
            resultado = logica_login.agregar_aporte("ana", "Viaje", monto)
            self.assertFalse(resultado["ok"])
            self.assertTrue(resultado["motivo"])
        self.assertFalse(logica_login.agregar_aporte("ana", "Viaje", 1000, "x" * 101)["ok"])
        self.assertFalse(logica_login.agregar_aporte("ana", "Inexistente", 1000)["ok"])
        self.assertFalse(logica_login.agregar_aporte("fantasma", "Viaje", 1000)["ok"])
        self.assertEqual(logica_login.obtener_metas("ana", self.HOY)[0]["ahorrado"], 0.0)
        self.assertEqual(logica_login.consultar_aportes_recientes("ana"), [])

    def test_editar_meta(self):
        """editar cambia nombre, objetivo y fecha, y conserva lo ahorrado y los aportes."""
        self._meta_ana("Viaje", 1000000, "31/12/2026")
        logica_login.agregar_aporte("ana", "Viaje", 200000, "inicio", fecha="01/11/2026")
        self.assertEqual(
            logica_login.editar_meta("ana", "viaje", "Viaje a Brasil", "1.500.000", "15/01/2027",
                                     hoy=self.HOY), (True, ""))
        meta = logica_login.obtener_metas("ana", self.HOY)[0]
        self.assertEqual((meta["nombre"], meta["objetivo"], meta["ahorrado"], meta["fecha_limite"]),
                         ("Viaje a Brasil", 1500000.0, 200000.0, "15/01/2027"))
        self.assertAlmostEqual(meta["porcentaje"], 200000 / 1500000)
        # los aportes siguen asociados con el nombre nuevo
        self.assertEqual(logica_login.consultar_aportes_recientes("ana"),
                         [("01/11/2026", "Viaje a Brasil", 200000.0, "inicio")])
        # none deja todo igual; texto vacío quita la fecha
        self.assertTrue(logica_login.editar_meta("ana", "Viaje a Brasil", hoy=self.HOY)[0])
        self.assertEqual(logica_login.obtener_metas("ana", self.HOY)[0]["fecha_limite"], "15/01/2027")
        self.assertTrue(logica_login.editar_meta("ana", "Viaje a Brasil", fecha_limite="", hoy=self.HOY)[0])
        self.assertIsNone(logica_login.obtener_metas("ana", self.HOY)[0]["fecha_limite"])

    def test_editar_meta_invalida(self):
        """no deja repetir nombres, usar datos malos ni editar lo que no existe."""
        self._meta_ana("Viaje", 1000000)
        logica_login.crear_meta("ana", "Auto", 5000000, hoy=self.HOY)
        hoy = self.HOY
        self.assertFalse(logica_login.editar_meta("ana", "Auto", "viaje", hoy=hoy)[0])
        self.assertFalse(logica_login.editar_meta("ana", "Auto", "", hoy=hoy)[0])
        self.assertFalse(logica_login.editar_meta("ana", "Auto", None, "abc", hoy=hoy)[0])
        self.assertFalse(logica_login.editar_meta("ana", "Auto", None, 0, hoy=hoy)[0])
        self.assertFalse(logica_login.editar_meta("ana", "Auto", None, None, "ayer", hoy=hoy)[0])
        self.assertFalse(logica_login.editar_meta("ana", "Auto", None, None, "01/01/2020", hoy=hoy)[0])
        self.assertFalse(logica_login.editar_meta("ana", "Inexistente", "X", hoy=hoy)[0])
        self.assertFalse(logica_login.editar_meta("fantasma", "Auto", "X", hoy=hoy)[0])
        self.assertEqual(logica_login.obtener_metas("ana", hoy)[1]["objetivo"], 5000000.0)
        # cambiar solo mayúsculas del propio nombre sí se puede
        self.assertTrue(logica_login.editar_meta("ana", "Auto", "AUTO", hoy=hoy)[0])

    def test_editar_meta_vencida_conserva_su_fecha(self):
        """si la fecha ya venció, se puede seguir editando lo demás sin cambiarla."""
        self._meta_ana("Viaje", 1000000, "20/11/2026")
        despues = datetime.date(2027, 3, 1)
        self.assertTrue(logica_login.editar_meta("ana", "Viaje", "Viaje 2", None, "20/11/2026", hoy=despues)[0])
        self.assertEqual(logica_login.obtener_metas("ana", despues)[0]["fecha_limite"], "20/11/2026")
        # pero no se puede poner otra fecha pasada
        self.assertFalse(logica_login.editar_meta("ana", "Viaje 2", None, None, "21/11/2026", hoy=despues)[0])

    def test_bajar_objetivo_bajo_lo_ahorrado_completa_la_meta(self):
        """si el objetivo baja a lo ya ahorrado, la meta queda completada."""
        self._meta_ana("Viaje", 1000000)
        logica_login.agregar_aporte("ana", "Viaje", 300000)
        logica_login.editar_meta("ana", "Viaje", None, 250000)
        meta = logica_login.obtener_metas("ana", self.HOY)[0]
        self.assertTrue(meta["completada"])
        self.assertEqual(meta["faltante"], 0.0)

    def test_eliminar_meta_borra_sus_aportes(self):
        """eliminar una meta borra también sus aportes, no los de otras."""
        self._meta_ana("Viaje", 1000000)
        logica_login.crear_meta("ana", "Auto", 5000000)
        logica_login.agregar_aporte("ana", "Viaje", 100000)
        logica_login.agregar_aporte("ana", "Auto", 200000)
        self.assertEqual(logica_login.eliminar_meta("ana", "viaje"), (True, ""))
        self.assertEqual([m["nombre"] for m in logica_login.obtener_metas("ana")], ["Auto"])
        aportes = logica_login.consultar_aportes_recientes("ana")
        self.assertEqual([(a[1], a[2]) for a in aportes], [("Auto", 200000.0)])
        self.assertFalse(logica_login.eliminar_meta("ana", "Viaje")[0])
        self.assertFalse(logica_login.eliminar_meta("fantasma", "Auto")[0])
        # el nombre queda libre para crear otra meta
        self.assertTrue(logica_login.crear_meta("ana", "Viaje", 1000)[0])

    def test_resumen_de_ahorros(self):
        """totales, metas completadas y porcentaje general."""
        self._crear("ana")
        logica_login.crear_meta("ana", "Viaje", 1000000)
        logica_login.crear_meta("ana", "Celular", 500000)
        logica_login.crear_meta("ana", "Auto", 4500000)
        logica_login.agregar_aporte("ana", "Viaje", 250000)
        logica_login.agregar_aporte("ana", "Celular", 600000)       # se pasa por 100.000
        resumen = logica_login.consultar_resumen_ahorros("ana", self.HOY)
        self.assertEqual((resumen["cantidad"], resumen["completadas"]), (3, 1))
        self.assertEqual(resumen["total_objetivo"], 6000000.0)
        self.assertEqual(resumen["total_ahorrado"], 850000.0)
        self.assertEqual(resumen["total_faltante"], 750000.0 + 0.0 + 4500000.0)
        # el excedente de Celular no cuenta: (250.000 + 500.000) / 6.000.000
        self.assertAlmostEqual(resumen["porcentaje_total"], 750000 / 6000000)
        self.assertEqual([m["nombre"] for m in resumen["metas"]], ["Viaje", "Celular", "Auto"])

    def test_resumen_de_ahorros_vacio(self):
        """sin metas el resumen viene en cero, sin errores."""
        self._crear("ana")
        for usuario in ("ana", "fantasma"):
            resumen = logica_login.consultar_resumen_ahorros(usuario)
            self.assertEqual((resumen["cantidad"], resumen["completadas"]), (0, 0))
            self.assertEqual((resumen["total_objetivo"], resumen["porcentaje_total"]), (0, 0.0))
            self.assertEqual(resumen["metas"], [])

    def test_aportes_recientes(self):
        """del más nuevo al más viejo, con meta, monto y nota, y límite configurable."""
        self._meta_ana("Viaje", 100000000)
        for numero in range(1, 13):
            logica_login.agregar_aporte("ana", "Viaje", 1000 * numero, f"aporte {numero}",
                                        fecha=f"{numero:02d}/11/2026")
        aportes = logica_login.consultar_aportes_recientes("ana")
        self.assertEqual(len(aportes), 10)
        self.assertEqual(aportes[0], ("12/11/2026", "Viaje", 12000.0, "aporte 12"))
        self.assertEqual(aportes[-1][3], "aporte 3")
        self.assertEqual(len(logica_login.consultar_aportes_recientes("ana", 3)), 3)
        self.assertEqual(len(logica_login.consultar_aportes_recientes("ana", 50)), 12)
        self.assertEqual(len(logica_login.consultar_aportes_recientes("ana", 0)), 10)
        self.assertEqual(logica_login.consultar_aportes_recientes("fantasma"), [])

    def test_aporte_usa_fecha_de_hoy_por_defecto(self):
        """sin fecha indicada se guarda la de hoy en formato dd/mm/aaaa."""
        self._meta_ana()
        logica_login.agregar_aporte("ana", "Viaje", 1000)
        self.assertRegex(logica_login.consultar_aportes_recientes("ana")[0][0], r"^\d{2}/\d{2}/\d{4}$")

    def test_ahorros_son_individuales(self):
        """las metas y aportes de un usuario no los ven ni los tocan otros."""
        self._meta_ana("Viaje", 1000000)
        self._crear("beto")
        self.assertEqual(logica_login.obtener_metas("beto"), [])
        self.assertFalse(logica_login.agregar_aporte("beto", "Viaje", 1000)["ok"])
        self.assertFalse(logica_login.editar_meta("beto", "Viaje", "X")[0])
        self.assertFalse(logica_login.eliminar_meta("beto", "Viaje")[0])
        # y cada uno puede tener una meta con el mismo nombre
        self.assertTrue(logica_login.crear_meta("beto", "Viaje", 500000)[0])
        logica_login.agregar_aporte("beto", "Viaje", 1000)
        self.assertEqual(logica_login.obtener_metas("ana")[0]["ahorrado"], 0.0)
        self.assertEqual(logica_login.consultar_aportes_recientes("ana"), [])

    def test_ahorros_son_independientes_del_presupuesto(self):
        """regenerar el presupuesto no toca las metas de ahorro."""
        self._meta_ana("Viaje", 1000000)
        logica_login.agregar_aporte("ana", "Viaje", 100000)
        logica_login.generar_presupuesto("ana", 2000000)
        self.assertEqual(logica_login.obtener_metas("ana")[0]["ahorrado"], 100000.0)

    def test_admin_elimina_usuario_con_sus_ahorros(self):
        """al eliminar un usuario también se borran sus metas y aportes."""
        self._crear("jefe", "admin")
        self._crear("ana")
        self._crear("beto")
        logica_login.crear_meta("ana", "Viaje", 1000000)
        logica_login.agregar_aporte("ana", "Viaje", 1000)
        logica_login.crear_meta("beto", "Auto", 5000000)
        logica_login.agregar_aporte("beto", "Auto", 2000)
        self.assertTrue(logica_login.eliminar_usuario("jefe", "ana")[0])
        con = sqlite3.connect(BD_PRUEBA)
        metas = con.execute("SELECT usuario_id FROM metas").fetchall()
        aportes = con.execute("SELECT usuario_id FROM aportes").fetchall()
        con.close()
        self.assertEqual(len(metas), 1)
        self.assertEqual(len(aportes), 1)
        self.assertEqual(logica_login.obtener_metas("beto")[0]["ahorrado"], 2000.0)

    #carpeta de la base (programa normal y .exe de pyinstaller)

    def test_carpeta_base_normal_y_empaquetada(self):
        """normal: junto al código. con pyinstaller: junto al .exe, no en la carpeta temporal."""
        aqui = os.path.dirname(os.path.abspath(logica_login.__file__))
        self.assertEqual(logica_login.carpeta_base(), aqui)

        carpeta_exe = os.path.abspath(os.path.join(tempfile.gettempdir(), "carpeta_del_exe"))
        sys.frozen = True
        sys.executable, ejecutable = os.path.join(carpeta_exe, "SogueApp.exe"), sys.executable
        try:
            self.assertEqual(logica_login.carpeta_base(), carpeta_exe)
        finally:
            sys.executable = ejecutable
            del sys.frozen
        self.assertEqual(logica_login.carpeta_base(), aqui)

    #documentación

    def test_generar_documentacion(self):
        """pydoc crea el html del módulo en la carpeta indicada."""
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = logica_login.generar_documentacion(carpeta)
            self.assertTrue(os.path.exists(ruta))
            with open(ruta, encoding="utf-8") as archivo:
                contenido = archivo.read()
        for nombre in ("crear_usuario", "generar_presupuesto", "agregar_categoria",
                       "registrar_gasto", "consultar_resumen_categorias",
                       "consultar_historial_reciente", "eliminar_usuario",
                       "crear_meta", "agregar_aporte", "consultar_resumen_ahorros"):
            self.assertIn(nombre, contenido)

    #bases creadas por la versión 1.5.2

    def test_migra_base_de_la_version_1_5_2(self):
        """una base vieja (sin rol ni orden) sigue funcionando y se actualiza."""
        logica_login.nombre_bd = BD_PRUEBA
        os.remove(BD_PRUEBA)
        con = sqlite3.connect(BD_PRUEBA)
        con.execute("""CREATE TABLE usuarios(id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE, clave TEXT, pregunta1 TEXT, respuesta1 TEXT,
            pregunta2 TEXT, respuesta2 TEXT, pregunta3 TEXT, respuesta3 TEXT)""")
        con.execute("CREATE TABLE categorias(id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    "nombre TEXT, presupuesto REAL, gastado REAL DEFAULT 0)")
        viejo = lambda t: hashlib.sha256(t.strip().lower().encode()).hexdigest()
        con.execute("INSERT INTO usuarios(usuario, clave, pregunta1, respuesta1) VALUES(?,?,?,?)",
                    ("veterano", viejo("Clave123"), self.pregunta, viejo("milanesa")))
        con.execute("INSERT INTO categorias(nombre, presupuesto) VALUES('Ahorro', 100)")
        con.commit()
        con.close()

        logica_login.inicializar_db()

        # el usuario viejo entra, conserva su pregunta y queda como 'completo'
        self.assertTrue(logica_login.verificar_usuario("veterano", "Clave123"))
        self.assertEqual(logica_login.obtener_rol_usuario("veterano"), "completo")
        self.assertEqual(logica_login.obtener_pregunta_secreta("veterano"), self.pregunta)
        self.assertTrue(logica_login.verificar_respuesta_secreta("veterano", "Milanesa"))

        # al entrar, su clave pasó al formato nuevo
        con = sqlite3.connect(BD_PRUEBA)
        clave = con.execute("SELECT clave FROM usuarios WHERE usuario='veterano'").fetchone()[0]
        categorias = con.execute("SELECT nombre, presupuesto, orden FROM categorias").fetchall()
        con.close()
        self.assertTrue(clave.startswith("pbkdf2_sha256$"))
        self.assertEqual(categorias, [("Ahorro", 100.0, 0)])

        # el presupuesto compartido de la 1.5.2 pasó al usuario más antiguo
        self.assertEqual(logica_login.obtener_categorias("veterano"), [("Ahorro", 100.0, 0.0)])

        # no se crea ningún admin y el ingreso se calcula con lo ya asignado
        self.assertFalse(logica_login.existe_admin())
        self.assertEqual(logica_login.obtener_ingreso("veterano"), 100.0)

        # y con la base migrada ya se pueden registrar gastos
        self.assertTrue(logica_login.registrar_gasto("veterano", "Ahorro", "cuota", 40)["ok"])
        self.assertEqual(logica_login.obtener_categorias("veterano"), [("Ahorro", 100.0, 40.0)])


class VentanaFalsa:
    """imita una ventana de customtkinter: anota las llamadas a iconbitmap y after."""

    def __init__(self, falla=False):
        self.iconos = []
        self.pendientes = []
        self.falla = falla

    def iconbitmap(self, ruta):
        if self.falla:
            raise RuntimeError("la ventana ya no existe")
        self.iconos.append(ruta)

    def after(self, milisegundos, funcion):
        self.pendientes.append((milisegundos, funcion))


class PruebasIcono(unittest.TestCase):
    """el ícono va dentro del código, así que no depende de ningún archivo extra."""

    def test_icono_embebido_es_un_ico_valido(self):
        """el base64 se decodifica a un .ico con los 7 tamaños, de 16 a 256 px."""
        datos = base64.b64decode(icono_sogue.ICONO_BASE64)
        reservado, tipo, cantidad = struct.unpack("<HHH", datos[:6])
        self.assertEqual((reservado, tipo, cantidad), (0, 1, 7))
        anchos = [datos[6 + 16 * i] or 256 for i in range(cantidad)]
        self.assertEqual(anchos, [16, 24, 32, 48, 64, 128, 256])

    def test_ruta_icono_escribe_el_archivo(self):
        """se crea el .ico en la carpeta temporal con el contenido correcto."""
        ruta = icono_sogue.ruta_icono()
        self.assertTrue(os.path.exists(ruta))
        with open(ruta, "rb") as archivo:
            self.assertEqual(archivo.read(), base64.b64decode(icono_sogue.ICONO_BASE64))

    def test_poner_icono_lo_repite_para_ganarle_a_customtkinter(self):
        """se pone al abrir y se repite a los 250 y 700 ms."""
        ventana = VentanaFalsa()
        icono_sogue.poner_icono(ventana)
        self.assertEqual([m for m, _ in ventana.pendientes], [250, 700])
        for _, funcion in ventana.pendientes:
            funcion()
        self.assertEqual(len(ventana.iconos), 3)
        self.assertEqual(len(set(ventana.iconos)), 1)
        self.assertTrue(ventana.iconos[0].endswith(".ico"))

    def test_poner_icono_no_rompe_si_la_ventana_se_cerro(self):
        """si la ventana ya no existe, no hay error."""
        ventana = VentanaFalsa(falla=True)
        icono_sogue.poner_icono(ventana)
        for _, funcion in ventana.pendientes:
            funcion()
        self.assertEqual(ventana.iconos, [])


if __name__ == "__main__":
    unittest.main()