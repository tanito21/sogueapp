"""lógica de sogueapp: usuarios, roles, presupuesto, gastos y reportes.

este módulo no usa la interfaz gráfica, asi que se puede probar solo
(ver test_login.py). la interfaz (interfaz_login.py) llama a estas funciones.

roles validos: admin, completo, presupuesto, ahorro.

módulos:
    login y usuarios      registro, roles, recuperación de contraseña
    administración        el admin gestiona usuarios (roles, claves, bajas)
    presupuesto           plantillas, porcentajes propios y categorías editables
    módulo 4 (CU.08)      registro de transacciones (gastos)
    módulo 5 (CU.09)      dashboard y reportes
    ahorros               metas de ahorro, aportes y porcentaje completado
"""

import hashlib
import hmac
import io
import math
import os
import re
import sqlite3
import sys
from contextlib import contextmanager, redirect_stdout
from datetime import datetime

def carpeta_base():
    """carpeta donde se guarda la base de datos.

    con el programa normal es la carpeta de este archivo. si está empaquetado
    con pyinstaller (.exe) es la carpeta del .exe: con ``--onefile`` el código
    corre desde una carpeta temporal que se borra al cerrar, y ahí se perdería la base.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

# archivo de la base, junto al programa; las pruebas lo cambian por uno temporal
nombre_bd = os.path.join(carpeta_base(), "soguebase.db")

ROLES_VALIDOS = ("admin", "completo", "presupuesto", "ahorro")
ROL_POR_DEFECTO = "completo"

LARGO_MINIMO_CLAVE = 8
LARGO_MAXIMO_NOMBRE = 40      # nombre de una categoría
LARGO_MAXIMO_CONCEPTO = 100   # detalle de un gasto

# a partir de este uso de la categoría se muestra "precaución"
UMBRAL_PRECAUCION = 0.8
# margen para comparar montos con decimales
TOLERANCIA = 0.01

# plantillas predeterminadas: nombre -> ((categoría, porcentaje), ...)
PLANTILLAS_PRESUPUESTO = {
    "50/30/20": (
        ("Necesidades Básicas", 50),
        ("Deseos y Ocio", 30),
        ("Ahorro e Inversión", 20),
    ),
    "Objetivos": (
        ("Necesidades", 40),
        ("Comida", 25),
        ("Transporte", 15),
        ("Ocio", 10),
        ("Ahorro", 10),
    ),
    "Básico": (
        ("Comidas", 50),
        ("Ahorro", 30),
        ("Ocio", 20),
    ),
}
# cuarto método: el usuario elige sus categorías y porcentajes
METODO_PERSONALIZADO = "Personalizado"
METODO_POR_DEFECTO = "50/30/20"

# nombre viejo, se mantiene por compatibilidad
DISTRIBUCION_50_30_20 = PLANTILLAS_PRESUPUESTO["50/30/20"]

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
    """crea las tablas si faltan y actualiza bases viejas.

    ya no se crea ningún administrador automático: el primero se registra
    desde la interfaz (ver ``existe_admin``). se puede llamar en cada
    arranque: no borra ni duplica nada.
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
        # ingreso mensual de cada usuario y método con el que armó el presupuesto
        cur.execute("""CREATE TABLE IF NOT EXISTS ingresos(
            usuario_id INTEGER PRIMARY KEY,
            ingreso REAL NOT NULL,
            metodo TEXT)""")
        # metas de ahorro y los aportes (depósitos) que se hacen a cada una
        cur.execute("""CREATE TABLE IF NOT EXISTS metas(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            objetivo REAL NOT NULL,
            ahorrado REAL NOT NULL DEFAULT 0,
            fecha_limite TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS aportes(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            meta_id INTEGER NOT NULL,
            monto REAL NOT NULL,
            fecha TEXT,
            nota TEXT)""")
        _actualizar_tablas_viejas(cur)
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

def _hay_admin(cur):
    """true si la base ya tiene al menos un administrador."""
    cur.execute("SELECT 1 FROM usuarios WHERE rol = 'admin' LIMIT 1")
    return cur.fetchone() is not None

def _es_admin(cur, usuario):
    """true si el usuario existe y tiene rol admin."""
    cur.execute("SELECT 1 FROM usuarios WHERE usuario = ? COLLATE NOCASE AND rol = 'admin'",
                ((usuario or "").strip(),))
    return cur.fetchone() is not None

def existe_admin():
    """true si ya hay un administrador registrado.

    mientras no haya ninguno, el registro ofrece el rol admin; cuando ya
    existe, nuevos administradores solo los crea otro administrador.
    """
    with _bd() as cur:
        return _hay_admin(cur)

def es_admin(usuario):
    """true si el usuario existe y es administrador."""
    with _bd() as cur:
        return _es_admin(cur, usuario)

