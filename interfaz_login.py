import customtkinter as ctk
# importamos nuestro propio archivo de lógica
import logica_login

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

usuario_actual = None

# preguntas secretas disponibles para la recuperación de contraseña
PREGUNTAS_SECRETAS = [
    "¿Cuál es el nombre de tu primera mascota?",
    "¿Cuál es tu comida favorita?",
    "¿En qué ciudad naciste?",
]

# inicializamos la bd antes de arrancar la interfaz
logica_login.inicializar_db()


def cerrar_sesion(ventana):
    global usuario_actual
    usuario_actual = None
    ventana.destroy()
    crear_pantalla_login()


def abrir_app_principal():
    """Pantalla principal de la app. Por ahora cada sección es solo un
    placeholder con una descripción; cuando unamos este login con
    sogueapp.py, cada botón de la barra lateral va a abrir su función
    real (gastos, presupuesto, etc.) en vez de solo mostrar texto."""
    ventana_principal = ctk.CTk()
    ventana_principal.geometry("800x500")
    ventana_principal.title("SogueApp - Panel Principal")

    # ---- barra lateral con la navegación ----
    barra_lateral = ctk.CTkFrame(ventana_principal, width=180, corner_radius=0)
    barra_lateral.pack(side="left", fill="y")

    ctk.CTkLabel(barra_lateral, text="SogueApp", font=("Arial", 20, "bold")).pack(pady=(30, 5))
    ctk.CTkLabel(barra_lateral, text=f"Hola, {usuario_actual}", font=("Arial", 12),
                 text_color="gray").pack(pady=(0, 30))

    # ---- área de contenido, se redibuja según la sección elegida ----
    marco_contenido = ctk.CTkFrame(ventana_principal)
    marco_contenido.pack(side="left", fill="both", expand=True, padx=20, pady=20)

    def mostrar_seccion(titulo, descripcion):
        for widget in marco_contenido.winfo_children():
            widget.destroy()
        ctk.CTkLabel(marco_contenido, text=titulo, font=("Arial", 24, "bold")).pack(pady=(60, 10))
        ctk.CTkLabel(marco_contenido, text=descripcion, text_color="gray", wraplength=420).pack()

    # cada tupla es (texto del botón, descripción del placeholder). Cuando
    # se conecte con la app real, el "command" de cada botón va a llamar
    # a la función correspondiente en vez de mostrar_seccion(...)
    secciones = [
        ("🏠 Inicio", "Acá va a ir el resumen general de tus finanzas"),
        ("💸 Gastos", "Acá vas a poder registrar y consultar tus gastos"),
        ("📊 Presupuesto", "Acá vas a poder armar tu presupuesto mensual"),
        ("📈 Reportes", "Acá van a ir los reportes y gráficos"),
    ]

    for texto_boton, descripcion in secciones:
        ctk.CTkButton(barra_lateral, text=texto_boton, anchor="w",
                      fg_color="transparent", hover_color="#2b2b2b",
                      command=lambda t=texto_boton, d=descripcion: mostrar_seccion(t, d)
                      ).pack(fill="x", padx=15, pady=5)

    ctk.CTkButton(barra_lateral, text="Cerrar Sesión", fg_color="#d9534f",
                  command=lambda: cerrar_sesion(ventana_principal)).pack(side="bottom", fill="x", padx=15, pady=20)

    # arrancamos mostrando la sección de inicio
    mostrar_seccion(*secciones[0])

    ventana_principal.mainloop()


