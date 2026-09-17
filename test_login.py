import unittest
import os
import logica_login


class PruebasLogin(unittest.TestCase):

    def setUp(self):
        # este se va a ejecutar antes de cada prueba y usamos una bd de prueba para no cambiar el real
        logica_login.nombre_bd = "test_soguebase.db"
        logica_login.inicializar_db()
        self.pregunta = "¿Cuál es tu comida favorita?"
        self.respuesta = "Milanesa"

    def tearDown(self):
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
        self.assertTrue(logica_login.verificar_usuario("con_recuperacion", "NuevaClave1"))
        self.assertFalse(logica_login.verificar_usuario("con_recuperacion", "Clave123"))

    def test_recuperar_clave_con_respuesta_incorrecta(self):
        """Prueba que la respuesta secreta incorrecta no pase la validación."""
        logica_login.crear_usuario("con_recuperacion2", "Clave123", self.pregunta, self.respuesta)
        self.assertFalse(logica_login.verificar_respuesta_secreta("con_recuperacion2", "pizza"))

    def test_cambiar_clave_no_permite_clave_insegura(self):
        """Prueba que no se pueda cambiar a una contraseña que no cumpla el mínimo."""
        logica_login.crear_usuario("con_recuperacion3", "Clave123", self.pregunta, self.respuesta)
        resultado = logica_login.cambiar_clave("con_recuperacion3", "abc")
        self.assertFalse(resultado)
        # la clave vieja debe seguir funcionando
        self.assertTrue(logica_login.verificar_usuario("con_recuperacion3", "Clave123"))


if __name__ == '__main__':
    unittest.main()