def crear_usuario(usuario, clave, pregunta, respuesta, rol=ROL_POR_DEFECTO, creado_por=None):
    """registra un usuario nuevo.

    devuelve false si faltan datos, el rol no existe, la clave es insegura
    o el usuario ya existe. el rol admin solo se acepta si todavía no hay
    ningún administrador, o si ``creado_por`` es un administrador.
    """
    usuario = (usuario or "").strip()
    respuesta = (respuesta or "").strip()
    if not usuario or not pregunta or not respuesta or rol not in ROLES_VALIDOS:
        return False
    if not clave_es_segura(clave)[0]:
        return False

    try:
        with _bd() as cur:
            if rol == "admin" and _hay_admin(cur) and not _es_admin(cur, creado_por):
                return False
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

# administración de usuarios (solo para el rol admin)
#
# la función del administrador: gestionar las cuentas del sistema. puede ver
# el resumen de cada usuario, cambiar roles, restablecer contraseñas (cuando
# alguien perdió la respuesta secreta), eliminar usuarios con todos sus datos
# y crear otros administradores.

_SIN_PERMISO = "Solo un administrador puede hacer esto"

def _datos_usuario(cur, usuario):
    """devuelve ``(id, rol)`` del usuario, o none si no existe."""
    cur.execute("SELECT id, rol FROM usuarios WHERE usuario = ? COLLATE NOCASE",
                ((usuario or "").strip(),))
    return cur.fetchone()

def cambiar_rol_usuario(actor, usuario, nuevo_rol):
    """cambia el rol de un usuario. devuelve ``(ok, motivo)``.

    solo lo puede hacer un administrador y no puede cambiar su propio rol
    (así nunca se queda el sistema sin administrador).
    """
    if nuevo_rol not in ROLES_VALIDOS:
        return False, "Rol inválido"
    with _bd() as cur:
        if not _es_admin(cur, actor):
            return False, _SIN_PERMISO
        destino = _datos_usuario(cur, usuario)
        if destino is None:
            return False, "El usuario no existe"
        if destino[0] == _id_usuario(cur, actor):
            return False, "No podés cambiar tu propio rol"
        cur.execute("UPDATE usuarios SET rol = ? WHERE id = ?", (nuevo_rol, destino[0]))
    return True, ""

def restablecer_clave_usuario(actor, usuario, nueva_clave):
    """el admin le pone una contraseña nueva a un usuario. devuelve ``(ok, motivo)``."""
    ok, motivo = clave_es_segura(nueva_clave)
    if not ok:
        return False, motivo
    with _bd() as cur:
        if not _es_admin(cur, actor):
            return False, _SIN_PERMISO
        destino = _datos_usuario(cur, usuario)
        if destino is None:
            return False, "El usuario no existe"
        cur.execute("UPDATE usuarios SET clave = ? WHERE id = ?",
                    (hashear(nueva_clave), destino[0]))
    return True, ""

def eliminar_usuario(actor, usuario):
    """elimina un usuario con su presupuesto, ingreso y gastos. devuelve ``(ok, motivo)``.

    un administrador no puede eliminarse a sí mismo.
    """
    with _bd() as cur:
        if not _es_admin(cur, actor):
            return False, _SIN_PERMISO
        destino = _datos_usuario(cur, usuario)
        if destino is None:
            return False, "El usuario no existe"
        if destino[0] == _id_usuario(cur, actor):
            return False, "No podés eliminar tu propia cuenta"
        for tabla in ("categorias", "gastos", "ingresos", "aportes", "metas"):
            cur.execute(f"DELETE FROM {tabla} WHERE usuario_id = ?", (destino[0],))
        cur.execute("DELETE FROM usuarios WHERE id = ?", (destino[0],))
    return True, ""

def obtener_resumen_usuarios(actor):
    """resumen de todas las cuentas para el panel del administrador.

    devuelve una lista de ``(id, usuario, rol, cantidad_categorias,
    presupuesto_total, gastado_total)``, o none si ``actor`` no es admin.
    """
    with _bd() as cur:
        if not _es_admin(cur, actor):
            return None
        cur.execute(
            "SELECT u.id, u.usuario, u.rol, COUNT(c.id), "
            "COALESCE(SUM(c.presupuesto), 0), COALESCE(SUM(c.gastado), 0) "
            "FROM usuarios u LEFT JOIN categorias c ON c.usuario_id = u.id "
            "GROUP BY u.id ORDER BY u.id")
        return cur.fetchall()

# formatos y conversiones

def formatear_gs(valor):
    """da formato de guaraníes con punto de miles: ``Gs. 1.500.000``."""
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        numero = 0.0
    return "Gs. " + f"{numero:,.0f}".replace(",", ".")

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

def convertir_porcentaje(texto):
    """convierte lo escrito en un porcentaje entre 0 (sin incluir) y 100, o none.

    acepta ``25``, ``12,5`` o ``30%``.
    """
    limpio = str(texto).strip().replace("%", "").replace(" ", "").replace(",", ".")
    try:
        valor = float(limpio)
    except ValueError:
        return None
    if not math.isfinite(valor) or valor <= 0 or valor > 100:
        return None
    return valor

def _id_usuario(cur, usuario):
    """devuelve el id de un usuario por su nombre, o none si no existe."""
    cur.execute("SELECT id FROM usuarios WHERE usuario = ? COLLATE NOCASE",
                ((usuario or "").strip(),))
    fila = cur.fetchone()
    return fila[0] if fila else None

