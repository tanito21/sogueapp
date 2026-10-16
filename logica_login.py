<<<<<<< HEAD
"""lógica del login de sogueapp: usuarios, roles, contraseñas y base de datos.

este módulo no usa la interfaz gráfica, asi que se puede probar solo
(ver test_login.py). la interfaz (interfaz_login.py) llama a estas funciones.

roles validos: admin, completo, presupuesto, ahorro.
"""

import hashlib
import hmac
import io
import math
import os
import re
import secrets
import sqlite3
import sys
from contextlib import contextmanager, redirect_stdout

# archivo de la base, junto a este módulo; las pruebas lo cambian por uno temporal
nombre_bd = os.path.join(os.path.dirname(os.path.abspath(__file__)), "soguebase.db")

ROLES_VALIDOS = ("admin", "completo", "presupuesto", "ahorro")
ROL_POR_DEFECTO = "completo"

LARGO_MINIMO_CLAVE = 8

# administrador inicial: se crea solo si no existe ningun admin
ADMIN_USUARIO = "administrator"
ADMIN_CLAVE_INICIAL = "Admin123"
ADMIN_PREGUNTA = "¿Cuál es el nombre de tu primera mascota?"

# reparto automático del ingreso: (nombre de la categoría, porcentaje)
DISTRIBUCION_50_30_20 = (
    ("Necesidades Básicas", 50),
    ("Deseos y Ocio", 30),
    ("Ahorro e Inversión", 20),
)

# hash de contraseñas: pbkdf2 con sal (las pruebas bajan las iteraciones para ir rápido)
PREFIJO_HASH = "pbkdf2_sha256"
ITERACIONES = 200_000

# base de datos

def conectar():
    """abre la conexión a la base de datos indicada en ``nombre_bd``.

    devuelve una conexión sqlite3 normal; quien la pide debe cerrarla.
    """
    return sqlite3.connect(nombre_bd)

@contextmanager
def _bd():
    """entrega un cursor, guarda los cambios al terminar y siempre cierra."""
    con = conectar()
    try:
        yield con.cursor()
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def inicializar_db():
    """crea las tablas si faltan, actualiza bases viejas y crea el admin inicial.

    se puede llamar en cada arranque: no borra ni duplica nada.
    """
    with _bd() as cur:
        cur.execute("""CREATE TABLE IF NOT EXISTS usuarios(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE,
            clave TEXT NOT NULL,
            pregunta TEXT,
            respuesta TEXT,
            rol TEXT NOT NULL DEFAULT 'completo')""")
        cur.execute("""CREATE TABLE IF NOT EXISTS categorias(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            presupuesto REAL,
            gastado REAL DEFAULT 0,
            orden INTEGER DEFAULT 0)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS gastos(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria TEXT,
            concepto TEXT,
            monto REAL,
            fecha TEXT)""")
        _actualizar_tablas_viejas(cur)
        _crear_admin_inicial(cur)
        _asignar_datos_sin_dueno(cur)

def _columnas(cur, tabla):
    """devuelve los nombres de columnas que tiene una tabla."""
    cur.execute(f"PRAGMA table_info({tabla})")
    return {fila[1] for fila in cur.fetchall()}

def _actualizar_tablas_viejas(cur):
    """agrega las columnas nuevas a bases creadas por versiones anteriores."""
    cols = _columnas(cur, "usuarios")
    if "pregunta" not in cols:
        cur.execute("ALTER TABLE usuarios ADD COLUMN pregunta TEXT")
        cur.execute("ALTER TABLE usuarios ADD COLUMN respuesta TEXT")
        # la 1.5.2 guardaba tres preguntas: nos quedamos con la primera
        if "pregunta1" in cols:
            cur.execute("UPDATE usuarios SET pregunta = pregunta1, respuesta = respuesta1")
    if "rol" not in cols:
        cur.execute("ALTER TABLE usuarios ADD COLUMN rol TEXT NOT NULL DEFAULT 'completo'")
    cols_categorias = _columnas(cur, "categorias")
    if "orden" not in cols_categorias:
        cur.execute("ALTER TABLE categorias ADD COLUMN orden INTEGER DEFAULT 0")
    # cada presupuesto y gasto pertenece a un usuario
    if "usuario_id" not in cols_categorias:
        cur.execute("ALTER TABLE categorias ADD COLUMN usuario_id INTEGER")
    if "usuario_id" not in _columnas(cur, "gastos"):
        cur.execute("ALTER TABLE gastos ADD COLUMN usuario_id INTEGER")

