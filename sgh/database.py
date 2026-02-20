"""
database.py - Capa de Acceso a Datos (DAL)
Sistema de Gestión Hotelera (SGH)
"""
import sqlite3
import json
from datetime import datetime
from contextlib import contextmanager

DB_NAME = "hotel.db"


@contextmanager
def get_connection():
    """Context manager para conexiones seguras a SQLite."""
    conn = sqlite3.connect(DB_NAME, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Inicializa todas las tablas y datos por defecto."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS Configuracion (
                id            INTEGER PRIMARY KEY,
                nombre_hotel  TEXT    DEFAULT 'Mi Hotel',
                tasa_dolar_bs REAL    DEFAULT 36.0,
                usuario_activo TEXT,
                turno_inicio  TEXT
            );

            CREATE TABLE IF NOT EXISTS Usuarios (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT    UNIQUE NOT NULL,
                password TEXT    NOT NULL,
                nombre   TEXT    NOT NULL,
                rol      TEXT    DEFAULT 'recepcionista',
                activo   INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS Huespedes (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                documento        TEXT    UNIQUE NOT NULL,
                nombres          TEXT    NOT NULL,
                telefono         TEXT,
                fecha_nacimiento TEXT,
                nacionalidad     TEXT    DEFAULT 'Venezolano',
                profesion        TEXT,
                vehiculo         TEXT,
                saldo_acumulado  REAL    DEFAULT 0.0
            );

            CREATE TABLE IF NOT EXISTS Habitaciones (
                numero      INTEGER PRIMARY KEY,
                tipo        TEXT    DEFAULT 'Estándar',
                descripcion TEXT,
                precio_usd  REAL    DEFAULT 30.0,
                estado      TEXT    DEFAULT 'Libre'
            );

            CREATE TABLE IF NOT EXISTS Registros (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                huesped_principal_id  INTEGER NOT NULL,
                habitacion_id         INTEGER NOT NULL,
                fecha_entrada         TEXT    NOT NULL,
                fecha_salida_prevista TEXT    NOT NULL,
                estado                TEXT    DEFAULT 'Activo',
                notas                 TEXT,
                FOREIGN KEY(huesped_principal_id) REFERENCES Huespedes(id),
                FOREIGN KEY(habitacion_id)        REFERENCES Habitaciones(numero)
            );

            CREATE TABLE IF NOT EXISTS Acompanantes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                registro_id INTEGER NOT NULL,
                huesped_id  INTEGER NOT NULL,
                FOREIGN KEY(registro_id) REFERENCES Registros(id),
                FOREIGN KEY(huesped_id)  REFERENCES Huespedes(id)
            );

            CREATE TABLE IF NOT EXISTS Transacciones (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                registro_id INTEGER,
                monto_usd   REAL    NOT NULL,
                tasa_cambio REAL    NOT NULL,
                monto_bs    REAL    NOT NULL,
                metodo_pago TEXT    NOT NULL,
                tipo        TEXT    NOT NULL,
                fecha_hora  TEXT    NOT NULL,
                usuario_id  INTEGER,
                referencia  TEXT,
                descripcion TEXT
            );

            CREATE TABLE IF NOT EXISTS CierresTurno (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id     INTEGER,
                fecha_apertura TEXT,
                fecha_cierre   TEXT,
                total_usd      REAL,
                total_bs       REAL,
                resumen        TEXT
            );
        """)

        # Config por defecto
        if conn.execute("SELECT COUNT(*) FROM Configuracion").fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO Configuracion (nombre_hotel, tasa_dolar_bs) VALUES (?,?)",
                ("Mi Hotel", 36.0)
            )

        # Usuario admin por defecto
        if conn.execute("SELECT COUNT(*) FROM Usuarios").fetchone()[0] == 0:
            users = [
                ("admin",       "admin123",   "Administrador",  "admin"),
                ("recepcion1",  "hotel2024",  "María González", "recepcionista"),
            ]
            conn.executemany(
                "INSERT INTO Usuarios (username, password, nombre, rol) VALUES (?,?,?,?)",
                users
            )

        # 39 habitaciones por defecto
        if conn.execute("SELECT COUNT(*) FROM Habitaciones").fetchone()[0] == 0:
            rooms = []
            for i in range(1, 40):
                if i <= 12:
                    tipo, precio = "Estándar",  25.0
                elif i <= 28:
                    tipo, precio = "Doble",     35.0
                elif i <= 36:
                    tipo, precio = "Matrimonial", 45.0
                else:
                    tipo, precio = "Suite",     80.0
                rooms.append((i, tipo, f"Habitación {i}", precio, "Libre"))
            conn.executemany(
                "INSERT INTO Habitaciones (numero, tipo, descripcion, precio_usd, estado) VALUES (?,?,?,?,?)",
                rooms
            )


# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────

def get_config() -> dict:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM Configuracion WHERE id=1").fetchone()
        return dict(row) if row else {}


def update_config(data: dict):
    with get_connection() as conn:
        placeholders = ", ".join(f"{k}=?" for k in data)
        conn.execute(f"UPDATE Configuracion SET {placeholders} WHERE id=1",
                     list(data.values()))


def get_tasa() -> float:
    return get_config().get("tasa_dolar_bs", 36.0)


def usd_to_bs(monto_usd: float) -> float:
    return round(monto_usd * get_tasa(), 2)


def bs_to_usd(monto_bs: float) -> float:
    tasa = get_tasa()
    return round(monto_bs / tasa, 4) if tasa else 0.0


# ─── USUARIOS ─────────────────────────────────────────────────────────────────

def login(username: str, password: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM Usuarios WHERE username=? AND password=? AND activo=1",
            (username, password)
        ).fetchone()
        return dict(row) if row else None


def get_all_users() -> list[dict]:
    with get_connection() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM Usuarios").fetchall()]


def create_user(data: dict):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO Usuarios (username, password, nombre, rol) VALUES (:username,:password,:nombre,:rol)",
            data
        )


def toggle_user_activo(user_id: int):
    with get_connection() as conn:
        conn.execute("UPDATE Usuarios SET activo = CASE WHEN activo=1 THEN 0 ELSE 1 END WHERE id=?",
                     (user_id,))


# ─── HUÉSPEDES ────────────────────────────────────────────────────────────────

def get_huesped_by_documento(doc: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM Huespedes WHERE documento=?", (doc,)).fetchone()
        return dict(row) if row else None


def get_huesped_by_id(hid: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM Huespedes WHERE id=?", (hid,)).fetchone()
        return dict(row) if row else None


def search_huespedes(query: str) -> list[dict]:
    q = f"%{query}%"
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM Huespedes WHERE documento LIKE ? OR nombres LIKE ? LIMIT 20",
            (q, q)
        ).fetchall()
        return [dict(r) for r in rows]


def create_huesped(data: dict) -> int:
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO Huespedes (documento, nombres, telefono, fecha_nacimiento,
                                   nacionalidad, profesion, vehiculo, saldo_acumulado)
            VALUES (:documento,:nombres,:telefono,:fecha_nacimiento,
                    :nacionalidad,:profesion,:vehiculo, 0)
        """, data)
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def update_huesped(data: dict):
    with get_connection() as conn:
        conn.execute("""
            UPDATE Huespedes SET nombres=:nombres, telefono=:telefono,
                fecha_nacimiento=:fecha_nacimiento, nacionalidad=:nacionalidad,
                profesion=:profesion, vehiculo=:vehiculo
            WHERE id=:id
        """, data)


