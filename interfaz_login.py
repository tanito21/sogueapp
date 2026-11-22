import customtkinter as ctk
from datetime import datetime
from tkinter import messagebox
import random
import logica_login
from icono_sogue import poner_icono

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

usuario_actual = None
rol_actual = "completo"

PREGUNTAS_SECRETAS = [
    "¿Cuál es el nombre de tu primera mascota?",
    "¿Cuál es tu comida favorita?",
    "¿En qué ciudad naciste?",
]

# Consejos financieros rotativos para el inicio
CONSEJOS_FINANCIEROS = [
    "💡 Consejo: Intenta ahorrar al menos el 20% de tus ingresos mensuales para imprevistos.",
    "💡 Consejo: Revisa tus gastos pequeños diarios; los 'gastos hormiga' suman mucho al mes.",
    "💡 Consejo: Antes de realizar una compra grande, espera 48 horas para evitar compras impulsivas.",
    "💡 Consejo: Define presupuestos claros por categoría para mantener tus finanzas bajo control."
]

# colores según el estado de cada categoría (ok / precaucion / excedido)
COLOR_ESTADO = {"ok": "#10b981", "precaucion": "#f59e0b", "excedido": "#ef4444"}
ICONO_ESTADO = {"ok": "🟢", "precaucion": "🟡", "excedido": "🔴"}

fmt = logica_login.formatear_gs   # Gs. 1.500.000

logica_login.inicializar_db()

def cerrar_sesion(ventana):
    global usuario_actual, rol_actual
    usuario_actual = None
    rol_actual = "completo"
    ventana.destroy()
    crear_pantalla_login()

def texto_monto(valor):
    """monto para mostrar dentro de un campo de texto (sin decimales de más)."""
    return f"{valor:.2f}".rstrip("0").rstrip(".")