def _crear_admin_inicial(cur):
    """crea el administrador si todavia no hay ninguno."""
    cur.execute("SELECT 1 FROM usuarios WHERE rol = 'admin' LIMIT 1")
    if cur.fetchone() is not None:
        return
    # la respuesta es aleatoria: el admin no se recupera por pregunta secreta
    cur.execute(
        "INSERT OR IGNORE INTO usuarios(usuario, clave, pregunta, respuesta, rol) "
        "VALUES(?,?,?,?,?)",
        (ADMIN_USUARIO, hashear(ADMIN_CLAVE_INICIAL), ADMIN_PREGUNTA,
         hashear(secrets.token_hex(16)), "admin"),
    )

def _asignar_datos_sin_dueno(cur):
    """en la 1.5.2 el presupuesto era de todos: pasa al usuario más antiguo."""
    cur.execute("SELECT MIN(id) FROM usuarios")
    id_dueno = cur.fetchone()[0]
    if id_dueno is None:
        return
    for tabla in ("categorias", "gastos"):
        cur.execute(f"UPDATE {tabla} SET usuario_id = ? WHERE usuario_id IS NULL", (id_dueno,))

#hashes (contraseñas y respuestas secretas)

def _normalizar(texto):
    """quita espacios y pasa a minúscula (para comparar respuestas)."""
    return texto.strip().lower()

def hashear(texto):
    """devuelve el hash con sal de un texto: ``pbkdf2_sha256$iter$sal$hash``."""
    sal = os.urandom(16)
    derivado = hashlib.pbkdf2_hmac("sha256", texto.encode("utf-8"), sal, ITERACIONES)
    return f"{PREFIJO_HASH}${ITERACIONES}${sal.hex()}${derivado.hex()}"

def _es_hash_viejo(almacenado):
    """los hashes de la 1.5.2 eran sha256 simple, sin el prefijo nuevo."""
    return not almacenado.startswith(PREFIJO_HASH + "$")


def verificar_hash(texto, almacenado):
    """compara un texto con su hash guardado (formato nuevo o viejo).

    devuelve true si coinciden.
    """
    if not almacenado:
        return False
    if _es_hash_viejo(almacenado):
        simple = hashlib.sha256(_normalizar(texto).encode()).hexdigest()
        return hmac.compare_digest(simple, almacenado)
    try:
        _, iteraciones, sal, esperado = almacenado.split("$")
        derivado = hashlib.pbkdf2_hmac(
            "sha256", texto.encode("utf-8"), bytes.fromhex(sal), int(iteraciones))
    except ValueError:
        return False
    return hmac.compare_digest(derivado.hex(), esperado)

# reglas y consultas de usuarios

def clave_es_segura(clave):
    """revisa las reglas de la contraseña.

    reglas: mínimo 8 caracteres, una mayúscula, una minúscula y un número.
    devuelve ``(True, "")`` si cumple o ``(False, motivo)`` si no.
    """
    clave = clave or ""
    if len(clave) < LARGO_MINIMO_CLAVE:
        return False, f"La contraseña debe tener al menos {LARGO_MINIMO_CLAVE} caracteres"
    if not any(c.isupper() for c in clave):
        return False, "La contraseña debe incluir al menos una mayúscula"
    if not any(c.islower() for c in clave):
        return False, "La contraseña debe incluir al menos una minúscula"
    if not any(c.isdigit() for c in clave):
        return False, "La contraseña debe incluir al menos un número"
    return True, ""

