<<<<<<< HEAD
"""pruebas unitarias de logica_login (ejecutar: python -m unittest -v)."""

import hashlib
import os
import sqlite3
import tempfile
import unittest

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
=======
import unittest
import os
import logica_login


class PruebasLogin(unittest.TestCase):

    def setUp(self):
        # este se va a ejecutar antes de cada prueba y usamos una bd de prueba para no cambiar el real
        logica_login.nombre_bd = "test_soguebase.db"
>>>>>>> 7bd8bf5674ae67b1e45373b0b5fea840cc61ce72
        logica_login.inicializar_db()
        self.pregunta = "¿Cuál es tu comida favorita?"
        self.respuesta = "Milanesa"

    def tearDown(self):
<<<<<<< HEAD
        # borramos la base de prueba y dejamos el módulo como estaba
        logica_login.nombre_bd = self.bd_original
        logica_login.ITERACIONES = self.iteraciones_original
        if os.path.exists(BD_PRUEBA):
            os.remove(BD_PRUEBA)

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
=======
        # este se ejecuta después de cada prueba y luego borra la bd de prueba
        if os.path.exists("test_soguebase.db"):
            os.remove("test_soguebase.db")

    def test_crear_y_verificar_usuario(self):
        """Prueba que un usuario se cree correctamente y pueda iniciar sesión."""
        # 1- creamos el usuario con una clave segura
        resultado_creacion = logica_login.crear_usuario(
            "admin_prueba", "Clave123", self.pregunta, self.respuesta)
        self.assertTrue(resultado_creacion)

        # 2- verificamos que el login sea correcto con la clave que corresponde
        login_exitoso = logica_login.verificar_usuario("admin_prueba", "Clave123")
        self.assertTrue(login_exitoso)

        # 3- verificamos que el login falle con una clave incorrecta
        login_fallido = logica_login.verificar_usuario("admin_prueba", "clavemala")
        self.assertFalse(login_fallido)

    def test_no_permite_usuario_duplicado(self):
        """Prueba que no se pueda crear dos veces el mismo usuario."""
        logica_login.crear_usuario("repetido", "Clave123", self.pregunta, self.respuesta)
        resultado = logica_login.crear_usuario("repetido", "OtraClave1", self.pregunta, self.respuesta)
        self.assertFalse(resultado)

    def test_clave_es_segura(self):
        """Prueba las distintas reglas de seguridad de la contraseña."""
        self.assertFalse(logica_login.clave_es_segura("corta1A")[0])       # muy corta
        self.assertFalse(logica_login.clave_es_segura("clavesinnumero")[0])  # sin número
        self.assertFalse(logica_login.clave_es_segura("clavesinmayus1")[0])  # sin mayúscula
        self.assertFalse(logica_login.clave_es_segura("CLAVESINMINUS1")[0])  # sin minúscula
        self.assertTrue(logica_login.clave_es_segura("Clave123")[0])       # cumple todo

    def test_no_crea_usuario_con_clave_insegura(self):
        """Prueba que no se cree el usuario si la contraseña no es segura."""
        resultado = logica_login.crear_usuario("usuario_debil", "abc", self.pregunta, self.respuesta)
        self.assertFalse(resultado)
        self.assertFalse(logica_login.usuario_existe("usuario_debil"))

    def test_recuperar_clave_con_respuesta_correcta(self):
        """Prueba el flujo completo de recuperación de contraseña."""
        logica_login.crear_usuario("con_recuperacion", "Clave123", self.pregunta, self.respuesta)

        # la pregunta guardada debe coincidir con la que se usó al registrar
        pregunta_guardada = logica_login.obtener_pregunta_secreta("con_recuperacion")
        self.assertEqual(pregunta_guardada, self.pregunta)

        # la respuesta correcta (sin importar mayúsculas o espacios) debe validar
        self.assertTrue(logica_login.verificar_respuesta_secreta("con_recuperacion", "  milanesa  "))

        # cambiamos la clave y verificamos que el login funcione con la nueva
        resultado_cambio = logica_login.cambiar_clave("con_recuperacion", "NuevaClave1")
        self.assertTrue(resultado_cambio)