def abrir_app_principal():
    global usuario_actual, rol_actual
    rol_actual = logica_login.obtener_rol_usuario(usuario_actual)

    ventana_principal = ctk.CTk()
    ventana_principal.geometry("1040x720")
    ventana_principal.title(f"SogueApp - Panel Principal [{usuario_actual} | Rol: {rol_actual.upper()}]")
    poner_icono(ventana_principal)

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

    #ventanas auxiliares (formularios cortos)
    def _tomar_foco(dialogo):
        try:
            dialogo.grab_set()
            dialogo.focus_force()
        except Exception:
            pass

    def dialogo_formulario(titulo, campos, texto_boton, al_aceptar):
        """abre una ventana con campos. campos: (etiqueta, valor inicial, oculto, opciones o None).

        al_aceptar recibe la lista de valores y devuelve un texto de error, o None si salió bien.
        """
        dialogo = ctk.CTkToplevel(ventana_principal)
        dialogo.title(titulo)
        dialogo.geometry(f"400x{170 + 70 * len(campos)}")
        dialogo.transient(ventana_principal)
        poner_icono(dialogo)

        ctk.CTkLabel(dialogo, text=titulo, font=("Arial", 16, "bold")).pack(pady=(15, 8))
        lectores = []
        for etiqueta, inicial, oculto, opciones in campos:
            ctk.CTkLabel(dialogo, text=etiqueta, font=("Arial", 11)).pack(anchor="w", padx=30)
            if opciones:
                var = ctk.StringVar(value=inicial or opciones[0])
                ctk.CTkOptionMenu(dialogo, values=opciones, variable=var, width=340).pack(pady=(0, 8))
                lectores.append(var.get)
            else:
                entrada = ctk.CTkEntry(dialogo, width=340, show="*" if oculto else "")
                if inicial:
                    entrada.insert(0, inicial)
                entrada.pack(pady=(0, 8))
                lectores.append(entrada.get)

        etiqueta_error = ctk.CTkLabel(dialogo, text="", text_color="#ef4444", wraplength=340)
        etiqueta_error.pack(pady=2)

        def aceptar():
            motivo = al_aceptar([leer() for leer in lectores])
            if motivo:
                etiqueta_error.configure(text=motivo)
                return
            dialogo.destroy()

        ctk.CTkButton(dialogo, text=texto_boton, command=aceptar, width=340).pack(pady=8)
        dialogo.after(200, lambda: _tomar_foco(dialogo))

    def confirmar_reemplazo(padre=None):
        """si ya hay presupuesto, avisa antes de reemplazarlo."""
        if not logica_login.obtener_categorias(usuario_actual):
            return True
        return messagebox.askyesno(
            "Confirmar",
            "Ya tienes un presupuesto. Al generar uno nuevo se reemplaza el actual y se borran sus gastos.\n\n¿Continuar?",
            parent=padre or ventana_principal)

    #parte de inicio (con consejos y barra visual de gastos)
    def seccion_inicio():
        limpiar_contenido()
        ctk.CTkLabel(marco_contenido, text="🏠 Resumen y Panel General", font=("Arial", 22, "bold")).pack(pady=(10, 5), anchor="w")

        # Tarjeta de consejo financiero dinámico
        f_consejo = ctk.CTkFrame(marco_contenido, fg_color="#1f2937", corner_radius=8)
        f_consejo.pack(fill="x", pady=10, padx=5)
        consejo_elegido = random.choice(CONSEJOS_FINANCIEROS)
        ctk.CTkLabel(f_consejo, text=consejo_elegido, font=("Arial", 13), text_color="#38bdf8", wraplength=680).pack(padx=15, pady=12)

        # CU.09.01: resumen de categorías (los mismos datos alimentan tarjetas y barras)
        resumen = logica_login.consultar_resumen_categorias(usuario_actual)

        # Tarjetas con los totales
        if resumen["categorias"]:
            f_totales = ctk.CTkFrame(marco_contenido, fg_color="transparent")
            f_totales.pack(fill="x", padx=5)
            tarjetas = [
                ("Ingreso", resumen["ingreso"], "#38bdf8"),
                ("Presupuestado", resumen["total_presupuestado"], "#a78bfa"),
                ("Gastado", resumen["total_gastado"], "#f59e0b"),
                ("Disponible", resumen["total_disponible"],
                 "#ef4444" if resumen["total_disponible"] < 0 else "#10b981"),
            ]
            for columna, (titulo, valor, color) in enumerate(tarjetas):
                f_tarjeta = ctk.CTkFrame(f_totales, fg_color="#111827", corner_radius=8)
                f_tarjeta.grid(row=0, column=columna, padx=4, sticky="ew")
                f_totales.grid_columnconfigure(columna, weight=1)
                ctk.CTkLabel(f_tarjeta, text=titulo, font=("Arial", 11), text_color="gray").pack(pady=(8, 0))
                ctk.CTkLabel(f_tarjeta, text=fmt(valor), font=("Arial", 14, "bold"), text_color=color).pack(pady=(0, 8), padx=8)

        # Panel visual de resumen y barras
        ctk.CTkLabel(marco_contenido, text="📊 Estado General de Presupuestos y Gastos", font=("Arial", 16, "bold")).pack(pady=(15, 5), anchor="w")

        f_graficos = ctk.CTkScrollableFrame(marco_contenido, width=700, height=350, fg_color="transparent")
        f_graficos.pack(fill="both", expand=True, pady=5)

        if not resumen["categorias"]:
            ctk.CTkLabel(f_graficos, text="No hay presupuestos generados todavía. Ve a la sección 'Presupuesto' para crear uno.", text_color="gray").pack(pady=20)
        else:
            for c in resumen["categorias"]:
                f_item = ctk.CTkFrame(f_graficos, fg_color="#111827", corner_radius=6)
                f_item.pack(fill="x", pady=6, padx=5)

                ctk.CTkLabel(f_item, text=f"📂 {c['nombre']}", font=("Arial", 13, "bold")).pack(side="top", anchor="w", padx=12, pady=(8, 2))

                # Cálculo de porcentaje para la barra visual (la barra no pasa de 100%)
                porcentaje = min(c["porcentaje"], 1.0)

                info_txt = (f"Presupuesto: {fmt(c['presupuesto'])} | Gastado: {fmt(c['gastado'])} | "
                            f"Saldo: {fmt(c['disponible'])} | Uso: {c['porcentaje'] * 100:.0f}%")
                ctk.CTkLabel(f_item, text=info_txt, font=("Arial", 11), text_color="gray").pack(side="top", anchor="w", padx=12, pady=(0, 4))

                # Barra de progreso visual CustomTkinter
                barra = ctk.CTkProgressBar(f_item, width=650, height=12)
                barra.pack(side="top", padx=12, pady=(0, 10))
                barra.set(porcentaje)

                # Color dinámico: verde saludable, amarillo precaución, rojo si excede el presupuesto
                barra.configure(progress_color=COLOR_ESTADO[c["estado"]])

    #presupuestos (Funcionalidad Principal)
    def seccion_presupuesto():
        limpiar_contenido()
        cuerpo = ctk.CTkScrollableFrame(marco_contenido, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True)

        ctk.CTkLabel(cuerpo, text="📊 Gestión de Presupuestos", font=("Arial", 22, "bold")).pack(pady=(10, 5), anchor="w")
        ctk.CTkLabel(cuerpo, text="Genera tu base de ingresos y distribuye tus límites por categoría.", font=("Arial", 12), text_color="gray").pack(anchor="w", pady=(0, 10))

        # --- generar presupuesto con un método predeterminado o personalizado ---
        f_gen = ctk.CTkFrame(cuerpo)
        f_gen.pack(fill="x", pady=(5, 0))

        ent_ingreso = ctk.CTkEntry(f_gen, placeholder_text="Ingreso mensual total (Gs.)", width=200)
        ent_ingreso.pack(side="left", padx=10, pady=12)

        metodos = list(logica_login.PLANTILLAS_PRESUPUESTO) + [logica_login.METODO_PERSONALIZADO]
        metodo_var = ctk.StringVar(value=logica_login.METODO_POR_DEFECTO)

        lbl_plantilla = ctk.CTkLabel(cuerpo, text=logica_login.describir_plantilla(metodo_var.get()),
                                     font=("Arial", 11), text_color="#38bdf8", wraplength=680, justify="left")

        def al_cambiar_metodo(valor):
            lbl_plantilla.configure(text=logica_login.describir_plantilla(valor))
            boton_generar.configure(text="Elegir porcentajes..." if valor == logica_login.METODO_PERSONALIZADO
                                    else "Generar Presupuesto")

        ctk.CTkOptionMenu(f_gen, values=metodos, variable=metodo_var, command=al_cambiar_metodo, width=150).pack(side="left", padx=10)

        def generar_base():
            # primero validamos el ingreso, así no preguntamos por algo que va a fallar
            if logica_login.convertir_monto(ent_ingreso.get()) is None:
                messagebox.showerror("Error", "Ingrese un valor numérico válido mayor a 0.")
                return

            metodo = metodo_var.get()
            if metodo == logica_login.METODO_PERSONALIZADO:
                editor_porcentajes(ent_ingreso.get())
                return

            if not confirmar_reemplazo():
                return

            if not logica_login.generar_presupuesto(usuario_actual, ent_ingreso.get(), metodo):
                messagebox.showerror("Error", "No se pudo generar el presupuesto.")
                return

            messagebox.showinfo("Éxito", f"¡Presupuesto generado con éxito bajo el método {metodo}!")
            seccion_presupuesto()

        boton_generar = ctk.CTkButton(f_gen, text="Generar Presupuesto", command=generar_base, fg_color="#2c82c9")
        boton_generar.pack(side="left", padx=10)
        lbl_plantilla.pack(anchor="w", padx=5, pady=(4, 8))

        # --- ingreso actual y lo que queda por asignar ---
        resumen = logica_login.consultar_resumen_categorias(usuario_actual)
        if logica_login.obtener_ingreso(usuario_actual) is not None:
            f_ing = ctk.CTkFrame(cuerpo, fg_color="#1f2937")
            f_ing.pack(fill="x", pady=8)
            ctk.CTkLabel(
                f_ing, font=("Arial", 12), justify="left",
                text=(f"💵 Ingreso: {fmt(resumen['ingreso'])}   |   Asignado: {fmt(resumen['total_presupuestado'])}"
                      f"   |   Sin asignar: {fmt(resumen['sin_asignar'])}")
            ).pack(anchor="w", padx=12, pady=(10, 4))

            f_nuevo = ctk.CTkFrame(f_ing, fg_color="transparent")
            f_nuevo.pack(anchor="w", padx=8, pady=(0, 10))
            ent_nuevo_ingreso = ctk.CTkEntry(f_nuevo, placeholder_text="Nuevo ingreso (Gs.)", width=200)
            ent_nuevo_ingreso.pack(side="left", padx=4)

            def actualizar_ingreso():
                ok, motivo = logica_login.cambiar_ingreso(usuario_actual, ent_nuevo_ingreso.get())
                if not ok:
                    messagebox.showerror("Error", motivo)
                    return
                seccion_presupuesto()

            ctk.CTkButton(f_nuevo, text="Actualizar ingreso", command=actualizar_ingreso, width=140).pack(side="left", padx=4)

        # --- categorías: agregar, editar y eliminar ---
        cats_db = logica_login.obtener_categorias(usuario_actual)
        nombres = [c[0] for c in cats_db]

        ctk.CTkLabel(cuerpo, text="🗂️ Mis categorías", font=("Arial", 16, "bold")).pack(anchor="w", pady=(12, 4))
        f_cat = ctk.CTkFrame(cuerpo)
        f_cat.pack(fill="x", pady=4)

        def agregar():
            def al_aceptar(valores):
                ok, motivo = logica_login.agregar_categoria(usuario_actual, valores[0], valores[1])
                if not ok:
                    return motivo
                seccion_presupuesto()
                return None
            dialogo_formulario("Agregar categoría",
                               [("Nombre (ej: Streaming, Movilidad)", "", False, None),
                                ("Monto asignado (Gs.)", "", False, None)],
                               "Agregar", al_aceptar)

        def editar():
            if not nombres:
                return
            nombre = sel_var.get()
            actual = next((c for c in cats_db if c[0] == nombre), None)
            if actual is None:
                return

            def al_aceptar(valores):
                ok, motivo = logica_login.editar_categoria(usuario_actual, nombre, valores[0], valores[1])
                if not ok:
                    return motivo
                seccion_presupuesto()
                return None
            dialogo_formulario(f"Editar «{nombre}»",
                               [("Nombre", nombre, False, None),
                                ("Monto asignado (Gs.)", texto_monto(actual[1]), False, None)],
                               "Guardar cambios", al_aceptar)

        def eliminar():
            if not nombres:
                return
            nombre = sel_var.get()
            if not messagebox.askyesno("Confirmar", f"Se eliminará «{nombre}» y todos los gastos registrados en ella.\n\n¿Continuar?"):
                return
            ok, motivo = logica_login.eliminar_categoria(usuario_actual, nombre)
            if not ok:
                messagebox.showerror("Error", motivo)
                return
            seccion_presupuesto()

        ctk.CTkButton(f_cat, text="➕ Agregar categoría", command=agregar, fg_color="#27ae60", width=160).pack(side="left", padx=10, pady=12)
        sel_var = ctk.StringVar(value=nombres[0] if nombres else "(sin categorías)")
        ctk.CTkOptionMenu(f_cat, values=nombres or ["(sin categorías)"], variable=sel_var, width=170).pack(side="left", padx=6)
        ctk.CTkButton(f_cat, text="✏️ Editar", command=editar, width=90).pack(side="left", padx=6)
        ctk.CTkButton(f_cat, text="🗑️ Eliminar", command=eliminar, fg_color="#d9534f", width=100).pack(side="left", padx=6)

        # --- detalle: presupuesto, gastado y disponible de cada categoría ---
        caja_p = ctk.CTkTextbox(cuerpo, font=("Courier New", 12), width=720, height=300)
        caja_p.pack(fill="x", pady=10)

        if not resumen["categorias"]:
            caja_p.insert("end", "ℹ️ Todavía no hay categorías generadas. Ingresa un monto arriba y haz clic en 'Generar Presupuesto'.\n")
        else:
            for c in resumen["categorias"]:
                caja_p.insert("end", f"{ICONO_ESTADO[c['estado']]} Categoría: {c['nombre']}\n 💰 Presupuesto: {fmt(c['presupuesto'])}\n 📉 Gastado: {fmt(c['gastado'])}\n 💳 Disponible: {fmt(c['disponible'])}\n\n")
        caja_p.configure(state="disabled")

    def editor_porcentajes(ingreso_texto):
        """ventana para armar un presupuesto con las categorías y porcentajes que el usuario quiera."""
        dialogo = ctk.CTkToplevel(ventana_principal)
        dialogo.title("Presupuesto personalizado")
        dialogo.geometry("470x580")
        dialogo.transient(ventana_principal)
        poner_icono(dialogo)

        ctk.CTkLabel(dialogo, text="Distribuí tu ingreso en categorías (los porcentajes deben sumar 100%)",
                     font=("Arial", 13, "bold"), wraplength=420).pack(pady=(15, 8))
        marco_filas = ctk.CTkScrollableFrame(dialogo, width=410, height=290)
        marco_filas.pack(padx=15)

        filas = []
        lbl_total = ctk.CTkLabel(dialogo, text="Total: 0%", font=("Arial", 13, "bold"))
        lbl_error = ctk.CTkLabel(dialogo, text="", text_color="#ef4444", wraplength=420)

        def recalcular(_evento=None):
            total = 0.0
            for entrada_nombre, entrada_pct, _marco in filas:
                valor = logica_login.convertir_porcentaje(entrada_pct.get())
                if valor:
                    total += valor
            total = round(total, 2)
            completo = abs(total - 100) <= logica_login.TOLERANCIA
            resto = round(100 - total, 2)
            lbl_total.configure(
                text=f"Total: {total:g}%   ({'completo' if completo else f'faltan {resto:g}%'})",
                text_color="#10b981" if completo else "#f59e0b")

        def agregar_fila(nombre="", porcentaje=""):
            marco = ctk.CTkFrame(marco_filas, fg_color="transparent")
            marco.pack(fill="x", pady=3)
            entrada_nombre = ctk.CTkEntry(marco, placeholder_text="Categoría", width=220)
            entrada_nombre.pack(side="left", padx=(0, 6))
            entrada_pct = ctk.CTkEntry(marco, placeholder_text="%", width=70)
            entrada_pct.pack(side="left", padx=(0, 6))
            entrada_pct.bind("<KeyRelease>", recalcular)
            fila = (entrada_nombre, entrada_pct, marco)

            def quitar():
                filas.remove(fila)
                marco.destroy()
                recalcular()

            ctk.CTkButton(marco, text="✕", width=30, fg_color="#d9534f", command=quitar).pack(side="left")
            if nombre:
                entrada_nombre.insert(0, nombre)
            if porcentaje:
                entrada_pct.insert(0, str(porcentaje))
            filas.append(fila)
            recalcular()

        # arrancamos con las tres principales, el usuario las cambia como quiera
        for nombre, porcentaje in logica_login.PLANTILLAS_PRESUPUESTO["Básico"]:
            agregar_fila(nombre, porcentaje)

        ctk.CTkButton(dialogo, text="➕ Agregar otra categoría", command=agregar_fila, width=200,
                      fg_color="transparent", border_width=1).pack(pady=(10, 4))
        lbl_total.pack(pady=2)
        lbl_error.pack(pady=2)

        def confirmar():
            reparto = [(en.get(), ep.get()) for en, ep, _ in filas]
            ok, motivo, _ = logica_login.validar_distribucion(reparto)
            if not ok:
                lbl_error.configure(text=motivo)
                return
            if not confirmar_reemplazo(dialogo):
                return
            if not logica_login.generar_presupuesto(usuario_actual, ingreso_texto,
                                                    logica_login.METODO_PERSONALIZADO, reparto):
                lbl_error.configure(text="No se pudo generar el presupuesto.")
                return
            dialogo.destroy()
            messagebox.showinfo("Éxito", "¡Presupuesto personalizado generado con éxito!")
            seccion_presupuesto()

        ctk.CTkButton(dialogo, text="Generar presupuesto", command=confirmar, fg_color="#27ae60", width=240).pack(pady=8)
        dialogo.after(200, lambda: _tomar_foco(dialogo))

    #gastos (Módulo 4: registro de transacciones)
    def seccion_gastos(categoria_inicial=None):
        limpiar_contenido()
        ctk.CTkLabel(marco_contenido, text="💸 Registro de Gastos", font=("Arial", 22, "bold")).pack(pady=(10, 5), anchor="w")
        ctk.CTkLabel(marco_contenido, text="Elegí una categoría, mirá cuánto te queda y anotá en qué gastaste.",
                     font=("Arial", 12), text_color="gray").pack(anchor="w", pady=(0, 10))

        # CU.08.01: categorías activas del usuario
        activas = logica_login.consultar_categorias_activas(usuario_actual)
        if not activas:
            f_aviso = ctk.CTkFrame(marco_contenido, fg_color="#1f2937")
            f_aviso.pack(fill="x", padx=5, pady=20)
            ctk.CTkLabel(f_aviso, text="Todavía no tenés categorías.\nGenerá tu presupuesto en la sección 'Presupuesto' para poder registrar gastos.",
                         font=("Arial", 13), text_color="gray").pack(pady=40)
            return

        nombres = [a[0] for a in activas]
        cat_var = ctk.StringVar(value=categoria_inicial if categoria_inicial in nombres else nombres[0])

        # saldo de la categoría elegida
        lbl_saldo = ctk.CTkLabel(marco_contenido, text="", font=("Arial", 14, "bold"))

        def mostrar_saldo(*_):
            for nombre, presupuesto, gastado, disponible in activas:
                if nombre == cat_var.get():
                    lbl_saldo.configure(
                        text=(f"Presupuesto: {fmt(presupuesto)}   |   Gastado: {fmt(gastado)}   |   "
                              f"Disponible: {fmt(disponible)}"),
                        text_color="#ef4444" if disponible < 0 else "#10b981")

        # CU.08.02: detalle del gasto
        f_form = ctk.CTkFrame(marco_contenido)
        f_form.pack(fill="x", padx=5, pady=5)
        ctk.CTkOptionMenu(f_form, values=nombres, variable=cat_var, command=mostrar_saldo, width=190).grid(row=0, column=0, padx=10, pady=15)
        ent_concepto = ctk.CTkEntry(f_form, placeholder_text="¿En qué gastaste? (ej: McDonalds)", width=260)
        ent_concepto.grid(row=0, column=1, padx=6)
        ent_monto = ctk.CTkEntry(f_form, placeholder_text="Monto gastado (Gs.)", width=160)
        ent_monto.grid(row=0, column=2, padx=6)

        def registrar():
            resultado = logica_login.registrar_gasto(usuario_actual, cat_var.get(), ent_concepto.get(), ent_monto.get())
            if not resultado["ok"]:
                messagebox.showerror("Error", resultado["motivo"])
                return
            detalle = (f"Gasto registrado en {resultado['categoria']}.\n\n"
                       f"Gastado: {fmt(resultado['gastado'])}\n"
                       f"Disponible: {fmt(resultado['disponible'])}")
            # CU.08.04: alerta si se pasó del límite
            if resultado["alerta"]:
                messagebox.showwarning("Límite superado", f"{resultado['alerta']}\n\n{detalle}")
            else:
                messagebox.showinfo("Gasto registrado", detalle)
            seccion_gastos(resultado["categoria"])

        ctk.CTkButton(f_form, text="Registrar Gasto", command=registrar, fg_color="#d9534f", width=130).grid(row=0, column=3, padx=10)
        lbl_saldo.pack(anchor="w", padx=10, pady=(8, 4))
        mostrar_saldo()

        # últimos movimientos
        ctk.CTkLabel(marco_contenido, text="🕑 Últimos gastos registrados", font=("Arial", 16, "bold")).pack(anchor="w", pady=(15, 5))
        f_hist = ctk.CTkScrollableFrame(marco_contenido, fg_color="transparent", height=260)
        f_hist.pack(fill="both", expand=True)
        historial = logica_login.consultar_historial_reciente(usuario_actual, 5)
        if not historial:
            ctk.CTkLabel(f_hist, text="Todavía no registraste gastos.", text_color="gray").pack(pady=15)
        for fecha, categoria, concepto, monto in historial:
            f_fila = ctk.CTkFrame(f_hist, fg_color="#111827", corner_radius=6)
            f_fila.pack(fill="x", pady=4, padx=5)
            ctk.CTkLabel(f_fila, text=f"{concepto}  →  {fmt(monto)}", font=("Arial", 13, "bold")).pack(anchor="w", padx=12, pady=(8, 0))
            ctk.CTkLabel(f_fila, text=f"{fecha}  |  {categoria}", font=("Arial", 11), text_color="gray").pack(anchor="w", padx=12, pady=(0, 8))

        mostrar_saldo()

    #reportes (Módulo 5: dashboard y reportes)
    def seccion_reportes(limite=10):
        limpiar_contenido()
        ctk.CTkLabel(marco_contenido, text="📈 Dashboard y Reportes", font=("Arial", 22, "bold")).pack(pady=(10, 5), anchor="w")

        f_barra = ctk.CTkFrame(marco_contenido, fg_color="transparent")
        f_barra.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(f_barra, text="Movimientos a mostrar:", font=("Arial", 12)).pack(side="left", padx=(0, 8))
        opciones = ["10", "25", "50"]
        limite_var = ctk.StringVar(value=str(limite) if str(limite) in opciones else "10")
        ctk.CTkOptionMenu(f_barra, values=opciones, variable=limite_var, width=80,
                          command=lambda valor: seccion_reportes(int(valor))).pack(side="left")

        caja = ctk.CTkTextbox(marco_contenido, font=("Courier New", 12))
        caja.pack(fill="both", expand=True, pady=5)

        # CU.09.01: resumen de categorías
        resumen = logica_login.consultar_resumen_categorias(usuario_actual)
        caja.insert("end", "=== RESUMEN POR CATEGORÍA ===\n\n")
        if not resumen["categorias"]:
            caja.insert("end", "Todavía no hay categorías. Generá tu presupuesto en la sección 'Presupuesto'.\n")
        else:
            caja.insert("end", f"{'Categoría':<22} {'Presupuesto':>15} {'Gastado':>15} {'Disponible':>15}  Uso\n")
            caja.insert("end", "-" * 78 + "\n")
            for c in resumen["categorias"]:
                caja.insert("end", (f"{c['nombre'][:22]:<22} {fmt(c['presupuesto']):>15} {fmt(c['gastado']):>15} "
                                    f"{fmt(c['disponible']):>15} {c['porcentaje'] * 100:>3.0f}% {ICONO_ESTADO[c['estado']]}\n"))
            caja.insert("end", "-" * 78 + "\n")
            caja.insert("end", (f"{'TOTAL':<22} {fmt(resumen['total_presupuestado']):>15} {fmt(resumen['total_gastado']):>15} "
                                f"{fmt(resumen['total_disponible']):>15} {resumen['porcentaje_usado'] * 100:>3.0f}%\n"))
            caja.insert("end", f"\nIngreso: {fmt(resumen['ingreso'])}   |   Sin asignar: {fmt(resumen['sin_asignar'])}\n")

        # CU.09.02: historial reciente
        cantidad = int(limite_var.get())
        caja.insert("end", f"\n\n=== HISTORIAL DE GASTOS RECIENTES (ÚLTIMOS {cantidad}) ===\n\n")
        historial = logica_login.consultar_historial_reciente(usuario_actual, cantidad)
        if not historial:
            caja.insert("end", "Todavía no registraste gastos.\n")
        for fecha, categoria, concepto, monto in historial:
            caja.insert("end", f"{fecha}  {categoria[:18]:<18}  {concepto[:28]:<28} {fmt(monto):>15}\n")
        caja.configure(state="disabled")

    #metas de ahorro: crear, editar, eliminar y agregar dinero
    def seccion_ahorros(meta_inicial=None):
        limpiar_contenido()
        cuerpo = ctk.CTkScrollableFrame(marco_contenido, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True)

        ctk.CTkLabel(cuerpo, text="🎯 Metas de Ahorro", font=("Arial", 22, "bold")).pack(pady=(10, 5), anchor="w")
        ctk.CTkLabel(cuerpo, text="Creá tus metas, sumales dinero y seguí cuánto te falta para completarlas.",
                     font=("Arial", 12), text_color="gray").pack(anchor="w", pady=(0, 10))

        resumen = logica_login.consultar_resumen_ahorros(usuario_actual)
        metas = resumen["metas"]
        nombres = [m["nombre"] for m in metas]

        # Tarjetas con los totales
        if metas:
            f_totales = ctk.CTkFrame(cuerpo, fg_color="transparent")
            f_totales.pack(fill="x", padx=5)
            tarjetas = [
                ("Total ahorrado", fmt(resumen["total_ahorrado"]), "#10b981"),
                ("Total objetivo", fmt(resumen["total_objetivo"]), "#a78bfa"),
                ("Falta ahorrar", fmt(resumen["total_faltante"]), "#f59e0b"),
                ("Completado", f"{resumen['porcentaje_total'] * 100:.0f}%  ({resumen['completadas']}/{resumen['cantidad']} metas)", "#38bdf8"),
            ]
            for columna, (titulo, valor, color) in enumerate(tarjetas):
                f_tarjeta = ctk.CTkFrame(f_totales, fg_color="#111827", corner_radius=8)
                f_tarjeta.grid(row=0, column=columna, padx=4, sticky="ew")
                f_totales.grid_columnconfigure(columna, weight=1)
                ctk.CTkLabel(f_tarjeta, text=titulo, font=("Arial", 11), text_color="gray").pack(pady=(8, 0))
                ctk.CTkLabel(f_tarjeta, text=valor, font=("Arial", 13, "bold"), text_color=color).pack(pady=(0, 8), padx=8)

        # Acciones: nueva meta, y editar / agregar dinero / eliminar sobre la meta elegida
        def nueva_meta():
            def al_aceptar(valores):
                ok, motivo = logica_login.crear_meta(usuario_actual, valores[0], valores[1], valores[2])
                if not ok:
                    return motivo
                seccion_ahorros(" ".join(valores[0].split()))
                return None
            dialogo_formulario("Nueva meta de ahorro",
                               [("Nombre (ej: Viaje, Celular nuevo)", "", False, None),
                                ("Monto objetivo (Gs.)", "", False, None),
                                ("Fecha límite (dd/mm/aaaa, opcional)", "", False, None)],
                               "Crear meta", al_aceptar)

        def meta_elegida():
            return next((m for m in metas if m["nombre"] == sel_var.get()), None)

        def agregar_dinero():
            meta = meta_elegida()
            if meta is None:
                return

            def al_aceptar(valores):
                resultado = logica_login.agregar_aporte(usuario_actual, meta["nombre"], valores[0], valores[1])
                if not resultado["ok"]:
                    return resultado["motivo"]
                detalle = (f"Meta: {resultado['nombre']}\n\n"
                           f"Ahorrado: {fmt(resultado['ahorrado'])} de {fmt(resultado['objetivo'])}\n"
                           f"Falta: {fmt(resultado['faltante'])}\n"
                           f"Completado: {resultado['porcentaje'] * 100:.0f}%")
                if resultado["recien_completada"]:
                    messagebox.showinfo("¡Meta cumplida! 🎉", f"¡Llegaste al objetivo!\n\n{detalle}")
                else:
                    messagebox.showinfo("Aporte registrado", detalle)
                seccion_ahorros(resultado["nombre"])
                return None
            dialogo_formulario(f"Agregar dinero a «{meta['nombre']}»",
                               [("Monto a ahorrar (Gs.)", "", False, None),
                                ("Nota (opcional)", "", False, None)],
                               "Agregar dinero", al_aceptar)

        def editar_meta():
            meta = meta_elegida()
            if meta is None:
                return

            def al_aceptar(valores):
                ok, motivo = logica_login.editar_meta(usuario_actual, meta["nombre"], valores[0], valores[1], valores[2])
                if not ok:
                    return motivo
                seccion_ahorros(" ".join(valores[0].split()))
                return None
            dialogo_formulario(f"Editar «{meta['nombre']}»",
                               [("Nombre", meta["nombre"], False, None),
                                ("Monto objetivo (Gs.)", texto_monto(meta["objetivo"]), False, None),
                                ("Fecha límite (dd/mm/aaaa, vacío para quitarla)", meta["fecha_limite"] or "", False, None)],
                               "Guardar cambios", al_aceptar)

        def eliminar_meta():
            meta = meta_elegida()
            if meta is None:
                return
            if not messagebox.askyesno("Confirmar", f"Se eliminará «{meta['nombre']}» con todos sus aportes.\n\n¿Continuar?"):
                return
            ok, motivo = logica_login.eliminar_meta(usuario_actual, meta["nombre"])
            if not ok:
                messagebox.showerror("Error", motivo)
                return
            seccion_ahorros()

        f_acc = ctk.CTkFrame(cuerpo)
        f_acc.pack(fill="x", pady=10, padx=5)
        ctk.CTkButton(f_acc, text="➕ Nueva meta", command=nueva_meta, fg_color="#27ae60", width=130).pack(side="left", padx=10, pady=12)
        sel_var = ctk.StringVar(value=meta_inicial if meta_inicial in nombres else (nombres[0] if nombres else "(sin metas)"))
        ctk.CTkOptionMenu(f_acc, values=nombres or ["(sin metas)"], variable=sel_var, width=170).pack(side="left", padx=6)
        ctk.CTkButton(f_acc, text="💰 Agregar dinero", command=agregar_dinero, fg_color="#2c82c9", width=140).pack(side="left", padx=6)
        ctk.CTkButton(f_acc, text="✏️ Editar", command=editar_meta, width=85).pack(side="left", padx=6)
        ctk.CTkButton(f_acc, text="🗑️ Eliminar", command=eliminar_meta, fg_color="#d9534f", width=95).pack(side="left", padx=6)

        # Detalle de cada meta con su barra de progreso
        ctk.CTkLabel(cuerpo, text="📋 Mis metas", font=("Arial", 16, "bold")).pack(anchor="w", pady=(6, 4))
        if not metas:
            f_vacio = ctk.CTkFrame(cuerpo, fg_color="#1f2937")
            f_vacio.pack(fill="x", padx=5, pady=5)
            ctk.CTkLabel(f_vacio, text="Todavía no tenés metas de ahorro.\nHacé clic en 'Nueva meta' para crear la primera.",
                         font=("Arial", 13), text_color="gray").pack(pady=30)

        icono_meta = {"completada": "✅", "vencida": "⏰", "en_curso": "🎯"}
        color_meta = {"completada": "#10b981", "vencida": "#ef4444", "en_curso": "#38bdf8"}
        for m in metas:
            f_item = ctk.CTkFrame(cuerpo, fg_color="#111827", corner_radius=6)
            f_item.pack(fill="x", pady=6, padx=5)
            ctk.CTkLabel(f_item, text=f"{icono_meta[m['estado']]} {m['nombre']}", font=("Arial", 13, "bold")).pack(anchor="w", padx=12, pady=(8, 2))

            info = (f"Ahorrado: {fmt(m['ahorrado'])} de {fmt(m['objetivo'])}  |  "
                    f"Falta: {fmt(m['faltante'])}  |  Completado: {m['porcentaje'] * 100:.0f}%")
            ctk.CTkLabel(f_item, text=info, font=("Arial", 11), text_color="gray").pack(anchor="w", padx=12, pady=(0, 2))

            if m["fecha_limite"]:
                dias = m["dias_restantes"]
                if m["completada"]:
                    texto_fecha = f"Fecha límite: {m['fecha_limite']}"
                elif dias is not None and dias < 0:
                    texto_fecha = f"Fecha límite: {m['fecha_limite']} (venció hace {-dias} días)"
                elif dias == 0:
                    texto_fecha = f"Fecha límite: {m['fecha_limite']} (¡vence hoy!)"
                else:
                    texto_fecha = f"Fecha límite: {m['fecha_limite']} (faltan {dias} días)"
                ctk.CTkLabel(f_item, text=texto_fecha, font=("Arial", 11), text_color="gray").pack(anchor="w", padx=12, pady=(0, 4))

            barra = ctk.CTkProgressBar(f_item, width=650, height=12, progress_color=color_meta[m["estado"]])
            barra.pack(padx=12, pady=(2, 10))
            barra.set(min(m["porcentaje"], 1.0))

        # Últimos aportes
        ctk.CTkLabel(cuerpo, text="🕑 Últimos aportes", font=("Arial", 16, "bold")).pack(anchor="w", pady=(12, 4))
        aportes = logica_login.consultar_aportes_recientes(usuario_actual, 8)
        if not aportes:
            ctk.CTkLabel(cuerpo, text="Todavía no hiciste aportes.", text_color="gray").pack(pady=10)
        for fecha, meta_nombre, monto, nota in aportes:
            f_fila = ctk.CTkFrame(cuerpo, fg_color="#111827", corner_radius=6)
            f_fila.pack(fill="x", pady=4, padx=5)
            ctk.CTkLabel(f_fila, text=f"+ {fmt(monto)}  →  {meta_nombre}", font=("Arial", 13, "bold"), text_color="#10b981").pack(anchor="w", padx=12, pady=(8, 0))
            ctk.CTkLabel(f_fila, text=f"{fecha}" + (f"  |  {nota}" if nota else ""), font=("Arial", 11), text_color="gray").pack(anchor="w", padx=12, pady=(0, 8))

    #administración (solo rol admin): gestiona las cuentas del sistema
    def seccion_admin():
        limpiar_contenido()
        ctk.CTkLabel(marco_contenido, text="🛡️ Administración de usuarios", font=("Arial", 22, "bold")).pack(pady=(10, 5), anchor="w")
        ctk.CTkLabel(marco_contenido, font=("Arial", 12), text_color="gray", wraplength=720, justify="left",
                     text="Como administrador podés cambiar roles, restablecer contraseñas, eliminar cuentas con todos sus datos y crear otros administradores."
                     ).pack(anchor="w", pady=(0, 10))

        cuentas = logica_login.obtener_resumen_usuarios(usuario_actual) or []

        # tarjetas con totales del sistema
        f_totales = ctk.CTkFrame(marco_contenido, fg_color="transparent")
        f_totales.pack(fill="x", padx=5)
        datos = [
            ("Usuarios", str(len(cuentas))),
            ("Administradores", str(sum(1 for c in cuentas if c[2] == "admin"))),
            ("Presupuestado", fmt(sum(c[4] for c in cuentas))),
            ("Gastado", fmt(sum(c[5] for c in cuentas))),
        ]
        for columna, (titulo, valor) in enumerate(datos):
            f_tarjeta = ctk.CTkFrame(f_totales, fg_color="#111827", corner_radius=8)
            f_tarjeta.grid(row=0, column=columna, padx=4, sticky="ew")
            f_totales.grid_columnconfigure(columna, weight=1)
            ctk.CTkLabel(f_tarjeta, text=titulo, font=("Arial", 11), text_color="gray").pack(pady=(8, 0))
            ctk.CTkLabel(f_tarjeta, text=valor, font=("Arial", 14, "bold"), text_color="#38bdf8").pack(pady=(0, 8), padx=8)

        def crear_admin():
            def al_aceptar(valores):
                nombre, clave, pregunta, respuesta = (v.strip() if i != 1 else v for i, v in enumerate(valores))
                if not nombre or not clave or not respuesta:
                    return "Completa todos los datos"
                if logica_login.usuario_existe(nombre):
                    return "El usuario ya existe"
                clave_ok, motivo = logica_login.clave_es_segura(clave)
                if not clave_ok:
                    return motivo
                if not logica_login.crear_usuario(nombre, clave, pregunta, respuesta, "admin", creado_por=usuario_actual):
                    return "No se pudo crear el administrador"
                seccion_admin()
                return None
            dialogo_formulario("Crear administrador",
                               [("Usuario", "", False, None),
                                ("Contraseña (mín. 8 carac., 1 mayús., 1 núm.)", "", True, None),
                                ("Pregunta secreta", PREGUNTAS_SECRETAS[0], False, PREGUNTAS_SECRETAS),
                                ("Respuesta secreta", "", False, None)],
                               "Crear administrador", al_aceptar)

        ctk.CTkButton(marco_contenido, text="➕ Crear administrador", command=crear_admin, fg_color="#27ae60", width=200).pack(anchor="w", padx=5, pady=10)

        def cambiar_rol(nombre, rol):
            def al_aceptar(valores):
                ok, motivo = logica_login.cambiar_rol_usuario(usuario_actual, nombre, valores[0])
                if not ok:
                    return motivo
                seccion_admin()
                return None
            dialogo_formulario(f"Cambiar rol de {nombre}",
                               [("Nuevo rol", rol, False, list(logica_login.ROLES_VALIDOS))],
                               "Guardar", al_aceptar)

        def restablecer(nombre):
            def al_aceptar(valores):
                ok, motivo = logica_login.restablecer_clave_usuario(usuario_actual, nombre, valores[0])
                if not ok:
                    return motivo
                messagebox.showinfo("Contraseña actualizada", f"Se cambió la contraseña de {nombre}.")
                return None
            dialogo_formulario(f"Nueva contraseña para {nombre}",
                               [("Contraseña (mín. 8 carac., 1 mayús., 1 núm.)", "", True, None)],
                               "Cambiar contraseña", al_aceptar)

        def eliminar(nombre):
            if not messagebox.askyesno("Confirmar", f"Se eliminará a «{nombre}» con su presupuesto y sus gastos. Esta acción no se puede deshacer.\n\n¿Continuar?"):
                return
            ok, motivo = logica_login.eliminar_usuario(usuario_actual, nombre)
            if not ok:
                messagebox.showerror("Error", motivo)
                return
            seccion_admin()

        f_lista = ctk.CTkScrollableFrame(marco_contenido, fg_color="transparent")
        f_lista.pack(fill="both", expand=True, pady=5)
        for _id, nombre, rol, cantidad, presupuesto, gastado in cuentas:
            es_propia = nombre.lower() == usuario_actual.lower()
            f_fila = ctk.CTkFrame(f_lista, fg_color="#111827", corner_radius=6)
            f_fila.pack(fill="x", pady=4, padx=5)
            ctk.CTkLabel(
                f_fila, justify="left", anchor="w",
                text=(f"👤 {nombre}  [{rol}]" + ("  (vos)" if es_propia else "") +
                      f"\n{cantidad} categorías · Presupuesto {fmt(presupuesto)} · Gastado {fmt(gastado)}"),
                font=("Arial", 12)).pack(side="left", padx=12, pady=8)
            ctk.CTkButton(f_fila, text="Eliminar", width=75, fg_color="#d9534f", state="disabled" if es_propia else "normal",
                          command=lambda n=nombre: eliminar(n)).pack(side="right", padx=(4, 10))
            ctk.CTkButton(f_fila, text="Clave", width=65, command=lambda n=nombre: restablecer(n)).pack(side="right", padx=4)
            ctk.CTkButton(f_fila, text="Rol", width=55, state="disabled" if es_propia else "normal",
                          command=lambda n=nombre, r=rol: cambiar_rol(n, r)).pack(side="right", padx=4)

    # Construcción de la barra lateral según los permisos y el orden solicitado (Presupuesto antes de Gastos)
    secciones = []
    if rol_actual in ["admin", "completo", "presupuesto"]:
        secciones.append(("🏠 Inicio", seccion_inicio))
        secciones.append(("📊 Presupuesto", seccion_presupuesto))
        secciones.append(("💸 Gastos", seccion_gastos))
        secciones.append(("📈 Reportes", seccion_reportes))
    if rol_actual in ["admin", "completo", "ahorro"]:
        secciones.append(("🎯 Ahorros", seccion_ahorros))
    if rol_actual == "admin":
        secciones.append(("🛡️ Administración", seccion_admin))

    for texto_boton, funcion_seccion in secciones:
        ctk.CTkButton(barra_lateral, text=texto_boton, anchor="w",
                      fg_color="transparent", hover_color="#2b2b2b",
                      command=funcion_seccion
                      ).pack(fill="x", padx=15, pady=5)

    ctk.CTkButton(barra_lateral, text="Cerrar Sesión", fg_color="#d9534f",
                  command=lambda: cerrar_sesion(ventana_principal)).pack(side="bottom", fill="x", padx=15, pady=20)

    if secciones:
        secciones[0][1]() # Iniciar en la primera sección por defecto

    ventana_principal.mainloop()