def update_huesped_saldo(huesped_id: int, nuevo_saldo: float):
    with get_connection() as conn:
        conn.execute("UPDATE Huespedes SET saldo_acumulado=? WHERE id=?",
                     (round(nuevo_saldo, 2), huesped_id))


# ─── HABITACIONES ─────────────────────────────────────────────────────────────

def get_all_habitaciones() -> list[dict]:
    """Retorna habitaciones con info del huésped activo si aplica."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT h.*,
                   r.id              AS registro_id,
                   r.fecha_entrada,
                   r.fecha_salida_prevista,
                   g.nombres         AS huesped_nombre,
                   g.documento       AS huesped_doc,
                   g.saldo_acumulado AS huesped_saldo
            FROM Habitaciones h
            LEFT JOIN Registros r ON h.numero = r.habitacion_id AND r.estado = 'Activo'
            LEFT JOIN Huespedes g ON r.huesped_principal_id = g.id
            ORDER BY h.numero
        """).fetchall()
        return [dict(r) for r in rows]


def get_habitacion(numero: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM Habitaciones WHERE numero=?", (numero,)).fetchone()
        return dict(row) if row else None


def update_habitacion(numero: int, data: dict):
    with get_connection() as conn:
        placeholders = ", ".join(f"{k}=?" for k in data)
        conn.execute(f"UPDATE Habitaciones SET {placeholders} WHERE numero=?",
                     list(data.values()) + [numero])


def set_estado_habitacion(numero: int, estado: str):
    with get_connection() as conn:
        conn.execute("UPDATE Habitaciones SET estado=? WHERE numero=?", (estado, numero))


# ─── REGISTROS (CHECK-IN / CHECK-OUT) ─────────────────────────────────────────

def create_registro(huesped_principal_id: int, habitacion_id: int,
                    fecha_entrada: str, fecha_salida_prevista: str,
                    notas: str = "") -> int:
    with get_connection() as conn:
        conn.execute("UPDATE Habitaciones SET estado='Ocupada' WHERE numero=?", (habitacion_id,))
        conn.execute("""
            INSERT INTO Registros (huesped_principal_id, habitacion_id, fecha_entrada,
                                   fecha_salida_prevista, estado, notas)
            VALUES (?,?,?,?,'Activo',?)
        """, (huesped_principal_id, habitacion_id, fecha_entrada, fecha_salida_prevista, notas))
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def get_registro_activo(habitacion_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("""
            SELECT r.*,
                   g.nombres         AS huesped_nombre,
                   g.documento       AS huesped_doc,
                   g.saldo_acumulado AS huesped_saldo,
                   g.id              AS guest_id
            FROM Registros r
            JOIN Huespedes g ON r.huesped_principal_id = g.id
            WHERE r.habitacion_id=? AND r.estado='Activo'
        """, (habitacion_id,)).fetchone()
        return dict(row) if row else None


def get_registro_by_id(reg_id: int) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("""
            SELECT r.*,
                   g.nombres         AS huesped_nombre,
                   g.documento       AS huesped_doc,
                   g.saldo_acumulado AS huesped_saldo,
                   g.id              AS guest_id,
                   hab.precio_usd,
                   hab.tipo          AS hab_tipo
            FROM Registros r
            JOIN Huespedes   g   ON r.huesped_principal_id = g.id
            JOIN Habitaciones hab ON r.habitacion_id = hab.numero
            WHERE r.id=?
        """, (reg_id,)).fetchone()
        return dict(row) if row else None


def checkout_registro(registro_id: int, habitacion_id: int,
                      huesped_id: int, saldo_nuevo: float):
    with get_connection() as conn:
        ahora = datetime.now().strftime("%Y-%m-%d")
        conn.execute(
            "UPDATE Registros SET estado='Cerrado', fecha_salida_prevista=? WHERE id=?",
            (ahora, registro_id)
        )
        conn.execute("UPDATE Habitaciones SET estado='Aseo' WHERE numero=?", (habitacion_id,))
        conn.execute("UPDATE Huespedes SET saldo_acumulado=? WHERE id=?",
                     (round(saldo_nuevo, 2), huesped_id))


# ─── ACOMPAÑANTES ─────────────────────────────────────────────────────────────

def add_acompanante(registro_id: int, huesped_id: int):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO Acompanantes (registro_id, huesped_id) VALUES (?,?)",
            (registro_id, huesped_id)
        )


def remove_acompanante(registro_id: int, huesped_id: int):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM Acompanantes WHERE registro_id=? AND huesped_id=?",
            (registro_id, huesped_id)
        )


