import customtkinter as ctk
import sqlite3
import hashlib
from tkinter import messagebox
from datetime import datetime


# CONEXION Y CONFIGURACION DE BASE DE DATOS

base_datos = sqlite3.connect("soguebase.db")
cursor = base_datos.cursor()

# tabla de usuarios (login, registro y preguntas de seguridad)
cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE,
    clave TEXT,
    pregunta1 TEXT,
    respuesta1 TEXT,
    pregunta2 TEXT,
    respuesta2 TEXT,
    pregunta3 TEXT,
    respuesta3 TEXT)""")

# tabla de categorias del presupuesto
cursor.execute("""
CREATE TABLE IF NOT EXISTS categorias(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT,
    presupuesto REAL,
    gastado REAL DEFAULT 0)""")

# tabla de gastos registrados
cursor.execute("""
CREATE TABLE IF NOT EXISTS gastos(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    categoria TEXT,
    concepto TEXT,
    monto REAL,
    fecha TEXT)""")

base_datos.commit()

# lista de preguntas de seguridad disponibles para elegir
preguntas_disponibles = [
    "¿cómo se llama tu mascota?",
    "¿cuál es tu comida favorita?",
    "¿en qué ciudad naciste?",
    "¿cómo se llama tu mejor amigo de la infancia?",
    "¿cómo se llamaba tu primera escuela?",
    "¿cuál es el segundo nombre de tu madre?",
]

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

usuario_actual = None  # guarda el nombre del usuario que inició sesión



# FUNCIONES DE SEGURIDAD (CLAVES Y RESPUESTAS)

def encriptar_texto(texto):
    """Convierte un texto en un hash para no guardar claves ni respuestas en claro."""
    texto_limpio = texto.strip().lower()
    return hashlib.sha256(texto_limpio.encode()).hexdigest()



# LOGICA DE NEGOCIO Y FUNCIONES DE CONTROL


def limpiar_tabla():
    """Limpia los registros existentes para reestructurar el presupuesto."""
    cursor.execute("DELETE FROM categorias")
    cursor.execute("DELETE FROM gastos")
    base_datos.commit()
    actualizar()

def generar_presupuesto():
    """Calcula y distribuye los fondos según el método seleccionado."""
    limpiar_tabla()

    try:
        ingreso = float(campo_ingreso.get())
    except ValueError:
        messagebox.showerror("Error de validación", "El ingreso ingresado debe ser un valor numérico.")
        return

    metodo = metodo_elegido.get()

    if metodo == "50/30/20":
        datos = [
            ("Necesidades", ingreso * 0.5),
            ("Deseos", ingreso * 0.3),
            ("Ahorro", ingreso * 0.2),
        ]
    elif metodo == "Objetivos":
        datos = [
            ("Necesidades", ingreso * 0.4),
            ("Comida", ingreso * 0.25),
            ("Transporte", ingreso * 0.15),
            ("Ocio", ingreso * 0.10),
            ("Ahorro", ingreso * 0.10),
        ]
    else:
        return

    # insercion parametrizada para evitar inyecciones sql
    for nombre, monto in datos:
        cursor.execute("""
        INSERT INTO categorias(nombre, presupuesto)
        VALUES(?,?)
        """, (nombre, monto))

    base_datos.commit()
    actualizar()

def registrar_gasto():
    """Procesa la transacción de egreso y actualiza los acumuladores locales."""
    categoria = lista_categorias.get()
    concepto = campo_concepto.get()

    try:
        monto = float(campo_monto.get())
    except ValueError:
        messagebox.showerror("Error de validación", "El monto del gasto debe ser numérico.")
        return

    fecha = datetime.now().strftime("%d/%m/%Y")

    cursor.execute("""
    SELECT presupuesto, gastado
    FROM categorias
    WHERE nombre=?
    """, (categoria,))

    datos = cursor.fetchone()
    if not datos:
        return

    presupuesto, gastado = datos
    nuevo_gastado = gastado + monto

    # actualizacion del acumulador de gastos de la categoria
    cursor.execute("""
    UPDATE categorias
    SET gastado=?
    WHERE nombre=?
    """, (nuevo_gastado, categoria))

    # insercion del registro en el historial de transacciones
    cursor.execute("""
    INSERT INTO gastos(categoria, concepto, monto, fecha)
    VALUES(?,?,?,?)
    """, (categoria, concepto, monto, fecha))
    base_datos.commit()

    # evaluacion de limites presupuestarios
    restante = presupuesto - nuevo_gastado
    if restante < 0:
        messagebox.showwarning(
            "Exceso de presupuesto",
            f"Alerta: Ha superado el saldo disponible en {categoria} por Gs. {abs(restante):,.0f}"
        )

    # limpieza de los campos de entrada en la interfaz
    campo_monto.delete(0, "end")
    campo_concepto.delete(0, "end")
    actualizar()


# GESTION DE VISTAS Y RENDERIZADO DE LA GUI PRINCIPAL

def cargar_categorias():
    """Sincroniza dinámicamente las opciones del ComboBox con la base de datos."""
    cursor.execute("SELECT nombre FROM categorias")
    datos = cursor.fetchall()
    opciones = [d[0] for d in datos]
    lista_categorias.configure(values=opciones)

    if datos:
        lista_categorias.set(datos[0][0])

def actualizar_datos():
    """Consulta la base de datos y renderiza el reporte en el Dashboard."""
    caja_resumen.configure(state="normal")
    caja_resumen.delete("1.0", "end")

    # renderizado del estado de las categorias
    cursor.execute("SELECT nombre, presupuesto, gastado FROM categorias")
    categorias = cursor.fetchall()

    caja_resumen.insert("end", "=== ESTADO DE CATEGORÍAS PRESUPUESTARIAS ===\n\n")
    for c in categorias:
        restante = c[1] - c[2]
        caja_resumen.insert("end",
            f"Categoría: {c[0]}\n"
            f" Presupuesto asignado: Gs. {c[1]:,.0f}\n"
            f" Total gastado:        Gs. {c[2]:,.0f}\n"
            f" Saldo disponible:     Gs. {restante:,.0f}\n\n"
        )

    # renderizado del historial de gastos recientes
    caja_resumen.insert("end", "\n=== HISTORIAL DE GASTOS RECIENTES (ÚLTIMOS 10) ===\n\n")
    cursor.execute("SELECT fecha, categoria, concepto, monto FROM gastos ORDER BY id DESC LIMIT 10")
    gastos = cursor.fetchall()

    for g in gastos:
        caja_resumen.insert("end", f" Fecha: {g[0]} | Categoría: {g[1]}\n Detalle: {g[2]} -> Gs. {g[3]:,.0f}\n\n")

    caja_resumen.configure(state="disabled")

def actualizar():
    """Función controladora encargada de refrescar la interfaz completa."""
    cargar_categorias()
    actualizar_datos()


# CONSTRUCCION DE LA APP PRINCIPAL (DESPUES DEL LOGIN)


def abrir_app_principal():
    """Crea y muestra la ventana principal de finanzas, ya con el usuario logueado."""
    global campo_ingreso, metodo_elegido, lista_categorias
    global campo_concepto, campo_monto, caja_resumen

    ventana_principal = ctk.CTk()
    ventana_principal.geometry("900x650")
    ventana_principal.title(f"Control de Finanzas Personales - {usuario_actual}")

    # encabezado principal
    titulo = ctk.CTkLabel(ventana_principal, text="Control de Finanzas Personales", font=("Arial", 26, "bold"))
    titulo.pack(pady=15)

    # panel superior: configuracion de ingresos
    panel_ingreso = ctk.CTkFrame(ventana_principal)
    panel_ingreso.pack(pady=10, padx=20, fill="x")

    campo_ingreso = ctk.CTkEntry(panel_ingreso, placeholder_text="Ingreso mensual total (Gs.)", width=200)
    campo_ingreso.grid(row=0, column=0, padx=15, pady=15)

    metodo_elegido = ctk.StringVar(value="50/30/20")
    menu_metodo = ctk.CTkOptionMenu(panel_ingreso, values=["50/30/20", "Objetivos"], variable=metodo_elegido)
    menu_metodo.grid(row=0, column=1, padx=15)

    boton_generar = ctk.CTkButton(panel_ingreso, text="Generar Presupuesto", command=generar_presupuesto, fg_color="#2c82c9")
    boton_generar.grid(row=0, column=2, padx=15)

    # panel central: registro de transacciones diarias
    panel_gasto = ctk.CTkFrame(ventana_principal)
    panel_gasto.pack(pady=10, padx=20, fill="x")

    lista_categorias = ctk.CTkComboBox(panel_gasto, values=[], width=150)
    lista_categorias.grid(row=0, column=0, padx=10, pady=15)

    campo_concepto = ctk.CTkEntry(panel_gasto, placeholder_text="Concepto/Detalle (ej: Alquiler)", width=220)
    campo_concepto.grid(row=0, column=1, padx=10)

    campo_monto = ctk.CTkEntry(panel_gasto, placeholder_text="Monto gastado (Gs.)", width=150)
    campo_monto.grid(row=0, column=2, padx=10)

    boton_registrar_gasto = ctk.CTkButton(panel_gasto, text="Registrar Gasto", command=registrar_gasto, fg_color="#d9534f")
    boton_registrar_gasto.grid(row=0, column=3, padx=10)

    # panel inferior: dashboard de visualizacion de datos
    caja_resumen = ctk.CTkTextbox(ventana_principal, width=850, height=380, font=("Courier New", 12))
    caja_resumen.pack(pady=15)

    # ejecucion inicial del ciclo de vida de la aplicacion
    actualizar()
    ventana_principal.mainloop()

    # cierre seguro de la conexion a la base de datos al finalizar la ejecucion
    base_datos.close()



# PANTALLA DE LOGIN

def crear_pantalla_login():
    ventana_login = ctk.CTk()
    ventana_login.geometry("400x420")
    ventana_login.title("Iniciar Sesión")

    titulo = ctk.CTkLabel(ventana_login, text="Control de Finanzas", font=("Arial", 22, "bold"))
    titulo.pack(pady=(30, 10))

    subtitulo = ctk.CTkLabel(ventana_login, text="Iniciá sesión para continuar", font=("Arial", 14))
    subtitulo.pack(pady=(0, 20))

    campo_usuario = ctk.CTkEntry(ventana_login, placeholder_text="usuario", width=250)
    campo_usuario.pack(pady=8)

    campo_clave = ctk.CTkEntry(ventana_login, placeholder_text="contraseña", show="*", width=250)
    campo_clave.pack(pady=8)

    etiqueta_error = ctk.CTkLabel(ventana_login, text="", text_color="#e74c3c")
    etiqueta_error.pack(pady=(5, 0))

    def intentar_ingresar():
        global usuario_actual
        nombre = campo_usuario.get().strip()
        clave = campo_clave.get()

        if not nombre or not clave:
            etiqueta_error.configure(text="Completá usuario y contraseña.")
            return

        cursor.execute("SELECT clave FROM usuarios WHERE usuario=?", (nombre,))
        fila = cursor.fetchone()

        if not fila or fila[0] != encriptar_texto(clave):
            etiqueta_error.configure(text="Usuario o contraseña incorrectos.")
            return

        usuario_actual = nombre
        ventana_login.destroy()
        abrir_app_principal()

    boton_entrar = ctk.CTkButton(ventana_login, text="Iniciar sesión", command=intentar_ingresar, fg_color="#2c82c9", width=250)
    boton_entrar.pack(pady=15)

    fila_botones = ctk.CTkFrame(ventana_login, fg_color="transparent")
    fila_botones.pack(pady=5)

    boton_crear_cuenta = ctk.CTkButton(
        fila_botones, text="Crear cuenta", width=120, fg_color="#27ae60",
        command=lambda: abrir_ventana_registro(ventana_login)
    )
    boton_crear_cuenta.grid(row=0, column=0, padx=5)

    boton_olvide_clave = ctk.CTkButton(
        fila_botones, text="Olvidé mi contraseña", width=120, fg_color="#7f8c8d",
        command=lambda: abrir_ventana_recuperar(ventana_login)
    )
    boton_olvide_clave.grid(row=0, column=1, padx=5)

    ventana_login.mainloop()


# VENTANA DE REGISTRO DE NUEVO USUARIO


def abrir_ventana_registro(ventana_padre):
    ventana_registro = ctk.CTkToplevel(ventana_padre)
    ventana_registro.geometry("420x620")
    ventana_registro.title("Crear cuenta")
    ventana_registro.grab_set()  # bloquea la ventana de atrás mientras se registra

    ctk.CTkLabel(ventana_registro, text="Crear cuenta nueva", font=("Arial", 20, "bold")).pack(pady=(20, 15))

    campo_usuario_nuevo = ctk.CTkEntry(ventana_registro, placeholder_text="usuario", width=280)
    campo_usuario_nuevo.pack(pady=6)

    campo_clave_nueva = ctk.CTkEntry(ventana_registro, placeholder_text="contraseña", show="*", width=280)
    campo_clave_nueva.pack(pady=6)

    campo_clave_confirmar = ctk.CTkEntry(ventana_registro, placeholder_text="confirmar contraseña", show="*", width=280)
    campo_clave_confirmar.pack(pady=6)

    ctk.CTkLabel(ventana_registro, text="Elegí 3 preguntas de seguridad", font=("Arial", 13, "bold")).pack(pady=(15, 5))

    menus_preguntas = []
    campos_respuestas = []

    for numero in range(3):
        menu_pregunta = ctk.CTkOptionMenu(ventana_registro, values=preguntas_disponibles, width=280)
        menu_pregunta.set(preguntas_disponibles[numero])
        menu_pregunta.pack(pady=(8, 2))

        campo_respuesta = ctk.CTkEntry(ventana_registro, placeholder_text="tu respuesta", width=280)
        campo_respuesta.pack(pady=2)

        menus_preguntas.append(menu_pregunta)
        campos_respuestas.append(campo_respuesta)

    etiqueta_error = ctk.CTkLabel(ventana_registro, text="", text_color="#e74c3c")
    etiqueta_error.pack(pady=(10, 0))

    def guardar_cuenta():
        nombre = campo_usuario_nuevo.get().strip()
        clave = campo_clave_nueva.get()
        confirmar = campo_clave_confirmar.get()

        preguntas_elegidas = [menu.get() for menu in menus_preguntas]
        respuestas = [campo.get().strip() for campo in campos_respuestas]

        if not nombre or not clave:
            etiqueta_error.configure(text="Completá usuario y contraseña.")
            return

        if clave != confirmar:
            etiqueta_error.configure(text="Las contraseñas no coinciden.")
            return

        if len(set(preguntas_elegidas)) < 3:
            etiqueta_error.configure(text="Elegí 3 preguntas distintas.")
            return

        if not all(respuestas):
            etiqueta_error.configure(text="Respondé las 3 preguntas de seguridad.")
            return

        cursor.execute("SELECT id FROM usuarios WHERE usuario=?", (nombre,))
        if cursor.fetchone():
            etiqueta_error.configure(text="Ese usuario ya existe.")
            return

        cursor.execute("""
        INSERT INTO usuarios(usuario, clave, pregunta1, respuesta1, pregunta2, respuesta2, pregunta3, respuesta3)
        VALUES(?,?,?,?,?,?,?,?)
        """, (
            nombre, encriptar_texto(clave),
            preguntas_elegidas[0], encriptar_texto(respuestas[0]),
            preguntas_elegidas[1], encriptar_texto(respuestas[1]),
            preguntas_elegidas[2], encriptar_texto(respuestas[2]),
        ))
        base_datos.commit()

        messagebox.showinfo("Cuenta creada", "Tu cuenta se creó correctamente. Ya podés iniciar sesión.")
        ventana_registro.destroy()

    boton_guardar = ctk.CTkButton(ventana_registro, text="Crear cuenta", command=guardar_cuenta, fg_color="#27ae60", width=280)
    boton_guardar.pack(pady=15)



# VENTANA DE RECUPERACION DE CONTRASEÑA


def abrir_ventana_recuperar(ventana_padre):
    ventana_recuperar = ctk.CTkToplevel(ventana_padre)
    ventana_recuperar.geometry("420x450")
    ventana_recuperar.title("Recuperar contraseña")
    ventana_recuperar.grab_set()

    contenedor = ctk.CTkFrame(ventana_recuperar, fg_color="transparent")
    contenedor.pack(fill="both", expand=True, padx=20, pady=20)

    ctk.CTkLabel(contenedor, text="Recuperar contraseña", font=("Arial", 20, "bold")).pack(pady=(0, 15))

    campo_usuario_buscar = ctk.CTkEntry(contenedor, placeholder_text="usuario", width=280)
    campo_usuario_buscar.pack(pady=6)

    etiqueta_estado = ctk.CTkLabel(contenedor, text="", text_color="#e74c3c")
    etiqueta_estado.pack(pady=(5, 0))

    # estos widgets se crean vacios y se completan cuando se encuentra el usuario
    etiquetas_preguntas = []
    campos_respuestas = []
    fila_preguntas = ctk.CTkFrame(contenedor, fg_color="transparent")

    fila_clave_nueva = ctk.CTkFrame(contenedor, fg_color="transparent")
    campo_clave_nueva = ctk.CTkEntry(fila_clave_nueva, placeholder_text="nueva contraseña", show="*", width=280)
    campo_clave_confirmar = ctk.CTkEntry(fila_clave_nueva, placeholder_text="confirmar nueva contraseña", show="*", width=280)

    datos_usuario_encontrado = {}

    def buscar_usuario():
        nombre = campo_usuario_buscar.get().strip()
        cursor.execute("""
        SELECT pregunta1, respuesta1, pregunta2, respuesta2, pregunta3, respuesta3
        FROM usuarios WHERE usuario=?
        """, (nombre,))
        fila = cursor.fetchone()

        if not fila:
            etiqueta_estado.configure(text="No existe ese usuario.")
            return

        datos_usuario_encontrado["usuario"] = nombre
        datos_usuario_encontrado["preguntas"] = fila

        etiqueta_estado.configure(text="")
        for hijo in fila_preguntas.winfo_children():
            hijo.destroy()
        etiquetas_preguntas.clear()
        campos_respuestas.clear()

        preguntas = [fila[0], fila[2], fila[4]]
        for pregunta in preguntas:
            ctk.CTkLabel(fila_preguntas, text=pregunta).pack(pady=(8, 2))
            campo = ctk.CTkEntry(fila_preguntas, placeholder_text="tu respuesta", width=280)
            campo.pack(pady=2)
            campos_respuestas.append(campo)

        boton_buscar.pack_forget()
        campo_usuario_buscar.configure(state="disabled")
        fila_preguntas.pack(pady=5)
        boton_verificar.pack(pady=10)

    def verificar_respuestas():
        fila = datos_usuario_encontrado.get("preguntas")
        if not fila:
            return

        respuestas_correctas = [fila[1], fila[3], fila[5]]
        respuestas_ingresadas = [campo.get() for campo in campos_respuestas]

        if all(encriptar_texto(r) == correcta for r, correcta in zip(respuestas_ingresadas, respuestas_correctas)):
            etiqueta_estado.configure(text_color="#27ae60", text="¡Correcto! Elegí tu nueva contraseña.")
            boton_verificar.pack_forget()
            fila_clave_nueva.pack(pady=5)
            campo_clave_nueva.pack(pady=6)
            campo_clave_confirmar.pack(pady=6)
            boton_cambiar_clave.pack(pady=15)
        else:
            etiqueta_estado.configure(text_color="#e74c3c", text="Alguna respuesta no coincide, probá de nuevo.")

    def cambiar_clave():
        nueva = campo_clave_nueva.get()
        confirmar = campo_clave_confirmar.get()

        if not nueva:
            etiqueta_estado.configure(text_color="#e74c3c", text="La contraseña no puede estar vacía.")
            return

        if nueva != confirmar:
            etiqueta_estado.configure(text_color="#e74c3c", text="Las contraseñas no coinciden.")
            return

        cursor.execute(
            "UPDATE usuarios SET clave=? WHERE usuario=?",
            (encriptar_texto(nueva), datos_usuario_encontrado["usuario"])
        )
        base_datos.commit()

        messagebox.showinfo("Contraseña actualizada", "Tu contraseña se cambió correctamente. Ya podés iniciar sesión.")
        ventana_recuperar.destroy()

    boton_buscar = ctk.CTkButton(contenedor, text="Buscar usuario", command=buscar_usuario, width=280)
    boton_buscar.pack(pady=10)

    boton_verificar = ctk.CTkButton(contenedor, text="Verificar respuestas", command=verificar_respuestas, fg_color="#2c82c9", width=280)

    boton_cambiar_clave = ctk.CTkButton(contenedor, text="Cambiar contraseña", command=cambiar_clave, fg_color="#27ae60", width=280)



# PUNTO DE ENTRADA DE LA APLICACION


if __name__ == "__main__":
    crear_pantalla_login()
