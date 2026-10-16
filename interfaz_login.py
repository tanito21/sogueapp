import customtkinter as ctk
<<<<<<< HEAD
from datetime import datetime
from tkinter import messagebox
import random
=======
# importamos nuestro propio archivo de lógica
>>>>>>> 7bd8bf5674ae67b1e45373b0b5fea840cc61ce72
import logica_login

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

usuario_actual = None
<<<<<<< HEAD
rol_actual = "completo"

=======

# preguntas secretas disponibles para la recuperación de contraseña
>>>>>>> 7bd8bf5674ae67b1e45373b0b5fea840cc61ce72
PREGUNTAS_SECRETAS = [
    "¿Cuál es el nombre de tu primera mascota?",
    "¿Cuál es tu comida favorita?",
    "¿En qué ciudad naciste?",
]

<<<<<<< HEAD
# Consejos financieros rotativos para el inicio
CONSEJOS_FINANCIEROS = [
    "💡 Consejo: Intenta ahorrar al menos el 20% de tus ingresos mensuales para imprevistos.",
    "💡 Consejo: Revisa tus gastos pequeños diarios; los 'gastos hormiga' suman mucho al mes.",
    "💡 Consejo: Antes de realizar una compra grande, espera 48 horas para evitar compras impulsivas.",
    "💡 Consejo: Define presupuestos claros por categoría para mantener tus finanzas bajo control."
]

logica_login.inicializar_db()

def cerrar_sesion(ventana):
    global usuario_actual, rol_actual
    usuario_actual = None
    rol_actual = "completo"
    ventana.destroy()
    crear_pantalla_login()