def get_acompanantes(registro_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT h.* FROM Acompanantes a
            JOIN Huespedes h ON a.huesped_id = h.id
            WHERE a.registro_id=?
        """, (registro_id,)).fetchall()
        return [dict(r) for r in rows]


# ─── TRANSACCIONES ────────────────────────────────────────────────────────────

def create_transaccion(data: dict):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO Transacciones
                (registro_id, monto_usd, tasa_cambio, monto_bs, metodo_pago,
                 tipo, fecha_hora, usuario_id, referencia, descripcion)
            VALUES (:registro_id,:monto_usd,:tasa_cambio,:monto_bs,:metodo_pago,
                    :tipo,:fecha_hora,:usuario_id,:referencia,:descripcion)
        """, data)


def get_transacciones_registro(registro_id: int) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM Transacciones WHERE registro_id=? ORDER BY fecha_hora",
            (registro_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_total_pagado_usd(registro_id: int) -> float:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(monto_usd),0) as t FROM Transacciones WHERE registro_id=? AND tipo='Pago'",
            (registro_id,)
        ).fetchone()
        return row["t"]


# ─── CIERRE DE TURNO ──────────────────────────────────────────────────────────

def get_transacciones_turno(usuario_id: int, desde: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM Transacciones WHERE usuario_id=? AND fecha_hora >= ? ORDER BY fecha_hora",
            (usuario_id, desde)
        ).fetchall()
        return [dict(r) for r in rows]