# presupuesto de cada usuario

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

def describir_plantilla(metodo):
    """texto corto con el reparto de un método, para mostrar en la interfaz."""
    if metodo == METODO_PERSONALIZADO:
        return "Vos elegís las categorías y los porcentajes (deben sumar 100%)."
    plantilla = PLANTILLAS_PRESUPUESTO.get(metodo)
    if plantilla is None:
        return ""
    return "  ·  ".join(f"{nombre} {porcentaje}%" for nombre, porcentaje in plantilla)

def _limpiar_nombre(nombre):
    """quita espacios de más en el nombre de una categoría."""
    return " ".join(str(nombre or "").split())

def _motivo_nombre_invalido(nombre, tipo="categoría"):
    """devuelve el motivo si el nombre no sirve, o un texto vacío si está bien.

    ``tipo`` es lo que se está nombrando (categoría o meta), solo para el mensaje.
    """
    if not nombre:
        return f"Escribí un nombre para la {tipo}"
    if len(nombre) > LARGO_MAXIMO_NOMBRE:
        return f"El nombre es demasiado largo (máximo {LARGO_MAXIMO_NOMBRE} caracteres)"
    return ""

def validar_distribucion(distribucion):
    """revisa un reparto personalizado ``[(nombre, porcentaje), ...]``.

    reglas: al menos una categoría, nombres válidos y sin repetir, cada
    porcentaje entre 0 y 100 y suma total de 100. devuelve
    ``(ok, motivo, lista)`` con la lista ya limpia ``[(nombre, float)]``.
    """
    if not distribucion:
        return False, "Agregá al menos una categoría", []
    resultado = []
    vistos = set()
    total = 0.0
    for item in distribucion:
        try:
            nombre, porcentaje = item
        except (TypeError, ValueError):
            return False, "Formato de categoría inválido", []
        nombre = _limpiar_nombre(nombre)
        motivo = _motivo_nombre_invalido(nombre)
        if motivo:
            return False, motivo, []
        if nombre.lower() in vistos:
            return False, f"La categoría «{nombre}» está repetida", []
        vistos.add(nombre.lower())
        valor = convertir_porcentaje(porcentaje)
        if valor is None:
            return False, f"El porcentaje de «{nombre}» debe ser un número entre 0 y 100", []
        resultado.append((nombre, valor))
        total += valor
    if abs(total - 100) > TOLERANCIA:
        return False, f"Los porcentajes suman {round(total, 2):g}% y deben sumar 100%", []
    return True, "", resultado

def generar_presupuesto(usuario, ingreso, metodo=METODO_POR_DEFECTO, distribucion=None):
    """arma el presupuesto del usuario y reemplaza el que tenía.

    ``metodo`` puede ser una plantilla de ``PLANTILLAS_PRESUPUESTO`` (50/30/20,
    Objetivos, Básico) o ``Personalizado``; en ese caso hay que pasar
    ``distribucion`` como ``[(nombre, porcentaje), ...]`` que sume 100.

    borra solo las categorías y gastos de ese usuario. devuelve false si el
    ingreso no es un monto válido, el método o el reparto no sirven, o el
    usuario no existe (y no borra nada).
    """
    monto = convertir_monto(ingreso)
    if monto is None:
        return False
    if metodo == METODO_PERSONALIZADO:
        ok, _, reparto = validar_distribucion(distribucion)
        if not ok:
            return False
    elif metodo in PLANTILLAS_PRESUPUESTO:
        reparto = list(PLANTILLAS_PRESUPUESTO[metodo])
    else:
        return False

    with _bd() as cur:
        id_usuario = _id_usuario(cur, usuario)
        if id_usuario is None:
            return False
        cur.execute("DELETE FROM categorias WHERE usuario_id = ?", (id_usuario,))
        cur.execute("DELETE FROM gastos WHERE usuario_id = ?", (id_usuario,))
        cur.execute("INSERT OR REPLACE INTO ingresos(usuario_id, ingreso, metodo) VALUES(?,?,?)",
                    (id_usuario, monto, metodo))
        for orden, (nombre, porcentaje) in enumerate(reparto):
            cur.execute(
                "INSERT INTO categorias(nombre, presupuesto, orden, usuario_id) "
                "VALUES(?,?,?,?)", (nombre, monto * porcentaje / 100, orden, id_usuario))
    return True

def _ingreso_de(cur, id_usuario):
    """ingreso del usuario; si es una base vieja sin ingreso, la suma de sus categorías.

    devuelve none si no tiene ni ingreso ni categorías.
    """
    cur.execute("SELECT ingreso FROM ingresos WHERE usuario_id = ?", (id_usuario,))
    fila = cur.fetchone()
    if fila:
        return fila[0]
    cur.execute("SELECT COUNT(*), COALESCE(SUM(presupuesto), 0) FROM categorias "
                "WHERE usuario_id = ?", (id_usuario,))
    cantidad, total = cur.fetchone()
    return total if cantidad else None

