"""
main.py - Punto de entrada del Sistema de Gestión Hotelera (SGH)
=========================================================================
  Tecnología : Python + Flet
  Arquitectura: Basada en Componentes con SQLite
  Estructura  :
      main.py          ← Este archivo (routing + app init)
      database.py      ← DAL: modelos y CRUD
      views/
          login.py     ← Pantalla de inicio de sesión
          dashboard.py ← Grid de 39 habitaciones
          checkin.py   ← Flujo Check-in paso a paso
          payments.py  ← Módulo de pagos multi-método
          config.py    ← Configuración, habitaciones, usuarios
      components/
          room_card.py  ← Tarjeta de habitación con color dinámico
          payment_row.py← Fila de pago individual
=========================================================================
"""
import flet as ft
import database as db
from datetime import datetime

from views.login    import LoginView
from views.dashboard import DashboardView
from views.checkin  import CheckinView
from views.payments import PaymentsView
from views.config   import ConfigView


def main(page: ft.Page):
    # ── Configuración de página ───────────────────────────────────────────────
    page.title        = "SGH — Sistema de Gestión Hotelera"
    page.theme_mode   = ft.ThemeMode.DARK
    page.bgcolor      = "#0f172a"
    page.padding      = 0
    page.window_width  = 1280
    page.window_height = 800
    page.window_min_width  = 900
    page.window_min_height = 600
    page.fonts = {
        "Roboto": "https://fonts.gstatic.com/s/roboto/v32/KFOmCnqEu92Fr1Me5WZLCzYlKw.woff2"
    }
    page.theme = ft.Theme(
        font_family="Roboto",
        color_scheme_seed="#3b82f6",
    )

    # ── Inicializar DB ────────────────────────────────────────────────────────
    db.init_db()

    # ── Navegación helper ─────────────────────────────────────────────────────
    def navigate(route: str, **kwargs):
        for k, v in kwargs.items():
            page.session.set(k, v)
        page.go(route)

    # ── Callback login exitoso ─────────────────────────────────────────────────
    def on_login_success(user: dict):
        page.session.set("current_user", user)

        # Iniciar/recuperar turno
        cfg         = db.get_config()
        turno_inicio = cfg.get("turno_inicio") or datetime.now().isoformat()
        page.session.set("turno_inicio", turno_inicio)
        db.update_config({
            "turno_inicio":   turno_inicio,
            "usuario_activo": user["username"],
        })
        page.go("/dashboard")

    # ── Route change ──────────────────────────────────────────────────────────
    def route_change(e: ft.RouteChangeEvent):
        route = page.route

        # Guard: rutas protegidas
        protected = ["/dashboard", "/checkin", "/payments", "/config"]
        if any(route.startswith(r) for r in protected):
            if not page.session.get("current_user"):
                page.go("/login")
                return

        page.views.clear()

        if route in ("/", "/login"):
            page.views.append(LoginView(page, on_login_success=on_login_success))

        elif route == "/dashboard":
            page.views.append(DashboardView(page, navigate=navigate))

        elif route == "/checkin":
            room_num    = page.session.get("selected_room")
            mode        = page.session.get("checkin_mode", "checkin")
            if not room_num:
                page.go("/dashboard")
                return
            page.views.append(
                CheckinView(page,
                            room_number=room_num,
                            navigate=navigate,
                            checkin_mode=mode)
            )

        elif route == "/payments":
            page.views.append(PaymentsView(page, navigate=navigate))

        elif route == "/config":
            page.views.append(ConfigView(page, navigate=navigate))

        else:
            # Ruta desconocida → dashboard o login
            fallback = "/dashboard" if page.session.get("current_user") else "/login"
            page.go(fallback)
            return

        page.update()

    def view_pop(e: ft.ViewPopEvent):
        page.views.pop()
        if page.views:
            page.go(page.views[-1].route)

    page.on_route_change = route_change
    page.on_view_pop     = view_pop

    # Arrancar en login
    page.go("/login")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ft.app(target=main)
