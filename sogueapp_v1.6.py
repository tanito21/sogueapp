import customtkinter as ctk
import sqlite3
import hashlib
from tkinter import messagebox

#conexión con la bd y creación de la tabla de usuarios
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

#variable para saber quién inició sesión
usuario_actual = None

#base de datos del programa

def hash_contraseña(clave):
    """Convierte una contraseña a hash SHA256"""
    return hashlib.sha256(clave.encode()).hexdigest()

def usuario_existe(nombre):
    """Verifica si un usuario ya existe en la base de datos"""
    cursor.execute("SELECT usuario FROM usuarios WHERE usuario=?", (nombre,))
    return cursor.fetchone() is not None

def crear_usuario(nombre, clave):
    """Crea un nuevo usuario en la base de datos"""
    try:
        clave_hash = hash_contraseña(clave)
        cursor.execute("INSERT INTO usuarios (usuario, clave) VALUES (?, ?)", 
                      (nombre, clave_hash))
        base_datos.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def verificar_usuario(nombre, clave):
    """Verifica si el usuario y contraseña son correctos"""
    cursor.execute("SELECT clave FROM usuarios WHERE usuario=?", (nombre,))
    fila = cursor.fetchone()
    
    if fila is None:
        return False
    
    clave_hash = hash_contraseña(clave)
    return fila[0] == clave_hash

#pantalla general

def cerrar_sesion(ventana):
    """Cierra la sesión actual y vuelve al login"""
    global usuario_actual
    usuario_actual = None
    ventana.destroy()
    crear_pantalla_login()

def abrir_app_principal():
    """Ventana principal después de iniciar sesión"""
    ventana_principal = ctk.CTk()
    ventana_principal.geometry("400x300")
    ventana_principal.title("Panel Principal")
    ventana_principal.resizable(False, False)

    #bienvenida para usuario
    titulo = ctk.CTkLabel(
        ventana_principal, 
        text=f"Bienvenido {usuario_actual}", 
        font=("Arial", 22, "bold")
    )
    titulo.pack(pady=50)

    #información de la sesión
    info = ctk.CTkLabel(
        ventana_principal,
        text=f"Usuario: {usuario_actual}",
        font=("Arial", 12)
    )
    info.pack(pady=10)

    #botón para cerrar sesión
    boton_cerrar = ctk.CTkButton(
        ventana_principal, 
        text="Cerrar Sesión",
        command=lambda: cerrar_sesion(ventana_principal),
        width=200,
        height=40
    )
    boton_cerrar.pack(pady=30)

    ventana_principal.mainloop()