def abrir_app_principal():
    global usuario_actual, rol_actual
    rol_actual = logica_login.obtener_rol_usuario(usuario_actual)

    ventana_principal = ctk.CTk()
    ventana_principal.geometry("980x680")
    ventana_principal.title(f"SogueApp - Panel Principal [{usuario_actual} | Rol: {rol_actual.upper()}]")

    # Barra lateral elegante
    barra_lateral = ctk.CTkFrame(ventana_principal, width=220, corner_radius=0)
    barra_lateral.pack(side="left", fill="y")

    ctk.CTkLabel(barra_lateral, text="💰 SogueApp", font=("Arial", 20, "bold")).pack(pady=(30, 5))
    ctk.CTkLabel(barra_lateral, text=f"Usuario: {usuario_actual}\nRol: {rol_actual}", font=("Arial", 11),
                 text_color="#2ec4b6").pack(pady=(0, 20))

    marco_contenido = ctk.CTkFrame(ventana_principal, fg_color="transparent")
    marco_contenido.pack(side="left", fill="both", expand=True, padx=20, pady=20)

    def limpiar_contenido():
        for widget in marco_contenido.winfo_children():
            widget.destroy()

    #parte de inicio (con consejos y barra visual de gastos)
    def seccion_inicio():
        limpiar_contenido()
        ctk.CTkLabel(marco_contenido, text="🏠 Resumen y Panel General", font=("Arial", 22, "bold")).pack(pady=(10, 5), anchor="w")
        
        # Tarjeta de consejo financiero dinámico
        f_consejo = ctk.CTkFrame(marco_contenido, fg_color="#1f2937", corner_radius=8)
        f_consejo.pack(fill="x", pady=10, padx=5)
        consejo_elegido = random.choice(CONSEJOS_FINANCIEROS)
        ctk.CTkLabel(f_consejo, text=consejo_elegido, font=("Arial", 13), text_color="#38bdf8", wraplength=680).pack(padx=15, pady=12)

        # Panel visual de resumen y barras
        ctk.CTkLabel(marco_contenido, text="📊 Estado General de Presupuestos y Gastos", font=("Arial", 16, "bold")).pack(pady=(15, 5), anchor="w")
        
        f_graficos = ctk.CTkScrollableFrame(marco_contenido, width=700, height=350, fg_color="transparent")
        f_graficos.pack(fill="both", expand=True, pady=5)

        categorias = logica_login.obtener_categorias(usuario_actual)

        if not categorias:
            ctk.CTkLabel(f_graficos, text="No hay presupuestos generados todavía. Ve a la sección 'Presupuesto' para crear uno.", text_color="gray").pack(pady=20)
        else:
            for cat, pres, gast in categorias:
                f_item = ctk.CTkFrame(f_graficos, fg_color="#111827", corner_radius=6)
                f_item.pack(fill="x", pady=6, padx=5)
                
                ctk.CTkLabel(f_item, text=f"📂 {cat}", font=("Arial", 13, "bold")).pack(side="top", anchor="w", padx=12, pady=(8, 2))
                
                # Cálculo de porcentaje para la barra visual
                porcentaje = (gast / pres) if pres > 0 else 0
                if porcentaje > 1.0: porcentaje = 1.0
                
                info_txt = f"Presupuesto: Gs. {pres:,.0f} | Gastado: Gs. {gast:,.0f} | Saldo: Gs. {pres - gast:,.0f}"
                ctk.CTkLabel(f_item, text=info_txt, font=("Arial", 11), text_color="gray").pack(side="top", anchor="w", padx=12, pady=(0, 4))
                
                # Barra de progreso visual CustomTkinter
                barra = ctk.CTkProgressBar(f_item, width=650, height=12)
                barra.pack(side="top", padx=12, pady=(0, 10))
                barra.set(porcentaje)
                
                # Color dinámico de la barra si excede el presupuesto
                if gast > pres:
                    barra.configure(progress_color="#ef4444") # Rojo alerta
                elif porcentaje > 0.8:
                    barra.configure(progress_color="#f59e0b") # Amarillo precaución
                else:
                    barra.configure(progress_color="#10b981") # Verde saludable

    #presupuestos (Funcionalidad Principal)
    def seccion_presupuesto():
        limpiar_contenido()
        ctk.CTkLabel(marco_contenido, text="📊 Gestión de Presupuestos", font=("Arial", 22, "bold")).pack(pady=(10, 5), anchor="w")
        ctk.CTkLabel(marco_contenido, text="Genera tu base de ingresos y distribuye tus límites por categoría.", font=("Arial", 12), text_color="gray").pack(anchor="w", pady=(0, 15))

        f_gen = ctk.CTkFrame(marco_contenido)
        f_gen.pack(fill="x", pady=10)

        ent_ingreso = ctk.CTkEntry(f_gen, placeholder_text="Ingreso mensual total (Gs.)", width=220)
        ent_ingreso.pack(side="left", padx=10, pady=12)

        def generar_base():
            # primero validamos el ingreso, así no preguntamos por algo que va a fallar
            if logica_login.convertir_monto(ent_ingreso.get()) is None:
                messagebox.showerror("Error", "Ingrese un valor numérico válido mayor a 0.")
                return

            # si ya hay presupuesto, avisamos antes de reemplazarlo
            if logica_login.obtener_categorias(usuario_actual) and not messagebox.askyesno(
                    "Confirmar", "Ya tienes un presupuesto. Al generar uno nuevo se reemplaza el actual y se borran sus gastos.\n\n¿Continuar?"):
                return

            if not logica_login.generar_presupuesto(usuario_actual, ent_ingreso.get()):
                messagebox.showerror("Error", "No se pudo generar el presupuesto.")
                return

            messagebox.showinfo("Éxito", "¡Presupuesto generado con éxito bajo el método 50/30/20!")
            seccion_presupuesto()

        ctk.CTkButton(f_gen, text="Generar Presupuesto 50/30/20", command=generar_base, fg_color="#2c82c9").pack(side="left", padx=10)

        caja_p = ctk.CTkTextbox(marco_contenido, font=("Courier New", 12), width=720, height=350)
        caja_p.pack(fill="both", expand=True, pady=10)
        
        cats_db = logica_login.obtener_categorias(usuario_actual)

        if not cats_db:
            caja_p.insert("end", "ℹ️ Todavía no hay categorías generadas. Ingresa un monto arriba y haz clic en 'Generar Presupuesto'.\n")
        else:
            for c in cats_db:
                caja_p.insert("end", f"📂 Categoría: {c[0]}\n 💰 Presupuesto: Gs. {c[1]:,.0f}\n 📉 Gastado: Gs. {c[2]:,.0f}\n 💳 Disponible: Gs. {c[1]-c[2]:,.0f}\n\n")
        caja_p.configure(state="disabled")

    #gatos (Próximamente, todavía no se termina)
    def seccion_gastos():
        limpiar_contenido()
        ctk.CTkLabel(marco_contenido, text="💸 Registro de Gastos (PRÓXIMAMENTE)", font=("Arial", 22, "bold")).pack(pady=(10, 5), anchor="w")
        
        f_aviso = ctk.CTkFrame(marco_contenido, fg_color="#1f2937")
        f_aviso.pack(fill="both", expand=True, padx=10, pady=20)
        ctk.CTkLabel(f_aviso, text="🚧 MÓDULO EN CONSTRUCCIÓN 🚧", font=("Arial", 18, "bold"), text_color="#f59e0b").pack(pady=(80, 15))
        ctk.CTkLabel(f_aviso, text="Estamos haciendo aún algunos ajustes.\nEstaremos actualizando los commits.", font=("Arial", 13), text_color="gray").pack(pady=10)

    #metas de ahorro (Próximamente, falta)
    def seccion_ahorros():
        limpiar_contenido()
        ctk.CTkLabel(marco_contenido, text="🎯 Metas de Ahorro (EN CONSTRUCCIÓN)", font=("Arial", 22, "bold")).pack(pady=(10, 5), anchor="w")
        
        f_aviso2 = ctk.CTkFrame(marco_contenido, fg_color="#1f2937")
        f_aviso2.pack(fill="both", expand=True, padx=10, pady=20)
        ctk.CTkLabel(f_aviso2, text="🚧 MÓDULO PRÓXIMAMENTE 🚧", font=("Arial", 18, "bold"), text_color="#f59e0b").pack(pady=(80, 15))
        ctk.CTkLabel(f_aviso2, text="Este módulo también falta ajustar.", font=("Arial", 13), text_color="gray").pack(pady=10)

    # Construcción de la barra lateral según los permisos y el orden solicitado (Presupuesto antes de Gastos)
    secciones = []
    if rol_actual in ["admin", "completo", "presupuesto"]:
        secciones.append(("🏠 Inicio", seccion_inicio))
        secciones.append(("📊 Presupuesto", seccion_presupuesto))
        secciones.append(("💸 Gastos (Próximamente)", seccion_gastos))
    if rol_actual in ["admin", "completo", "ahorro"]:
        secciones.append(("🎯 Ahorros (En Construcción)", seccion_ahorros))

    for texto_boton, funcion_seccion in secciones:
        ctk.CTkButton(barra_lateral, text=texto_boton, anchor="w",
                      fg_color="transparent", hover_color="#2b2b2b",
                      command=funcion_seccion
=======
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
>>>>>>> 7bd8bf5674ae67b1e45373b0b5fea840cc61ce72
                      ).pack(fill="x", padx=15, pady=5)

    ctk.CTkButton(barra_lateral, text="Cerrar Sesión", fg_color="#d9534f",
                  command=lambda: cerrar_sesion(ventana_principal)).pack(side="bottom", fill="x", padx=15, pady=20)