def registrar_cierre_turno(usuario_id: int, fecha_apertura: str,
                            total_usd: float, total_bs: float, resumen: dict):
    fecha_cierre = datetime.now().isoformat()
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO CierresTurno (usuario_id, fecha_apertura, fecha_cierre, total_usd, total_bs, resumen)
            VALUES (?,?,?,?,?,?)
        """, (usuario_id, fecha_apertura, fecha_cierre, total_usd, total_bs,
               json.dumps(resumen, ensure_ascii=False)))
        conn.execute("UPDATE Configuracion SET turno_inicio=? WHERE id=1", (fecha_cierre,))


def get_historial_cierres() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT c.*, u.nombre AS usuario_nombre
            FROM CierresTurno c
            JOIN Usuarios u ON c.usuario_id = u.id
            ORDER BY c.fecha_cierre DESC LIMIT 30
        """).fetchall()
        return [dict(r) for r in rows]


# ─── REPORTES ─────────────────────────────────────────────────────────────────

def get_resumen_dia(fecha: str) -> dict:
    """Resumen de operaciones de un día específico."""
    with get_connection() as conn:
        pagos = conn.execute("""
            SELECT metodo_pago, SUM(monto_usd) as total_usd, SUM(monto_bs) as total_bs,
                   COUNT(*) as cantidad
            FROM Transacciones
            WHERE tipo='Pago' AND DATE(fecha_hora)=?
            GROUP BY metodo_pago
        """, (fecha,)).fetchall()

        checkins = conn.execute(
            "SELECT COUNT(*) as c FROM Registros WHERE DATE(fecha_entrada)=?", (fecha,)
        ).fetchone()["c"]

        checkouts = conn.execute(
            "SELECT COUNT(*) as c FROM Registros WHERE DATE(fecha_salida_prevista)=? AND estado='Cerrado'",
            (fecha,)
        ).fetchone()["c"]

        return {
            "pagos":    [dict(p) for p in pagos],
            "checkins":  checkins,
            "checkouts": checkouts,
        }