def _total_asignado(cur, id_usuario, excepto_id=None):
    """suma de lo asignado a las categorías del usuario (sin contar una, si se indica)."""
    sql = "SELECT COALESCE(SUM(presupuesto), 0) FROM categorias WHERE usuario_id = ?"
    params = [id_usuario]
    if excepto_id is not None:
        sql += " AND id <> ?"
        params.append(excepto_id)
    cur.execute(sql, params)
    return cur.fetchone()[0]

def _buscar_categoria(cur, id_usuario, nombre):
    """devuelve ``(id, nombre, presupuesto, gastado)`` de una categoría, o none."""
    cur.execute("SELECT id, nombre, presupuesto, gastado FROM categorias "
                "WHERE usuario_id = ? AND nombre = ? COLLATE NOCASE",
                (id_usuario, _limpiar_nombre(nombre)))
    return cur.fetchone()

def obtener_ingreso(usuario):
    """devuelve el ingreso mensual del usuario, o none si todavía no armó presupuesto."""
    with _bd() as cur:
        id_usuario = _id_usuario(cur, usuario)
        if id_usuario is None:
            return None
        return _ingreso_de(cur, id_usuario)

def cambiar_ingreso(usuario, nuevo_ingreso):
    """actualiza el ingreso mensual sin tocar las categorías. devuelve ``(ok, motivo)``.

    el nuevo ingreso no puede ser menor a lo que ya está asignado a categorías.
    """
    monto = convertir_monto(nuevo_ingreso)
    if monto is None:
        return False, "El ingreso debe ser un número mayor a 0"
    with _bd() as cur:
        id_usuario = _id_usuario(cur, usuario)
        if id_usuario is None:
            return False, "El usuario no existe"
        asignado = _total_asignado(cur, id_usuario)
        if monto < asignado - TOLERANCIA:
            return False, ("El ingreso no puede ser menor a lo ya asignado "
                           f"({formatear_gs(asignado)})")
        cur.execute("UPDATE ingresos SET ingreso = ? WHERE usuario_id = ?", (monto, id_usuario))
        if cur.rowcount == 0:
            cur.execute("INSERT INTO ingresos(usuario_id, ingreso, metodo) VALUES(?,?,?)",
                        (id_usuario, monto, "Manual"))
    return True, ""

def agregar_categoria(usuario, nombre, presupuesto):
    """agrega una categoría nueva (streaming, movilidad, etc). devuelve ``(ok, motivo)``.

    el monto no puede superar lo que queda sin asignar del ingreso, y el
    nombre no se puede repetir.
    """
    nombre = _limpiar_nombre(nombre)
    motivo = _motivo_nombre_invalido(nombre)
    if motivo:
        return False, motivo
    monto = convertir_monto(presupuesto)
    if monto is None:
        return False, "El monto debe ser un número mayor a 0"
    with _bd() as cur:
        id_usuario = _id_usuario(cur, usuario)
        if id_usuario is None:
            return False, "El usuario no existe"
        ingreso = _ingreso_de(cur, id_usuario)
        if ingreso is None:
            return False, "Primero generá un presupuesto con tu ingreso mensual"
        if _buscar_categoria(cur, id_usuario, nombre) is not None:
            return False, "Ya existe una categoría con ese nombre"
        libre = ingreso - _total_asignado(cur, id_usuario)
        if monto > libre + TOLERANCIA:
            return False, ("El monto supera lo que queda sin asignar "
                           f"({formatear_gs(max(libre, 0))})")
        cur.execute("SELECT COALESCE(MAX(orden), -1) + 1 FROM categorias WHERE usuario_id = ?",
                    (id_usuario,))
        orden = cur.fetchone()[0]
        cur.execute("INSERT INTO categorias(nombre, presupuesto, orden, usuario_id) "
                    "VALUES(?,?,?,?)", (nombre, monto, orden, id_usuario))
    return True, ""

def editar_categoria(usuario, nombre_actual, nuevo_nombre=None, nuevo_presupuesto=None):
    """cambia el nombre y/o el monto de una categoría. devuelve ``(ok, motivo)``.

    pasar none en un dato lo deja como está. si se renombra, los gastos ya
    registrados pasan al nombre nuevo. el total asignado no puede superar el ingreso.
    """
    with _bd() as cur:
        id_usuario = _id_usuario(cur, usuario)
        if id_usuario is None:
            return False, "El usuario no existe"
        fila = _buscar_categoria(cur, id_usuario, nombre_actual)
        if fila is None:
            return False, "La categoría no existe"
        id_cat, nombre_bd, presupuesto_bd, _ = fila

        nombre_final = nombre_bd if nuevo_nombre is None else _limpiar_nombre(nuevo_nombre)
        motivo = _motivo_nombre_invalido(nombre_final)
        if motivo:
            return False, motivo
        repetida = _buscar_categoria(cur, id_usuario, nombre_final)
        if repetida is not None and repetida[0] != id_cat:
            return False, "Ya existe una categoría con ese nombre"

        monto_final = presupuesto_bd
        if nuevo_presupuesto is not None:
            monto_final = convertir_monto(nuevo_presupuesto)
            if monto_final is None:
                return False, "El monto debe ser un número mayor a 0"
        ingreso = _ingreso_de(cur, id_usuario)
        if ingreso is not None:
            otras = _total_asignado(cur, id_usuario, excepto_id=id_cat)
            if otras + monto_final > ingreso + TOLERANCIA:
                return False, ("El monto supera lo que queda sin asignar "
                               f"({formatear_gs(max(ingreso - otras, 0))})")

        cur.execute("UPDATE categorias SET nombre = ?, presupuesto = ? WHERE id = ?",
                    (nombre_final, monto_final, id_cat))
        if nombre_final != nombre_bd:
            cur.execute("UPDATE gastos SET categoria = ? WHERE usuario_id = ? AND categoria = ?",
                        (nombre_final, id_usuario, nombre_bd))
    return True, ""