>>>>>>> 7bd8bf5674ae67b1e45373b0b5fea840cc61ce72
        self.assertTrue(logica_login.verificar_usuario("con_recuperacion", "NuevaClave1"))
        self.assertFalse(logica_login.verificar_usuario("con_recuperacion", "Clave123"))

    def test_recuperar_clave_con_respuesta_incorrecta(self):
<<<<<<< HEAD
        """una respuesta secreta incorrecta se rechaza."""
=======
        """Prueba que la respuesta secreta incorrecta no pase la validación."""
>>>>>>> 7bd8bf5674ae67b1e45373b0b5fea840cc61ce72
        logica_login.crear_usuario("con_recuperacion2", "Clave123", self.pregunta, self.respuesta)
        self.assertFalse(logica_login.verificar_respuesta_secreta("con_recuperacion2", "pizza"))

    def test_cambiar_clave_no_permite_clave_insegura(self):
<<<<<<< HEAD
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
        """los tres roles que ofrece el registro se pueden guardar."""
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

    #administrador inicial y listado

    def test_admin_inicial_existe_y_es_unico(self):
        """al inicializar se crea un admin, y repetir la inicialización no lo duplica."""
        self.assertEqual(logica_login.obtener_rol_usuario(logica_login.ADMIN_USUARIO), "admin")
        self.assertTrue(logica_login.verificar_usuario(
            logica_login.ADMIN_USUARIO, logica_login.ADMIN_CLAVE_INICIAL))
        logica_login.inicializar_db()
        admins = [u for u in logica_login.obtener_todos_los_usuarios() if u[2] == "admin"]
        self.assertEqual(len(admins), 1)

    def test_listado_de_usuarios(self):
        """el listado devuelve (id, usuario, rol) de todos los usuarios."""
        logica_login.crear_usuario("listado1", "Clave123", self.pregunta, self.respuesta, "ahorro")
        filas = logica_login.obtener_todos_los_usuarios()
        self.assertIn("listado1", [f[1] for f in filas])
        self.assertTrue(all(len(f) == 3 for f in filas))

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

    def test_convertir_monto(self):
        """acepta montos con separadores de miles y rechaza lo que no sirve."""
        self.assertEqual(logica_login.convertir_monto("1500000"), 1500000.0)
        self.assertEqual(logica_login.convertir_monto("1.500.000"), 1500000.0)
        self.assertEqual(logica_login.convertir_monto("1,500,000"), 1500000.0)
        self.assertEqual(logica_login.convertir_monto(" 2500.50 "), 2500.5)
        self.assertEqual(logica_login.convertir_monto(750000), 750000.0)
        for invalido in ("", "abc", "0", "-5", "nan", "inf", "1.2.3", None):
            self.assertIsNone(logica_login.convertir_monto(invalido))

    #documentación

    def test_generar_documentacion(self):
        """pydoc crea el html del módulo en la carpeta indicada."""
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = logica_login.generar_documentacion(carpeta)
            self.assertTrue(os.path.exists(ruta))
            with open(ruta, encoding="utf-8") as archivo:
                contenido = archivo.read()
        self.assertIn("crear_usuario", contenido)
        self.assertIn("generar_presupuesto", contenido)


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
        self.assertEqual(logica_login.obtener_categorias(logica_login.ADMIN_USUARIO), [])


if __name__ == "__main__":
    unittest.main()
=======
        """Prueba que no se pueda cambiar a una contraseña que no cumpla el mínimo."""
        logica_login.crear_usuario("con_recuperacion3", "Clave123", self.pregunta, self.respuesta)
        resultado = logica_login.cambiar_clave("con_recuperacion3", "abc")
        self.assertFalse(resultado)
        # la clave vieja debe seguir funcionando
        self.assertTrue(logica_login.verificar_usuario("con_recuperacion3", "Clave123"))


if __name__ == '__main__':
    unittest.main()
>>>>>>> 7bd8bf5674ae67b1e45373b0b5fea840cc61ce72
