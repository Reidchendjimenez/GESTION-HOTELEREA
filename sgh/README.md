# 🏨 SGH — Sistema de Gestión Hotelera

Sistema completo de gestión hotelera desarrollado en **Python + Flet** con base de datos **SQLite**.

---

## 📁 Estructura del Proyecto

```
sgh/
├── main.py              ← Punto de entrada, routing y navegación
├── database.py          ← Capa de acceso a datos (DAL) — todos los modelos y CRUD
├── requirements.txt
├── views/
│   ├── login.py         ← Pantalla de inicio de sesión
│   ├── dashboard.py     ← Dashboard principal con Grid de 39 habitaciones
│   ├── checkin.py       ← Flujo Check-in / Check-out (4 pasos)
│   ├── payments.py      ← Módulo de pagos multi-método
│   └── config.py        ← Configuración: hotel, habitaciones, usuarios
└── components/
    ├── room_card.py     ← Tarjeta de habitación con color dinámico
    └── payment_row.py   ← Fila de pago individual (multi-método)
```

---

## 🚀 Instalación y Ejecución

### Requisitos
- Python 3.10+
- Flet ≥ 0.21.0

### Pasos
```bash
# 1. Clonar / descomprimir el proyecto
cd sgh

# 2. Instalar dependencias
pip install flet

# 3. Ejecutar
python main.py
```

> La base de datos `hotel.db` se crea automáticamente en el primer arranque con:
> - **39 habitaciones** preconfiguradas (12 Estándar · 16 Doble · 8 Matrimonial · 3 Suite)
> - Usuario **admin** / contraseña **admin123**
> - Usuario **recepcion1** / contraseña **hotel2024**
> - Tasa de cambio inicial: **36 Bs/$**

---

## 🗂 Modelo de Base de Datos

| Tabla            | Descripción                                              |
|-----------------|----------------------------------------------------------|
| `Configuracion`  | Parámetros globales: nombre hotel, tasa Bs/$, turno activo |
| `Usuarios`       | Login, roles (admin / recepcionista), activación         |
| `Huespedes`      | Documento (PK único), datos personales, **saldo_acumulado** |
| `Habitaciones`   | Número, tipo, precio_USD, estado                         |
| `Registros`      | Check-in activos y cerrados                              |
| `Acompanantes`   | Huéspedes adicionales por registro                       |
| `Transacciones`  | Pagos, cargos y ajustes con monto en USD y Bs            |
| `CierresTurno`   | Historial de cierres de caja por usuario                 |

---

## 🖥 Módulos / Vistas

### Dashboard — Grid de Habitaciones
- **Grid de 39 habitaciones** con colores por estado:
  - 🟢 Verde → Libre
  - 🔴 Rojo → Ocupada
  - 🟡 Amarillo → Reservada
  - ⚫ Gris → Aseo
  - 🟠 Naranja → Mantenimiento
- Indicadores de alerta: ⚠ deuda pendiente, 🔔 salida vencida
- Filtro por estado, contador de estadísticas en tiempo real
- **Tasa de cambio actualizable** desde el top-bar (se propaga globalmente)
- Botón de **Cierre de Turno** con resumen por método de pago

### Check-in (4 pasos)
1. **Buscar huésped** por cédula/pasaporte → carga datos si existe
2. **Formulario de registro** (si es huésped nuevo o actualización)
3. **Configurar estancia** — fechas, acompañantes, notas
4. **Pre-factura** — cálculo automático:
   - `Días × Precio` + Deuda anterior − Saldo a favor

### Módulo de Pagos
- Lista dinámica de líneas de pago (multi-método)
- Métodos: Efectivo USD, Efectivo BS, Pago Móvil, Transferencia, Zelle, Otro
- **Referencia obligatoria** para Pago Móvil, Transferencia y Zelle
- Conversión automática USD ↔ Bs según tasa activa
- **Pago Parcial**: registra sin hacer check-out
- **Finalizar Check-out**: activa solo si suma ≥ total
  - Sobrante → se guarda automáticamente en `Huesped.saldo_acumulado`
- Recibo de cierre con detalle completo

### Configuración
- **General**: nombre del hotel, tasa Bs/$, historial de cierres
- **Habitaciones**: edición inline de tipo, precio y descripción
- **Usuarios**: crear, activar/desactivar, asignar rol

---

## 💱 Lógica Financiera

```
Total a pagar = (Días × Precio) + Deuda Anterior − Saldo a Favor
                                  ↑                ↑
                          saldo_acumulado < 0    saldo_acumulado > 0

Si cobrado > total:
    sobrante → saldo_acumulado (positivo = saldo a favor)
```

---

## 🔐 Roles y Seguridad

| Acción                   | admin | recepcionista |
|--------------------------|-------|---------------|
| Ver dashboard            | ✅    | ✅            |
| Check-in / Check-out     | ✅    | ✅            |
| Cambiar tasa de cambio   | ✅    | ✅            |
| Configuración general    | ✅    | ✅            |
| Gestionar usuarios       | ✅    | ❌ (ver solo) |

---

## 🛠 Roadmap de Extensiones Sugeridas

- [ ] Reportes PDF (ingresos diarios, ocupación)
- [ ] Backup automático de la base de datos
- [ ] Soporte PostgreSQL para entornos en red (cambiar `DB_NAME` en `database.py`)
- [ ] QR para comprobante de pago
- [ ] Notificaciones de salidas próximas (cron / threading)
- [ ] Modo oscuro / claro configurable

---

## 📞 Credenciales por Defecto

| Usuario      | Contraseña   | Rol           |
|-------------|-------------|---------------|
| `admin`     | `admin123`   | Administrador |
| `recepcion1`| `hotel2024`  | Recepcionista |

> ⚠ **Cambia las contraseñas antes de poner en producción.**