def eliminar_categoria(usuario, nombre):
    """elimina una categoría y los gastos registrados en ella. devuelve ``(ok, motivo)``."""
    with _bd() as cur:
        id_usuario = _id_usuario(cur, usuario)
        if id_usuario is None:
            return False, "El usuario no existe"
        fila = _buscar_categoria(cur, id_usuario, nombre)
        if fila is None:
            return False, "La categoría no existe"
        cur.execute("DELETE FROM gastos WHERE usuario_id = ? AND categoria = ?",
                    (id_usuario, fila[1]))
        cur.execute("DELETE FROM categorias WHERE id = ?", (fila[0],))
    return True, ""

# módulo 4 - CU.08 registro de transacciones (gastos)

def consultar_categorias_activas(usuario):
    """CU.08.01 - consultar categorías activas.

    devuelve ``[(nombre, presupuesto, gastado, disponible)]`` de las categorías
    del usuario, para elegir en qué categoría se carga un gasto.
    """
    return [(nombre, presupuesto, gastado, presupuesto - gastado)
            for nombre, presupuesto, gastado in obtener_categorias(usuario)]

def validar_detalle_gasto(concepto, monto):
    """CU.08.02 - ingresar detalle de gasto (validación).

    el concepto no puede estar vacío ni pasar de 100 caracteres y el monto
    debe ser mayor a 0. devuelve ``(ok, motivo, monto_numerico)``.
    """
    concepto = " ".join(str(concepto or "").split())
    if not concepto:
        return False, "Escribí en qué gastaste (concepto)", None
    if len(concepto) > LARGO_MAXIMO_CONCEPTO:
        return False, f"El concepto es demasiado largo (máximo {LARGO_MAXIMO_CONCEPTO} caracteres)", None
    valor = convertir_monto(monto)
    if valor is None:
        return False, "El monto debe ser un número mayor a 0", None
    return True, "", valor

def actualizar_saldo_categoria(cur, id_categoria, monto):
    """CU.08.03 - actualizar saldo de categoría (uso interno de ``registrar_gasto``).

    suma el gasto al acumulado de la categoría y devuelve el nuevo total gastado.
    """
    cur.execute("UPDATE categorias SET gastado = gastado + ? WHERE id = ?", (monto, id_categoria))
    cur.execute("SELECT gastado FROM categorias WHERE id = ?", (id_categoria,))
    return cur.fetchone()[0]

def evaluar_alerta_limite(categoria, presupuesto, gastado):
    """CU.08.04 - alerta de límite superado.

    devuelve el texto de la alerta si lo gastado supera el presupuesto de la
    categoría, o un texto vacío si todavía está dentro del límite.
    """
    exceso = gastado - presupuesto
    if exceso > 0.005:
        return f"Superaste el presupuesto de «{categoria}» por {formatear_gs(exceso)}."
    return ""

def _gasto_fallido(motivo):
    """resultado de ``registrar_gasto`` cuando algo falla."""
    return {"ok": False, "motivo": motivo, "categoria": None, "presupuesto": 0.0,
            "gastado": 0.0, "disponible": 0.0, "alerta": ""}

def registrar_gasto(usuario, categoria, concepto, monto, fecha=None):
    """registra un gasto en una categoría del usuario (CU.08.02 a CU.08.04).

    valida el detalle, suma el monto a lo gastado de la categoría, guarda el
    movimiento en el historial y evalúa la alerta de límite. un gasto que
    supera el presupuesto igual se registra, pero devuelve la alerta.

    devuelve un diccionario con ``ok``, ``motivo``, ``categoria``,
    ``presupuesto``, ``gastado``, ``disponible`` y ``alerta``.
    """
    ok, motivo, valor = validar_detalle_gasto(concepto, monto)
    if not ok:
        return _gasto_fallido(motivo)
    concepto = " ".join(str(concepto).split())
    fecha = fecha or datetime.now().strftime("%d/%m/%Y")
    with _bd() as cur:
        id_usuario = _id_usuario(cur, usuario)
        if id_usuario is None:
            return _gasto_fallido("El usuario no existe")
        fila = _buscar_categoria(cur, id_usuario, categoria)
        if fila is None:
            return _gasto_fallido("La categoría no existe")
        id_cat, nombre, presupuesto, _ = fila
        nuevo_gastado = actualizar_saldo_categoria(cur, id_cat, valor)
        cur.execute("INSERT INTO gastos(categoria, concepto, monto, fecha, usuario_id) "
                    "VALUES(?,?,?,?,?)", (nombre, concepto, valor, fecha, id_usuario))
    return {"ok": True, "motivo": "", "categoria": nombre, "presupuesto": presupuesto,
            "gastado": nuevo_gastado, "disponible": presupuesto - nuevo_gastado,
            "alerta": evaluar_alerta_limite(nombre, presupuesto, nuevo_gastado)}

