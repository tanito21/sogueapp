import sqlite3
import hashlib
import re

# aca elegimos usar una variable para la BD, así podemos usar una falsa durante las pruebas
nombre_bd = "soguebase.db"

# le damos más tiempo de espera a sqlite por si el archivo está momentáneamente
# bloqueado (por ejemplo, por un antivirus)
TIMEOUT_BD = 10


def conectar():
    """Función centralizada para conectarnos a la bd, así todas las funciones
    usan el mismo timeout sin repetir el parámetro en cada una."""
    return sqlite3.connect(nombre_bd, timeout=TIMEOUT_BD)


def inicializar_db():
    """Crea la tabla de usuarios si no existe, y agrega las columnas nuevas
    si venimos de una versión anterior de la base de datos (migración simple)."""
    base_datos = conectar()
    try:
        cursor = base_datos.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            clave TEXT,
            pregunta_secreta TEXT,
            respuesta_secreta TEXT)""")

        # revisamos las columnas existentes por si la bd es de una versión vieja
        cursor.execute("PRAGMA table_info(usuarios)")
        columnas = [fila[1] for fila in cursor.fetchall()]
        if "pregunta_secreta" not in columnas:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN pregunta_secreta TEXT")
        if "respuesta_secreta" not in columnas:
            cursor.execute("ALTER TABLE usuarios ADD COLUMN respuesta_secreta TEXT")

        base_datos.commit()
    finally:
        # el finally asegura que la conexión se cierre siempre, incluso si algo falla arriba
        base_datos.close()


def hash_texto(texto):
    """Convierte un texto (contraseña o respuesta secreta) a hash SHA256."""
    return hashlib.sha256(texto.encode()).hexdigest()


def clave_es_segura(clave):
    """Revisa que la contraseña cumpla un mínimo de seguridad.
    Retorna (True, "") si está bien, o (False, "motivo") si no cumple."""
    if len(clave) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres"
    if not re.search(r"[A-Z]", clave):
        return False, "La contraseña debe tener al menos una mayúscula"
    if not re.search(r"[a-z]", clave):
        return False, "La contraseña debe tener al menos una minúscula"
    if not re.search(r"[0-9]", clave):
        return False, "La contraseña debe tener al menos un número"
    return True, ""


def usuario_existe(nombre):
    """Verifica si un usuario ya existe."""
    base_datos = conectar()
    try:
        cursor = base_datos.cursor()
        cursor.execute("SELECT usuario FROM usuarios WHERE usuario=?", (nombre,))
        return cursor.fetchone() is not None
    finally:
        base_datos.close()


def crear_usuario(nombre, clave, pregunta, respuesta):
    """Crea un nuevo usuario junto con su pregunta secreta (para poder
    recuperar la clave después). Retorna True si fue exitoso o False si
    falló (usuario ya existe, datos vacíos, o clave insegura)."""
    if not nombre or not clave or not pregunta or not respuesta:
        return False

    es_segura, _ = clave_es_segura(clave)
    if not es_segura:
        return False

    base_datos = conectar()
    try:
        cursor = base_datos.cursor()
        clave_hash = hash_texto(clave)
        # normalizamos la respuesta para que no importe mayúsculas o espacios de más
        respuesta_hash = hash_texto(respuesta.strip().lower())
        cursor.execute("""
            INSERT INTO usuarios (usuario, clave, pregunta_secreta, respuesta_secreta)
            VALUES (?, ?, ?, ?)
        """, (nombre, clave_hash, pregunta, respuesta_hash))
        base_datos.commit()
        return True
    except sqlite3.IntegrityError:
        # el usuario ya existe (columna UNIQUE), no es un error grave
        return False
    finally:
        # esto se ejecuta tanto si todo salió bien como si saltó la excepción,
        # así la conexión nunca queda abierta y bloqueando el archivo
        base_datos.close()


def verificar_usuario(nombre, clave):
    """Verifica si el usuario y contraseña coinciden en el sistema."""
    base_datos = conectar()
    try:
        cursor = base_datos.cursor()
        cursor.execute("SELECT clave FROM usuarios WHERE usuario=?", (nombre,))
        fila = cursor.fetchone()
    finally:
        base_datos.close()

    if fila is None:
        return False

    clave_hash = hash_texto(clave)
    return fila[0] == clave_hash


def obtener_pregunta_secreta(nombre):
    """Devuelve la pregunta secreta de un usuario, o None si no existe."""
    base_datos = conectar()
    try:
        cursor = base_datos.cursor()
        cursor.execute("SELECT pregunta_secreta FROM usuarios WHERE usuario=?", (nombre,))
        fila = cursor.fetchone()
        return fila[0] if fila else None
    finally:
        base_datos.close()


def verificar_respuesta_secreta(nombre, respuesta):
    """Verifica si la respuesta secreta coincide con la registrada."""
    base_datos = conectar()
    try:
        cursor = base_datos.cursor()
        cursor.execute("SELECT respuesta_secreta FROM usuarios WHERE usuario=?", (nombre,))
        fila = cursor.fetchone()
    finally:
        base_datos.close()

    if fila is None or fila[0] is None:
        return False

    respuesta_hash = hash_texto(respuesta.strip().lower())
    return fila[0] == respuesta_hash


def cambiar_clave(nombre, nueva_clave):
    """Actualiza la contraseña de un usuario (usar solo después de verificar
    la respuesta secreta). Retorna True si se pudo cambiar."""
    es_segura, _ = clave_es_segura(nueva_clave)
    if not es_segura:
        return False

    base_datos = conectar()
    try:
        cursor = base_datos.cursor()
        clave_hash = hash_texto(nueva_clave)
        cursor.execute("UPDATE usuarios SET clave=? WHERE usuario=?", (clave_hash, nombre))
        base_datos.commit()
        return cursor.rowcount > 0
    finally:
        base_datos.close()