def usuario_existe(usuario):
    """true si ya hay un usuario con ese nombre (sin distinguir mayúsculas)."""
    with _bd() as cur:
        cur.execute("SELECT 1 FROM usuarios WHERE usuario = ? COLLATE NOCASE",
                    ((usuario or "").strip(),))
        return cur.fetchone() is not None

def crear_usuario(usuario, clave, pregunta, respuesta, rol=ROL_POR_DEFECTO):
    """registra un usuario nuevo.

    devuelve false si faltan datos, el rol no existe, la clave es insegura
    o el usuario ya existe. la interfaz nunca ofrece el rol admin al registrarse.
    """
    usuario = (usuario or "").strip()
    respuesta = (respuesta or "").strip()
    if not usuario or not pregunta or not respuesta or rol not in ROLES_VALIDOS:
        return False
    if not clave_es_segura(clave)[0]:
        return False

    try:
        with _bd() as cur:
            # el not exists evita duplicados aunque cambien las mayúsculas
            cur.execute(
                "INSERT INTO usuarios(usuario, clave, pregunta, respuesta, rol) "
                "SELECT ?,?,?,?,? WHERE NOT EXISTS "
                "(SELECT 1 FROM usuarios WHERE usuario = ? COLLATE NOCASE)",
                (usuario, hashear(clave), pregunta, hashear(_normalizar(respuesta)),
                 rol, usuario))
            return cur.rowcount == 1
    except sqlite3.IntegrityError:
        return False


def verificar_usuario(usuario, clave):
    """true si el usuario existe y la contraseña es correcta.

    si la clave estaba guardada con el formato viejo, la actualiza al nuevo.
    """
    usuario = (usuario or "").strip()
    if not usuario or not clave:
        return False
    with _bd() as cur:
        cur.execute("SELECT clave FROM usuarios WHERE usuario = ? COLLATE NOCASE", (usuario,))
        fila = cur.fetchone()
        if fila is None or not verificar_hash(clave, fila[0]):
            return False
        if _es_hash_viejo(fila[0]):
            cur.execute("UPDATE usuarios SET clave = ? WHERE usuario = ? COLLATE NOCASE",
                        (hashear(clave), usuario))
    return True

def obtener_rol_usuario(usuario):
    """devuelve el rol del usuario, o none si no existe."""
    with _bd() as cur:
        cur.execute("SELECT rol FROM usuarios WHERE usuario = ? COLLATE NOCASE",
                    ((usuario or "").strip(),))
        fila = cur.fetchone()
    return fila[0] if fila else None


def obtener_todos_los_usuarios():
    """devuelve la lista ``(id, usuario, rol)`` de todos los usuarios (panel admin)."""
    with _bd() as cur:
        cur.execute("SELECT id, usuario, rol FROM usuarios ORDER BY id")
        return cur.fetchall()

# recuperación de contraseña

def obtener_pregunta_secreta(usuario):
    """devuelve la pregunta secreta del usuario, o none si no existe."""
    with _bd() as cur:
        cur.execute("SELECT pregunta FROM usuarios WHERE usuario = ? COLLATE NOCASE",
                    ((usuario or "").strip(),))
        fila = cur.fetchone()
    return fila[0] if fila else None

def verificar_respuesta_secreta(usuario, respuesta):
    """true si la respuesta es correcta (ignora espacios y mayúsculas)."""
    with _bd() as cur:
        cur.execute("SELECT respuesta FROM usuarios WHERE usuario = ? COLLATE NOCASE",
                    ((usuario or "").strip(),))
        fila = cur.fetchone()
    if fila is None:
        return False
    return verificar_hash(_normalizar(respuesta or ""), fila[0])