def _normalizar_limite(limite):
    """cantidad de filas a traer: entre 1 y 100 (si no es válida, 10)."""
    try:
        limite = int(limite)
    except (TypeError, ValueError):
        return 10
    if limite < 1:
        return 10
    return min(limite, 100)

# módulo 5 - CU.09 dashboard y reportes

def _estado_categoria(presupuesto, gastado):
    """devuelve ``excedido``, ``precaucion`` u ``ok`` según el uso de la categoría."""
    if gastado > presupuesto + 0.005:
        return "excedido"
    if presupuesto > 0 and gastado / presupuesto > UMBRAL_PRECAUCION:
        return "precaucion"
    return "ok"

def consultar_resumen_categorias(usuario):
    """CU.09.01 - consultar resumen de categorías.

    devuelve un diccionario con ``ingreso``, ``total_presupuestado``,
    ``total_gastado``, ``total_disponible``, ``sin_asignar``,
    ``porcentaje_usado`` y ``categorias``: una lista de diccionarios con
    ``nombre``, ``presupuesto``, ``gastado``, ``disponible``, ``porcentaje``
    (0 a 1 o más) y ``estado`` (ok, precaucion o excedido).
    """
    categorias = []
    total_presupuesto = 0.0
    total_gastado = 0.0
    for nombre, presupuesto, gastado in obtener_categorias(usuario):
        categorias.append({
            "nombre": nombre,
            "presupuesto": presupuesto,
            "gastado": gastado,
            "disponible": presupuesto - gastado,
            "porcentaje": gastado / presupuesto if presupuesto > 0 else 0.0,
            "estado": _estado_categoria(presupuesto, gastado),
        })
        total_presupuesto += presupuesto
        total_gastado += gastado
    ingreso = obtener_ingreso(usuario) or 0.0
    return {
        "ingreso": ingreso,
        "total_presupuestado": total_presupuesto,
        "total_gastado": total_gastado,
        "total_disponible": total_presupuesto - total_gastado,
        "sin_asignar": max(ingreso - total_presupuesto, 0.0),
        "porcentaje_usado": total_gastado / total_presupuesto if total_presupuesto > 0 else 0.0,
        "categorias": categorias,
    }

def consultar_historial_reciente(usuario, limite=10):
    """CU.09.02 - consultar historial reciente.

    devuelve los últimos gastos del usuario, del más nuevo al más viejo, como
    ``(fecha, categoria, concepto, monto)``. ``limite`` va de 1 a 100 (si no
    es válido se usan 10).
    """
    limite = _normalizar_limite(limite)
    with _bd() as cur:
        id_usuario = _id_usuario(cur, usuario)
        if id_usuario is None:
            return []
        cur.execute("SELECT fecha, categoria, concepto, monto FROM gastos "
                    "WHERE usuario_id = ? ORDER BY id DESC LIMIT ?", (id_usuario, limite))
        return cur.fetchall()

# ahorros: metas de ahorro y aportes
#
# una meta tiene un nombre, un monto objetivo y, si se quiere, una fecha
# límite. el usuario le va sumando dinero (aportes) y se calcula cuánto lleva
# ahorrado, cuánto falta y el porcentaje completado.

FORMATO_FECHA = "%d/%m/%Y"

def _convertir_fecha(texto):
    """convierte ``dd/mm/aaaa`` en fecha, o devuelve none si no sirve."""
    try:
        return datetime.strptime(str(texto).strip(), FORMATO_FECHA).date()
    except ValueError:
        return None

def _validar_fecha_limite(texto, hoy=None):
    """revisa la fecha límite de una meta (opcional, formato dd/mm/aaaa, no pasada).

    devuelve ``(ok, motivo, fecha_texto)``; si se deja vacía, ``fecha_texto`` es none.
    """
    texto = str(texto or "").strip()
    if not texto:
        return True, "", None
    fecha = _convertir_fecha(texto)
    if fecha is None:
        return False, "La fecha debe tener el formato dd/mm/aaaa", None
    if fecha < (hoy or datetime.now().date()):
        return False, "La fecha límite no puede estar en el pasado", None
    return True, "", fecha.strftime(FORMATO_FECHA)

def _buscar_meta(cur, id_usuario, nombre):
    """devuelve ``(id, nombre, objetivo, ahorrado, fecha_limite)`` de una meta, o none."""
    cur.execute("SELECT id, nombre, objetivo, ahorrado, fecha_limite FROM metas "
                "WHERE usuario_id = ? AND nombre = ? COLLATE NOCASE",
                (id_usuario, _limpiar_nombre(nombre)))
    return cur.fetchone()