<<<<<<< HEAD
    if secciones:
        secciones[0][1]() # Iniciar en la primera sección por defecto

    ventana_principal.mainloop()

def crear_pantalla_login():
    ventana = ctk.CTk()
    ventana.geometry("420x600")
    ventana.title("SogueApp - Login")

    marco_principal = ctk.CTkFrame(ventana)
    marco_principal.pack(fill="both", expand=True, padx=20, pady=20)
    ctk.CTkLabel(marco_principal, text="SogueApp Financiera", font=("Arial", 22, "bold")).pack(pady=15)

    marco_botones = ctk.CTkFrame(marco_principal)
    marco_botones.pack(fill="x", pady=5)
=======
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
>>>>>>> 7bd8bf5674ae67b1e45373b0b5fea840cc61ce72
    marco_formulario = ctk.CTkFrame(marco_principal)
    marco_formulario.pack(fill="both", expand=True, pady=10)

    def limpiar_formulario():
        for widget in marco_formulario.winfo_children():
            widget.destroy()

    def mostrar_login():
        limpiar_formulario()
        ctk.CTkLabel(marco_formulario, text="Iniciar Sesión", font=("Arial", 16, "bold")).pack(pady=10)
<<<<<<< HEAD
        user = ctk.CTkEntry(marco_formulario, placeholder_text="Usuario", width=280)
        user.pack(pady=8)
        pwd = ctk.CTkEntry(marco_formulario, placeholder_text="Contraseña", show="*", width=280)
        pwd.pack(pady=8)