def crear_pantalla_login():
    ventana = ctk.CTk()
    ventana.geometry("440x660")
    ventana.title("SogueApp - Login")
    poner_icono(ventana)

    marco_principal = ctk.CTkFrame(ventana)
    marco_principal.pack(fill="both", expand=True, padx=20, pady=20)
    ctk.CTkLabel(marco_principal, text="SogueApp Financiera", font=("Arial", 22, "bold")).pack(pady=15)

    marco_botones = ctk.CTkFrame(marco_principal)
    marco_botones.pack(fill="x", pady=5)
    marco_formulario = ctk.CTkFrame(marco_principal)
    marco_formulario.pack(fill="both", expand=True, pady=10)

    def limpiar_formulario():
        for widget in marco_formulario.winfo_children():
            widget.destroy()

    def mostrar_login():
        limpiar_formulario()
        ctk.CTkLabel(marco_formulario, text="Iniciar Sesión", font=("Arial", 16, "bold")).pack(pady=10)
        user = ctk.CTkEntry(marco_formulario, placeholder_text="Usuario", width=280)
        user.pack(pady=8)
        pwd = ctk.CTkEntry(marco_formulario, placeholder_text="Contraseña", show="*", width=280)
        pwd.pack(pady=8)
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

        ctk.CTkButton(marco_formulario, text="Entrar", command=intentar_login, width=280, fg_color="#2c82c9").pack(pady=12)
        ctk.CTkButton(marco_formulario, text="¿Olvidaste tu contraseña?",
                      fg_color="transparent", text_color="#3b8ed0",
                      hover=False, command=mostrar_recuperar).pack(pady=5)

        # mientras no exista ningún administrador, avisamos cómo crear el primero
        if not logica_login.existe_admin():
            ctk.CTkLabel(marco_formulario, text_color="#f59e0b", wraplength=280,
                         text="Todavía no hay administrador. Registrate como Administrador para gestionar el sistema."
                         ).pack(pady=(10, 0))

    def mostrar_registro():
        limpiar_formulario()
        ctk.CTkLabel(marco_formulario, text="Crear Cuenta Nueva", font=("Arial", 16, "bold")).pack(pady=5)
        user = ctk.CTkEntry(marco_formulario, placeholder_text="Usuario", width=280)
        user.pack(pady=6)
        pwd = ctk.CTkEntry(marco_formulario, placeholder_text="Contraseña (mín. 8 carac., 1 mayús., 1 núm.)", show="*", width=280)
        pwd.pack(pady=6)

        # Selector de rol con explicaciones claras
        ctk.CTkLabel(marco_formulario, text="Selecciona tu tipo de perfil:", font=("Arial", 11, "bold")).pack(anchor="w", padx=15, pady=(5, 0))

        rol_opciones = {
            "Usuario Completo (Presupuestos + Ahorros)": "completo",
            "Solo Presupuesto (Quiero ver cómo gastar y organizar)": "presupuesto",
            "Solo Ahorros (Quiero llevar un registro de mis metas)": "ahorro"
        }
        # el rol administrador solo se ofrece si todavía no hay ninguno;
        # después, nuevos administradores los crea otro administrador desde su panel
        if not logica_login.existe_admin():
            rol_opciones["Administrador (gestiona usuarios del sistema)"] = "admin"

        rol_combo_var = ctk.StringVar(value=list(rol_opciones.keys())[0])
        ctk.CTkOptionMenu(marco_formulario, values=list(rol_opciones.keys()), variable=rol_combo_var, width=280).pack(pady=6)

        pregunta_var = ctk.StringVar(value=PREGUNTAS_SECRETAS[0])
        ctk.CTkOptionMenu(marco_formulario, values=PREGUNTAS_SECRETAS, variable=pregunta_var, width=280).pack(pady=6)
        respuesta = ctk.CTkEntry(marco_formulario, placeholder_text="Respuesta secreta", width=280)
        respuesta.pack(pady=6)

        error = ctk.CTkLabel(marco_formulario, text="", text_color="red", wraplength=280)
        error.pack(pady=2)

        def intentar_registro():
            nombre = user.get().strip()
            clave = pwd.get()
            rol_seleccionado = rol_opciones[rol_combo_var.get()]

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

            if logica_login.crear_usuario(nombre, clave, pregunta_var.get(), respuesta.get(), rol_seleccionado):
                error.configure(text="¡Éxito! Ya puedes iniciar sesión", text_color="green")
                ventana.after(1500, mostrar_login)
            else:
                error.configure(text="No se pudo crear el usuario", text_color="red")

        ctk.CTkButton(marco_formulario, text="Registrarse", command=intentar_registro, width=280, fg_color="#27ae60").pack(pady=10)

    def mostrar_recuperar():
        limpiar_formulario()
        ctk.CTkLabel(marco_formulario, text="Recuperar Contraseña", font=("Arial", 16, "bold")).pack(pady=10)
        user = ctk.CTkEntry(marco_formulario, placeholder_text="Usuario", width=280)
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

        ctk.CTkButton(marco_formulario, text="Buscar", command=buscar_pregunta, width=280).pack(pady=15)
        ctk.CTkButton(marco_formulario, text="Volver a Iniciar Sesión", fg_color="transparent",
                      text_color="#3b8ed0", hover=False, command=mostrar_login).pack(pady=5)

    def mostrar_responder_pregunta(nombre, pregunta):
        limpiar_formulario()
        ctk.CTkLabel(marco_formulario, text="Recuperar Contraseña", font=("Arial", 16, "bold")).pack(pady=10)
        ctk.CTkLabel(marco_formulario, text=pregunta, wraplength=280).pack(pady=5)
        respuesta = ctk.CTkEntry(marco_formulario, placeholder_text="Tu respuesta", width=280)
        respuesta.pack(pady=8)
        nueva_pwd = ctk.CTkEntry(marco_formulario, placeholder_text="Nueva contraseña", show="*", width=280)
        nueva_pwd.pack(pady=8)

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

        ctk.CTkButton(marco_formulario, text="Cambiar Contraseña", command=confirmar_cambio, width=280, fg_color="#27ae60").pack(pady=15)

    ctk.CTkButton(marco_botones, text="Iniciar Sesión", command=mostrar_login, width=170).pack(side="left", padx=5)
    ctk.CTkButton(marco_botones, text="Registrarse", command=mostrar_registro, width=170).pack(side="left", padx=5)

    mostrar_login()
    ventana.mainloop()

if __name__ == "__main__":
    crear_pantalla_login()