def _estado_meta(nombre, objetivo, ahorrado, fecha_limite, hoy=None):
    """arma el diccionario de una meta con sus porcentajes y su estado.

    claves: ``nombre``, ``objetivo``, ``ahorrado``, ``faltante``, ``porcentaje``
    (0 a 1, o más si se pasó del objetivo), ``completada``, ``fecha_limite``,
    ``dias_restantes`` (none sin fecha; negativo si ya venció) y ``estado``
    (completada, vencida o en_curso).
    """
    completada = ahorrado >= objetivo - 0.005
    dias = None
    if fecha_limite:
        fecha = _convertir_fecha(fecha_limite)
        if fecha is not None:
            dias = (fecha - (hoy or datetime.now().date())).days
    if completada:
        estado = "completada"
    elif dias is not None and dias < 0:
        estado = "vencida"
    else:
        estado = "en_curso"
    return {
        "nombre": nombre,
        "objetivo": objetivo,
        "ahorrado": ahorrado,
        "faltante": max(objetivo - ahorrado, 0.0),
        "porcentaje": ahorrado / objetivo if objetivo > 0 else 0.0,
        "completada": completada,
        "fecha_limite": fecha_limite,
        "dias_restantes": dias,
        "estado": estado,
    }

def crear_meta(usuario, nombre, objetivo, fecha_limite=None, hoy=None):
    """crea una meta de ahorro nueva. devuelve ``(ok, motivo)``.

    el nombre no se puede repetir, el objetivo debe ser mayor a 0 y la fecha
    límite (opcional) va como ``dd/mm/aaaa`` y no puede estar en el pasado.
    """
    nombre = _limpiar_nombre(nombre)
    motivo = _motivo_nombre_invalido(nombre, "meta")
    if motivo:
        return False, motivo
    monto = convertir_monto(objetivo)
    if monto is None:
        return False, "El objetivo debe ser un número mayor a 0"
    ok, motivo, fecha = _validar_fecha_limite(fecha_limite, hoy)
    if not ok:
        return False, motivo
    with _bd() as cur:
        id_usuario = _id_usuario(cur, usuario)
        if id_usuario is None:
            return False, "El usuario no existe"
        if _buscar_meta(cur, id_usuario, nombre) is not None:
            return False, "Ya existe una meta con ese nombre"
        cur.execute("INSERT INTO metas(usuario_id, nombre, objetivo, ahorrado, fecha_limite) "
                    "VALUES(?,?,?,0,?)", (id_usuario, nombre, monto, fecha))
    return True, ""

def editar_meta(usuario, nombre_actual, nuevo_nombre=None, nuevo_objetivo=None,
                fecha_limite=None, hoy=None):
    """cambia nombre, objetivo y/o fecha límite de una meta. devuelve ``(ok, motivo)``.

    none en un dato lo deja como está; en ``fecha_limite``, un texto vacío
    quita la fecha. lo ahorrado y los aportes no se tocan. si se baja el
    objetivo por debajo de lo ahorrado, la meta queda completada.
    """
    with _bd() as cur:
        id_usuario = _id_usuario(cur, usuario)
        if id_usuario is None:
            return False, "El usuario no existe"
        fila = _buscar_meta(cur, id_usuario, nombre_actual)
        if fila is None:
            return False, "La meta no existe"
        id_meta, nombre_bd, objetivo_bd, _, fecha_bd = fila

        nombre_final = nombre_bd if nuevo_nombre is None else _limpiar_nombre(nuevo_nombre)
        motivo = _motivo_nombre_invalido(nombre_final, "meta")
        if motivo:
            return False, motivo
        repetida = _buscar_meta(cur, id_usuario, nombre_final)
        if repetida is not None and repetida[0] != id_meta:
            return False, "Ya existe una meta con ese nombre"

        objetivo_final = objetivo_bd
        if nuevo_objetivo is not None:
            objetivo_final = convertir_monto(nuevo_objetivo)
            if objetivo_final is None:
                return False, "El objetivo debe ser un número mayor a 0"

        fecha_final = fecha_bd
        if fecha_limite is not None:
            ok, motivo, fecha_final = _validar_fecha_limite(fecha_limite, hoy)
            if not ok:
                # una fecha que ya estaba guardada (aunque venciera) se puede conservar
                fecha_pedida = _convertir_fecha(fecha_limite)
                if fecha_pedida is not None and fecha_pedida.strftime(FORMATO_FECHA) == fecha_bd:
                    fecha_final = fecha_bd
                else:
                    return False, motivo

        cur.execute("UPDATE metas SET nombre = ?, objetivo = ?, fecha_limite = ? WHERE id = ?",
                    (nombre_final, objetivo_final, fecha_final, id_meta))
    return True, ""

def eliminar_meta(usuario, nombre):
    """elimina una meta junto con todos sus aportes. devuelve ``(ok, motivo)``."""
    with _bd() as cur:
        id_usuario = _id_usuario(cur, usuario)
        if id_usuario is None:
            return False, "El usuario no existe"
        fila = _buscar_meta(cur, id_usuario, nombre)
        if fila is None:
            return False, "La meta no existe"
        cur.execute("DELETE FROM aportes WHERE meta_id = ?", (fila[0],))
        cur.execute("DELETE FROM metas WHERE id = ?", (fila[0],))
    return True, ""

