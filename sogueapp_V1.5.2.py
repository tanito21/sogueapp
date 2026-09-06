import customtkinter as ctk
import sqlite3
import hashlib

# conexión a la base de datos y creación de la tabla de usuarios
base_datos = sqlite3.connect("soguebase.db")
cursor = base_datos.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE,
    clave TEXT)""")

base_datos.commit()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# variable para saber quién inició sesión
usuario_actual = None

def cerrar_sesion(ventana):
        # borra el usuario actual y vuelve a abrir el login
        global usuario_actual
        usuario_actual = None
        ventana.destroy()
        crear_pantalla_login()

def abrir_app_principal():
        # ventana básica que se muestra al entrar correctamente
        ventana_principal = ctk.CTk()
        ventana_principal.geometry("400x300")
        ventana_principal.title("inicio")

        titulo = ctk.CTkLabel(ventana_principal, text="bienvenido " + usuario_actual, font=("Arial", 20))
        titulo.pack(pady=50)

        boton_salir = ctk.CTkButton(ventana_principal, text="cerrar sesión", command=lambda: cerrar_sesion(ventana_principal))
        boton_salir.pack(pady=20)

        ventana_principal.mainloop()

def crear_pantalla_login():
        # crea la interfaz principal para iniciar sesión
        ventana_login = ctk.CTk()
        ventana_login.geometry("400x350")
        ventana_login.title("iniciar sesión")

        titulo = ctk.CTkLabel(ventana_login, text="control de finanzas", font=("Arial", 22, "bold"))
        titulo.pack(pady=30)

        campo_usuario = ctk.CTkEntry(ventana_login, placeholder_text="usuario", width=250)
        campo_usuario.pack(pady=10)

        campo_clave = ctk.CTkEntry(ventana_login, placeholder_text="contraseña", show="*", width=250)
        campo_clave.pack(pady=10)

        etiqueta_error = ctk.CTkLabel(ventana_login, text="", text_color="red")
        etiqueta_error.pack(pady=10)

        def intentar_ingresar():
                # verifica que el usuario y la contraseña coincidan con la base de datos
                global usuario_actual
                nombre = campo_usuario.get()
                clave = campo_clave.get()

                if nombre == "" or clave == "":
                        etiqueta_error.configure(text="completa todos los campos")
                        return

                # busca al usuario en la base de datos
                cursor.execute("SELECT clave FROM usuarios WHERE usuario=?", (nombre,))
                fila = cursor.fetchone()

                # convierte la clave escrita a hash para compararla
                clave_hash = hashlib.sha256(clave.encode()).hexdigest()

                if fila == None or fila[0] != clave_hash:
                        etiqueta_error.configure(text="datos incorrectos")
                        return

                # si todo está bien, entra al sistema
                usuario_actual = nombre
                ventana_login.destroy()
                abrir_app_principal()

        boton_entrar = ctk.CTkButton(ventana_login, text="entrar", command=intentar_ingresar)
        boton_entrar.pack(pady=20)

        ventana_login.mainloop()

# inicia el programa
if __name__ == "__main__":
        crear_pantalla_login()