def crear_pantalla_login():
    ventana = ctk.CTk()
    ventana.geometry("400x550")
    ventana.title("SogueApp")

    marco_principal = ctk.CTkFrame(ventana)
    marco_principal.pack(fill="both", expand=True, padx=20, pady=20)
    ctk.CTkLabel(marco_principal, text="Control de Finanzas", font=("Arial", 24, "bold")).pack(pady=20)

    marco_botones = ctk.CTkFrame(marco_principal)
    marco_botones.pack(fill="x", pady=10)
    marco_formulario = ctk.CTkFrame(marco_principal)
    marco_formulario.pack(fill="both", expand=True, pady=10)

    def limpiar_formulario():
        for widget in marco_formulario.winfo_children():
            widget.destroy()

    def mostrar_login():
        limpiar_formulario()
        ctk.CTkLabel(marco_formulario, text="Iniciar Sesión", font=("Arial", 16, "bold")).pack(pady=10)
        user = ctk.CTkEntry(marco_formulario, placeholder_text="Usuario")
        user.pack(pady=10)
        pwd = ctk.CTkEntry(marco_formulario, placeholder_text="Contraseña", show="*")
        pwd.pack(pady=10)
        error = ctk.CTkLabel(marco_formulario, text="", text_color="red")
        error.pack(pady=5)

        def intentar_login():
            global usuario_actual
            if logica_login.verificar_usuario(user.get().strip(), pwd.get()):
                usuario_actual = user.get().strip()
                ventana.destroy()
                abrir_app_principal()
            else:
                error.configure(text="Usuario o contraseña incorrectos", text_color="red")

        ctk.CTkButton(marco_formulario, text="Entrar", command=intentar_login).pack(pady=15)

        # link para recuperar la contraseña
        link_olvide = ctk.CTkButton(marco_formulario, text="¿Olvidaste tu contraseña?",
                                     fg_color="transparent", text_color="#3b8ed0",
                                     hover=False, command=mostrar_recuperar)
        link_olvide.pack(pady=5)

    def mostrar_registro():
        limpiar_formulario()
        ctk.CTkLabel(marco_formulario, text="Crear Cuenta", font=("Arial", 16, "bold")).pack(pady=10)
        user = ctk.CTkEntry(marco_formulario, placeholder_text="Usuario")
        user.pack(pady=8)
        pwd = ctk.CTkEntry(marco_formulario, placeholder_text="Contraseña", show="*")
        pwd.pack(pady=8)
        ctk.CTkLabel(marco_formulario, text="Mínimo 8 caracteres, con mayúscula, minúscula y número",
                     text_color="gray", font=("Arial", 10)).pack()

        pregunta_var = ctk.StringVar(value=PREGUNTAS_SECRETAS[0])
        ctk.CTkOptionMenu(marco_formulario, values=PREGUNTAS_SECRETAS, variable=pregunta_var).pack(pady=8)
        respuesta = ctk.CTkEntry(marco_formulario, placeholder_text="Respuesta secreta")
        respuesta.pack(pady=8)

        error = ctk.CTkLabel(marco_formulario, text="", text_color="red")
        error.pack(pady=5)

        def intentar_registro():
            nombre = user.get().strip()
            clave = pwd.get()

            if not nombre or not clave or not respuesta.get().strip():
                error.configure(text="Completa todos los datos", text_color="red")
                return

            if logica_login.usuario_existe(nombre):
                error.configure(text="El usuario ya existe", text_color="red")
                return

            clave_ok, motivo = logica_login.clave_es_segura(clave)
            if not clave_ok:
                error.configure(text=motivo, text_color="red")
                return

            if logica_login.crear_usuario(nombre, clave, pregunta_var.get(), respuesta.get()):
                error.configure(text="¡Éxito! Inicia sesión", text_color="green")
                ventana.after(1500, mostrar_login)
            else:
                error.configure(text="No se pudo crear el usuario", text_color="red")

        ctk.CTkButton(marco_formulario, text="Registrarse", command=intentar_registro).pack(pady=15)

    def mostrar_recuperar():
        """Primer paso de la recuperación: pedimos el usuario y buscamos su pregunta secreta."""
        limpiar_formulario()
        ctk.CTkLabel(marco_formulario, text="Recuperar Contraseña", font=("Arial", 16, "bold")).pack(pady=10)
        user = ctk.CTkEntry(marco_formulario, placeholder_text="Usuario")
        user.pack(pady=10)
        error = ctk.CTkLabel(marco_formulario, text="", text_color="red")
        error.pack(pady=5)

        def buscar_pregunta():
            nombre = user.get().strip()
            pregunta = logica_login.obtener_pregunta_secreta(nombre)
            if pregunta is None:
                error.configure(text="Ese usuario no existe")
            else:
                mostrar_responder_pregunta(nombre, pregunta)

        ctk.CTkButton(marco_formulario, text="Buscar", command=buscar_pregunta).pack(pady=15)
        ctk.CTkButton(marco_formulario, text="Volver a Iniciar Sesión", fg_color="transparent",
                      text_color="#3b8ed0", hover=False, command=mostrar_login).pack(pady=5)

    def mostrar_responder_pregunta(nombre, pregunta):
        """Segundo paso: mostramos la pregunta secreta y pedimos la respuesta y la nueva clave."""
        limpiar_formulario()
        ctk.CTkLabel(marco_formulario, text="Recuperar Contraseña", font=("Arial", 16, "bold")).pack(pady=10)
        ctk.CTkLabel(marco_formulario, text=pregunta, wraplength=280).pack(pady=5)
        respuesta = ctk.CTkEntry(marco_formulario, placeholder_text="Tu respuesta")
        respuesta.pack(pady=8)
        nueva_pwd = ctk.CTkEntry(marco_formulario, placeholder_text="Nueva contraseña", show="*")
        nueva_pwd.pack(pady=8)
        ctk.CTkLabel(marco_formulario, text="Mínimo 8 caracteres, con mayúscula, minúscula y número",
                     text_color="gray", font=("Arial", 10)).pack()

        error = ctk.CTkLabel(marco_formulario, text="", text_color="red")
        error.pack(pady=5)

        def confirmar_cambio():
            if not logica_login.verificar_respuesta_secreta(nombre, respuesta.get()):
                error.configure(text="Respuesta incorrecta", text_color="red")
                return

            if logica_login.cambiar_clave(nombre, nueva_pwd.get()):
                error.configure(text="¡Contraseña actualizada! Inicia sesión", text_color="green")
                ventana.after(1500, mostrar_login)
            else:
                error.configure(text="La contraseña no cumple los requisitos", text_color="red")

        ctk.CTkButton(marco_formulario, text="Cambiar Contraseña", command=confirmar_cambio).pack(pady=15)

    ctk.CTkButton(marco_botones, text="Iniciar Sesión", command=mostrar_login, width=150).pack(side="left", padx=10)
    ctk.CTkButton(marco_botones, text="Registrarse", command=mostrar_registro, width=150).pack(side="left", padx=10)

    mostrar_login()
    ventana.mainloop()


if __name__ == "__main__":
    crear_pantalla_login()