def _aporte_fallido(motivo):
    """resultado de ``agregar_aporte`` cuando algo falla."""
    return {"ok": False, "motivo": motivo, "nombre": None, "objetivo": 0.0, "ahorrado": 0.0,
            "faltante": 0.0, "porcentaje": 0.0, "completada": False, "fecha_limite": None,
            "dias_restantes": None, "estado": None, "recien_completada": False}

def agregar_aporte(usuario, meta, monto, nota="", fecha=None, hoy=None):
    """suma dinero a una meta de ahorro y lo guarda en el historial de aportes.

    ``nota`` es opcional (máximo 100 caracteres). se puede aportar más que lo
    que falta: la meta queda completada y el porcentaje pasa de 100%.

    devuelve el diccionario de ``_estado_meta`` más ``ok``, ``motivo`` y
    ``recien_completada`` (true si con este aporte se completó la meta).
    """
    valor = convertir_monto(monto)
    if valor is None:
        return _aporte_fallido("El monto debe ser un número mayor a 0")
    nota = " ".join(str(nota or "").split())
    if len(nota) > LARGO_MAXIMO_CONCEPTO:
        return _aporte_fallido(f"La nota es demasiado larga (máximo {LARGO_MAXIMO_CONCEPTO} caracteres)")
    fecha = fecha or datetime.now().strftime(FORMATO_FECHA)
    with _bd() as cur:
        id_usuario = _id_usuario(cur, usuario)
        if id_usuario is None:
            return _aporte_fallido("El usuario no existe")
        fila = _buscar_meta(cur, id_usuario, meta)
        if fila is None:
            return _aporte_fallido("La meta no existe")
        id_meta, nombre, objetivo, ahorrado_antes, fecha_limite = fila
        cur.execute("UPDATE metas SET ahorrado = ahorrado + ? WHERE id = ?", (valor, id_meta))
        cur.execute("SELECT ahorrado FROM metas WHERE id = ?", (id_meta,))
        ahorrado = cur.fetchone()[0]
        cur.execute("INSERT INTO aportes(usuario_id, meta_id, monto, fecha, nota) VALUES(?,?,?,?,?)",
                    (id_usuario, id_meta, valor, fecha, nota))
    resultado = _estado_meta(nombre, objetivo, ahorrado, fecha_limite, hoy)
    resultado["ok"] = True
    resultado["motivo"] = ""
    resultado["recien_completada"] = (resultado["completada"]
                                      and ahorrado_antes < objetivo - 0.005)
    return resultado

def obtener_metas(usuario, hoy=None):
    """devuelve las metas del usuario (diccionarios de ``_estado_meta``), en orden de creación."""
    with _bd() as cur:
        id_usuario = _id_usuario(cur, usuario)
        if id_usuario is None:
            return []
        cur.execute("SELECT nombre, objetivo, ahorrado, fecha_limite FROM metas "
                    "WHERE usuario_id = ? ORDER BY id", (id_usuario,))
        filas = cur.fetchall()
    return [_estado_meta(n, o, a, f, hoy) for n, o, a, f in filas]

def consultar_resumen_ahorros(usuario, hoy=None):
    """resumen de todas las metas del usuario.

    devuelve un diccionario con ``cantidad``, ``completadas``,
    ``total_objetivo``, ``total_ahorrado``, ``total_faltante``,
    ``porcentaje_total`` (0 a 1: lo ahorrado hacia cada objetivo, sin contar
    lo que se pasó) y ``metas`` (la lista de ``obtener_metas``).
    """
    metas = obtener_metas(usuario, hoy)
    total_objetivo = sum(m["objetivo"] for m in metas)
    # lo que se aportó de más a una meta no completa a las otras
    cubierto = sum(min(m["ahorrado"], m["objetivo"]) for m in metas)
    return {
        "cantidad": len(metas),
        "completadas": sum(1 for m in metas if m["completada"]),
        "total_objetivo": total_objetivo,
        "total_ahorrado": sum(m["ahorrado"] for m in metas),
        "total_faltante": sum(m["faltante"] for m in metas),
        "porcentaje_total": cubierto / total_objetivo if total_objetivo > 0 else 0.0,
        "metas": metas,
    }

def consultar_aportes_recientes(usuario, limite=10):
    """últimos aportes del usuario, del más nuevo al más viejo.

    devuelve ``(fecha, meta, monto, nota)``. ``limite`` va de 1 a 100 (si no
    es válido se usan 10).
    """
    limite = _normalizar_limite(limite)
    with _bd() as cur:
        id_usuario = _id_usuario(cur, usuario)
        if id_usuario is None:
            return []
        cur.execute("SELECT a.fecha, m.nombre, a.monto, a.nota FROM aportes a "
                    "JOIN metas m ON m.id = a.meta_id "
                    "WHERE a.usuario_id = ? ORDER BY a.id DESC LIMIT ?", (id_usuario, limite))
        return cur.fetchall()


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