=======
        user = ctk.CTkEntry(marco_formulario, placeholder_text="Usuario")
        user.pack(pady=10)
        pwd = ctk.CTkEntry(marco_formulario, placeholder_text="Contraseña", show="*")
        pwd.pack(pady=10)
>>>>>>> 7bd8bf5674ae67b1e45373b0b5fea840cc61ce72
        error = ctk.CTkLabel(marco_formulario, text="", text_color="red")
        error.pack(pady=5)

        def intentar_login():
            global usuario_actual
<<<<<<< HEAD
            # Permitir acceso rápido o normal al administrador creado por defecto ('administrator' / '123')
=======
>>>>>>> 7bd8bf5674ae67b1e45373b0b5fea840cc61ce72
            if logica_login.verificar_usuario(user.get().strip(), pwd.get()):
                usuario_actual = user.get().strip()
                ventana.destroy()
                abrir_app_principal()
            else:
                error.configure(text="Usuario o contraseña incorrectos", text_color="red")

<<<<<<< HEAD
        ctk.CTkButton(marco_formulario, text="Entrar", command=intentar_login, width=280, fg_color="#2c82c9").pack(pady=12)
        ctk.CTkButton(marco_formulario, text="¿Olvidaste tu contraseña?",
                      fg_color="transparent", text_color="#3b8ed0",
                      hover=False, command=mostrar_recuperar).pack(pady=5)

    def mostrar_registro():
        limpiar_formulario()
        ctk.CTkLabel(marco_formulario, text="Crear Cuenta Nueva", font=("Arial", 16, "bold")).pack(pady=5)
        user = ctk.CTkEntry(marco_formulario, placeholder_text="Usuario", width=280)
        user.pack(pady=6)
        pwd = ctk.CTkEntry(marco_formulario, placeholder_text="Contraseña (mín. 8 carac., 1 mayús., 1 núm.)", show="*", width=280)
        pwd.pack(pady=6)
        
        # Selector de rol con explicaciones claras (Sin opción de crear administrador por seguridad)
        ctk.CTkLabel(marco_formulario, text="Selecciona tu tipo de perfil:", font=("Arial", 11, "bold")).pack(anchor="w", padx=15, pady=(5, 0))
        
        rol_opciones = {
            "Usuario Completo (Presupuestos + Ahorros)": "completo",
            "Solo Presupuesto (Quiero ver cómo gastar y organizar)": "presupuesto",
            "Solo Ahorros (Quiero llevar un registro de mis metas)": "ahorro"
        }
        
        rol_combo_var = ctk.StringVar(value=list(rol_opciones.keys())[0])
        ctk.CTkOptionMenu(marco_formulario, values=list(rol_opciones.keys()), variable=rol_combo_var, width=280).pack(pady=6)

        pregunta_var = ctk.StringVar(value=PREGUNTAS_SECRETAS[0])
        ctk.CTkOptionMenu(marco_formulario, values=PREGUNTAS_SECRETAS, variable=pregunta_var, width=280).pack(pady=6)
        respuesta = ctk.CTkEntry(marco_formulario, placeholder_text="Respuesta secreta", width=280)
        respuesta.pack(pady=6)

        error = ctk.CTkLabel(marco_formulario, text="", text_color="red")
        error.pack(pady=2)
=======
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
>>>>>>> 7bd8bf5674ae67b1e45373b0b5fea840cc61ce72

        def intentar_registro():
            nombre = user.get().strip()
            clave = pwd.get()
<<<<<<< HEAD
            rol_seleccionado = rol_opciones[rol_combo_var.get()]
=======
>>>>>>> 7bd8bf5674ae67b1e45373b0b5fea840cc61ce72

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