def cambiar_clave(usuario, nueva_clave):
    """cambia la contraseña si cumple las reglas y el usuario existe.

    no comprueba la identidad: antes hay que llamar a verificar_respuesta_secreta.
    """
    if not clave_es_segura(nueva_clave)[0]:
        return False
    with _bd() as cur:
        cur.execute("UPDATE usuarios SET clave = ? WHERE usuario = ? COLLATE NOCASE",
                    (hashear(nueva_clave), (usuario or "").strip()))
        return cur.rowcount == 1

# presupuesto de cada usuario

def convertir_monto(texto):
    """convierte lo escrito en un monto mayor a 0, o devuelve none si no sirve.

    acepta separadores de miles: 1500000, 1.500.000 o 1,500,000.
    """
    limpio = str(texto).strip().replace(" ", "")
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", limpio):
        limpio = re.sub(r"[.,]", "", limpio)
    else:
        limpio = limpio.replace(",", ".")
    try:
        valor = float(limpio)
    except ValueError:
        return None
    if not math.isfinite(valor) or valor <= 0:
        return None
    return valor

def _id_usuario(cur, usuario):
    """devuelve el id de un usuario por su nombre, o none si no existe."""
    cur.execute("SELECT id FROM usuarios WHERE usuario = ? COLLATE NOCASE",
                ((usuario or "").strip(),))
    fila = cur.fetchone()
    return fila[0] if fila else None

def obtener_categorias(usuario):
    """devuelve las categorías del usuario como ``(nombre, presupuesto, gastado)``.

    solo trae las de ese usuario; si no existe o no tiene presupuesto, la lista va vacía.
    """
    with _bd() as cur:
        id_usuario = _id_usuario(cur, usuario)
        if id_usuario is None:
            return []
        cur.execute("SELECT nombre, presupuesto, gastado FROM categorias "
                    "WHERE usuario_id = ? ORDER BY orden, id", (id_usuario,))
        return cur.fetchall()

def generar_presupuesto(usuario, ingreso):
    """arma el presupuesto 50/30/20 del usuario y reemplaza el que tenía.

    borra solo las categorías y gastos de ese usuario. devuelve false si el
    ingreso no es un monto válido o el usuario no existe (y no borra nada).
    """
    monto = convertir_monto(ingreso)
    if monto is None:
        return False
    with _bd() as cur:
        id_usuario = _id_usuario(cur, usuario)
        if id_usuario is None:
            return False
        cur.execute("DELETE FROM categorias WHERE usuario_id = ?", (id_usuario,))
        cur.execute("DELETE FROM gastos WHERE usuario_id = ?", (id_usuario,))
        for orden, (nombre, porcentaje) in enumerate(DISTRIBUCION_50_30_20):
            cur.execute(
                "INSERT INTO categorias(nombre, presupuesto, orden, usuario_id) "
                "VALUES(?,?,?,?)", (nombre, monto * porcentaje / 100, orden, id_usuario))
    return True



#documentación

def generar_documentacion(carpeta=None):
    """crea logica_login.html con pydoc a partir de los docstrings.

    se guarda en la carpeta de este archivo (o en la que se indique).
    devuelve la ruta del html creado.
    """
    import pydoc

    aqui = os.path.dirname(os.path.abspath(__file__))
    carpeta = carpeta or aqui
    if aqui not in sys.path:
        sys.path.insert(0, aqui)
    # pydoc guarda el html en la carpeta actual, así que entramos a la elegida
    anterior = os.getcwd()
    os.chdir(carpeta)
    try:
        with redirect_stdout(io.StringIO()):   # pydoc imprime un aviso, lo ocultamos
            pydoc.writedoc("logica_login")
    finally:
        os.chdir(anterior)
    return os.path.join(carpeta, "logica_login.html")

#al ejecutar este archivo directamente se genera la documentación html
if __name__ == "__main__":
    print("documentación creada en:", generar_documentacion())
=======
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
>>>>>>> 7bd8bf5674ae67b1e45373b0b5fea840cc61ce72