def crear_pantalla_login():
    """Crea la interfaz de login/registro"""
    ventana = ctk.CTk()
    ventana.geometry("400x500")
    ventana.title("SogueApp")
    ventana.resizable(False, False)

    #marco principal
    marco_principal = ctk.CTkFrame(ventana)
    marco_principal.pack(fill="both", expand=True, padx=20, pady=20)

    #título
    titulo = ctk.CTkLabel(
        marco_principal, 
        text="Control de Finanzas", 
        font=("Arial", 24, "bold")
    )
    titulo.pack(pady=20)

    #login
    def mostrar_login():
        """Muestra el formulario de login"""
        limpiar_marco_formulario()
        
        ctk.CTkLabel(marco_formulario, text="Iniciar Sesión", font=("Arial", 16, "bold")).pack(pady=10)
        
        campo_usuario_login = ctk.CTkEntry(marco_formulario, placeholder_text="Usuario", width=250)
        campo_usuario_login.pack(pady=10)
        
        campo_clave_login = ctk.CTkEntry(marco_formulario, placeholder_text="Contraseña", show="*", width=250)
        campo_clave_login.pack(pady=10)
        
        etiqueta_error_login = ctk.CTkLabel(marco_formulario, text="", text_color="red")
        etiqueta_error_login.pack(pady=5)

        def intentar_login():
            global usuario_actual
            nombre = campo_usuario_login.get().strip()
            clave = campo_clave_login.get()

            if not nombre or not clave:
                etiqueta_error_login.configure(text="Completa todos los campos")
                return

            if verificar_usuario(nombre, clave):
                usuario_actual = nombre
                ventana.destroy()
                abrir_app_principal()
            else:
                etiqueta_error_login.configure(text="Usuario o contraseña incorrectos")
                campo_clave_login.delete(0, "end")

        boton_entrar = ctk.CTkButton(
            marco_formulario,
            text="Entrar",
            command=intentar_login,
            width=200,
            height=40
        )
        boton_entrar.pack(pady=15)

    #registro del usuario
    def mostrar_registro():
        """Muestra el formulario de registro"""
        limpiar_marco_formulario()
        
        ctk.CTkLabel(marco_formulario, text="Crear Cuenta", font=("Arial", 16, "bold")).pack(pady=10)
        
        campo_usuario_reg = ctk.CTkEntry(marco_formulario, placeholder_text="Usuario", width=250)
        campo_usuario_reg.pack(pady=10)
        
        campo_clave_reg = ctk.CTkEntry(marco_formulario, placeholder_text="Contraseña", show="*", width=250)
        campo_clave_reg.pack(pady=10)
        
        campo_confirmar = ctk.CTkEntry(marco_formulario, placeholder_text="Confirmar Contraseña", show="*", width=250)
        campo_confirmar.pack(pady=10)
        
        etiqueta_error_reg = ctk.CTkLabel(marco_formulario, text="", text_color="red")
        etiqueta_error_reg.pack(pady=5)

        def intentar_registro():
            nombre = campo_usuario_reg.get().strip()
            clave = campo_clave_reg.get()
            confirmar = campo_confirmar.get()

            if not nombre or not clave or not confirmar:
                etiqueta_error_reg.configure(text="Completa todos los campos")
                return

            if len(nombre) < 3:
                etiqueta_error_reg.configure(text="El usuario debe tener al menos 3 caracteres")
                return

            if len(clave) < 5:
                etiqueta_error_reg.configure(text="La contraseña debe tener al menos 5 caracteres")
                return

            if clave != confirmar:
                etiqueta_error_reg.configure(text="Las contraseñas no coinciden")
                campo_clave_reg.delete(0, "end")
                campo_confirmar.delete(0, "end")
                return

            if usuario_existe(nombre):
                etiqueta_error_reg.configure(text="El usuario ya existe")
                return

            if crear_usuario(nombre, clave):
                etiqueta_error_reg.configure(text="¡Registro exitoso! Inicia sesión", text_color="green")
                campo_usuario_reg.delete(0, "end")
                campo_clave_reg.delete(0, "end")
                campo_confirmar.delete(0, "end")
                ventana.after(1500, mostrar_login)
            else:
                etiqueta_error_reg.configure(text="Error al crear la cuenta")

        boton_registrar = ctk.CTkButton(
            marco_formulario,
            text="Registrarse",
            command=intentar_registro,
            width=200,
            height=40
        )
        boton_registrar.pack(pady=15)

    def limpiar_marco_formulario():
        """Limpia el marco de formulario"""
        for widget in marco_formulario.winfo_children():
            widget.destroy()

    #botones de selección
    marco_botones = ctk.CTkFrame(marco_principal)
    marco_botones.pack(fill="x", pady=10)

    boton_login = ctk.CTkButton(
        marco_botones,
        text="Iniciar Sesión",
        command=mostrar_login,
        width=150
    )
    boton_login.pack(side="left", padx=10)

    boton_registro = ctk.CTkButton(
        marco_botones,
        text="Registrarse",
        command=mostrar_registro,
        width=150
    )
    boton_registro.pack(side="left", padx=10)

    #recuadro del formulario dinámico
    marco_formulario = ctk.CTkFrame(marco_principal)
    marco_formulario.pack(fill="both", expand=True, pady=10)

    #login por defecto
    mostrar_login()

    ventana.mainloop()

#main que ejecuta nuestro código

if __name__ == "__main__":
    crear_pantalla_login()