"""
components/room_card.py
Tarjeta de habitación con color dinámico según estado.
"""
import flet as ft
from datetime import datetime, date

# Paleta de colores por estado
STATE_COLORS = {
    "Libre":         {"bg": "#1a6b3c", "icon": ft.icons.CHECK_CIRCLE,     "icon_color": "#4ade80"},
    "Ocupada":       {"bg": "#7f1d1d", "icon": ft.icons.PERSON,           "icon_color": "#f87171"},
    "Reservada":     {"bg": "#78350f", "icon": ft.icons.EVENT_AVAILABLE,  "icon_color": "#fbbf24"},
    "Aseo":          {"bg": "#374151", "icon": ft.icons.CLEANING_SERVICES,"icon_color": "#9ca3af"},
    "Mantenimiento": {"bg": "#1c1917", "icon": ft.icons.BUILD,            "icon_color": "#f97316"},
}

STATE_LABELS = {
    "Libre":         "Libre",
    "Ocupada":       "Ocupada",
    "Reservada":     "Reservada",
    "Aseo":          "En Aseo",
    "Mantenimiento": "Mantenimiento",
}


def dias_restantes(fecha_salida: str) -> int | None:
    try:
        fs = datetime.strptime(fecha_salida, "%Y-%m-%d").date()
        delta = (fs - date.today()).days
        return delta
    except Exception:
        return None


def RoomCard(hab: dict, on_click) -> ft.Container:
    estado   = hab.get("estado", "Libre")
    numero   = hab.get("numero", "?")
    tipo     = hab.get("tipo", "")
    precio   = hab.get("precio_usd", 0)
    huesped  = hab.get("huesped_nombre", "")
    f_salida = hab.get("fecha_salida_prevista", "")
    saldo    = hab.get("huesped_saldo", 0) or 0

    cfg      = STATE_COLORS.get(estado, STATE_COLORS["Libre"])
    bg_color = cfg["bg"]
    icon     = cfg["icon"]
    ic_color = cfg["icon_color"]

    # Indicador de alerta (deuda o vencida)
    alerts = []
    if estado == "Ocupada":
        if saldo < 0:
            alerts.append(
                ft.Tooltip(
                    message=f"Deuda: ${abs(saldo):.2f}",
                    content=ft.Icon(ft.icons.WARNING_AMBER_ROUNDED,
                                    color="#ef4444", size=14)
                )
            )
        if f_salida:
            dias = dias_restantes(f_salida)
            if dias is not None and dias <= 0:
                alerts.append(
                    ft.Tooltip(
                        message="Salida vencida",
                        content=ft.Icon(ft.icons.ALARM, color="#f97316", size=14)
                    )
                )
            elif dias is not None and dias == 1:
                alerts.append(
                    ft.Tooltip(
                        message="Sale mañana",
                        content=ft.Icon(ft.icons.SCHEDULE, color="#fbbf24", size=14)
                    )
                )

    # Contenido de la card
    header = ft.Row(
        controls=[
            ft.Icon(icon, color=ic_color, size=18),
            ft.Text(f"#{numero}", size=16, weight=ft.FontWeight.BOLD,
                    color="#ffffff"),
            ft.Row(controls=alerts, spacing=2),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    body_controls = [
        ft.Text(tipo, size=11, color="#cbd5e1"),
        ft.Text(f"${precio:.0f}/noche", size=11, color="#94a3b8"),
    ]

    if estado == "Ocupada" and huesped:
        nombre_corto = huesped.split()[0] if huesped else ""
        body_controls.append(
            ft.Text(nombre_corto, size=12, color="#e2e8f0",
                    weight=ft.FontWeight.W_500,
                    overflow=ft.TextOverflow.ELLIPSIS, max_lines=1)
        )
        if f_salida:
            dias = dias_restantes(f_salida)
            color_dias = "#ef4444" if (dias is not None and dias <= 0) else "#94a3b8"
            label = f"Sale: {f_salida}" if dias is None else f"Salida en {dias}d"
            body_controls.append(ft.Text(label, size=10, color=color_dias))

    estado_badge = ft.Container(
        content=ft.Text(STATE_LABELS.get(estado, estado),
                        size=9, color="#ffffff", weight=ft.FontWeight.W_600),
        bgcolor=ft.colors.with_opacity(0.3, "#ffffff"),
        border_radius=4,
        padding=ft.padding.symmetric(horizontal=5, vertical=2),
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                header,
                ft.Column(controls=body_controls, spacing=2),
                ft.Row(controls=[estado_badge],
                       alignment=ft.MainAxisAlignment.END),
            ],
            spacing=6,
            expand=True,
        ),
        bgcolor=bg_color,
        border_radius=10,
        padding=10,
        border=ft.border.all(1, ft.colors.with_opacity(0.2, "#ffffff")),
        ink=True,
        on_click=lambda e: on_click(hab),
        animate=ft.animation.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
        shadow=ft.BoxShadow(
            spread_radius=0, blur_radius=8,
            color=ft.colors.with_opacity(0.4, "#000000"),
            offset=ft.Offset(0, 2)
        ),
    )