<<<<<<< HEAD
            if logica_login.crear_usuario(nombre, clave, pregunta_var.get(), respuesta.get(), rol_seleccionado):
                error.configure(text="¡Éxito! Ya puedes iniciar sesión", text_color="green")
=======
            if logica_login.crear_usuario(nombre, clave, pregunta_var.get(), respuesta.get()):
                error.configure(text="¡Éxito! Inicia sesión", text_color="green")
>>>>>>> 7bd8bf5674ae67b1e45373b0b5fea840cc61ce72
                ventana.after(1500, mostrar_login)
            else:
                error.configure(text="No se pudo crear el usuario", text_color="red")

<<<<<<< HEAD
        ctk.CTkButton(marco_formulario, text="Registrarse", command=intentar_registro, width=280, fg_color="#27ae60").pack(pady=10)

    def mostrar_recuperar():
        limpiar_formulario()
        ctk.CTkLabel(marco_formulario, text="Recuperar Contraseña", font=("Arial", 16, "bold")).pack(pady=10)
        user = ctk.CTkEntry(marco_formulario, placeholder_text="Usuario", width=280)
=======
        ctk.CTkButton(marco_formulario, text="Registrarse", command=intentar_registro).pack(pady=15)

    def mostrar_recuperar():
        """Primer paso de la recuperación: pedimos el usuario y buscamos su pregunta secreta."""
        limpiar_formulario()
        ctk.CTkLabel(marco_formulario, text="Recuperar Contraseña", font=("Arial", 16, "bold")).pack(pady=10)
        user = ctk.CTkEntry(marco_formulario, placeholder_text="Usuario")
>>>>>>> 7bd8bf5674ae67b1e45373b0b5fea840cc61ce72
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

<<<<<<< HEAD
        ctk.CTkButton(marco_formulario, text="Buscar", command=buscar_pregunta, width=280).pack(pady=15)
=======
        ctk.CTkButton(marco_formulario, text="Buscar", command=buscar_pregunta).pack(pady=15)
>>>>>>> 7bd8bf5674ae67b1e45373b0b5fea840cc61ce72
        ctk.CTkButton(marco_formulario, text="Volver a Iniciar Sesión", fg_color="transparent",
                      text_color="#3b8ed0", hover=False, command=mostrar_login).pack(pady=5)

    def mostrar_responder_pregunta(nombre, pregunta):
<<<<<<< HEAD
        limpiar_formulario()
        ctk.CTkLabel(marco_formulario, text="Recuperar Contraseña", font=("Arial", 16, "bold")).pack(pady=10)
        ctk.CTkLabel(marco_formulario, text=pregunta, wraplength=280).pack(pady=5)
        respuesta = ctk.CTkEntry(marco_formulario, placeholder_text="Tu respuesta", width=280)
        respuesta.pack(pady=8)
        nueva_pwd = ctk.CTkEntry(marco_formulario, placeholder_text="Nueva contraseña", show="*", width=280)
        nueva_pwd.pack(pady=8)
=======
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
>>>>>>> 7bd8bf5674ae67b1e45373b0b5fea840cc61ce72

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

<<<<<<< HEAD
        ctk.CTkButton(marco_formulario, text="Cambiar Contraseña", command=confirmar_cambio, width=280, fg_color="#27ae60").pack(pady=15)

    ctk.CTkButton(marco_botones, text="Iniciar Sesión", command=mostrar_login, width=170).pack(side="left", padx=5)
    ctk.CTkButton(marco_botones, text="Registrarse", command=mostrar_registro, width=170).pack(side="left", padx=5)
=======
        ctk.CTkButton(marco_formulario, text="Cambiar Contraseña", command=confirmar_cambio).pack(pady=15)

    ctk.CTkButton(marco_botones, text="Iniciar Sesión", command=mostrar_login, width=150).pack(side="left", padx=10)
    ctk.CTkButton(marco_botones, text="Registrarse", command=mostrar_registro, width=150).pack(side="left", padx=10)
>>>>>>> 7bd8bf5674ae67b1e45373b0b5fea840cc61ce72

    mostrar_login()
    ventana.mainloop()

<<<<<<< HEAD
=======

>>>>>>> 7bd8bf5674ae67b1e45373b0b5fea840cc61ce72
if __name__ == "__main__":
    crear_pantalla_login()