"""
views/dashboard.py - Panel principal con grid de habitaciones
"""
import flet as ft
import database as db
from components.room_card import RoomCard

ESTADOS_CYCLE = {
    "Libre":         ["Libre", "Reservada", "Aseo", "Mantenimiento"],
    "Reservada":     ["Libre", "Reservada", "Aseo", "Mantenimiento"],
    "Aseo":          ["Libre", "Aseo", "Mantenimiento"],
    "Mantenimiento": ["Libre", "Mantenimiento"],
    "Ocupada":       ["Ocupada"],   # Solo via checkout
}


def DashboardView(page: ft.Page, navigate) -> ft.View:
    user = page.session.get("current_user")
    cfg  = db.get_config()

    # ── Estado local ─────────────────────────────────────────────────────────
    tasa_field = ft.TextField(
        value=str(cfg.get("tasa_dolar_bs", 36.0)),
        keyboard_type=ft.KeyboardType.NUMBER,
        width=100,
        dense=True,
        border_color="#334155",
        focused_border_color="#3b82f6",
        text_style=ft.TextStyle(color="#f1f5f9", size=13),
        suffix_text="Bs/$",
        on_submit=lambda e: save_tasa(e),
    )

    tasa_label = ft.Text(
        f"Tasa: {cfg.get('tasa_dolar_bs', 36.0)} Bs/$",
        color="#94a3b8", size=12
    )

    filter_estado = ft.Ref[ft.Dropdown]()
    grid_ref      = ft.Ref[ft.GridView]()
    stats_ref     = ft.Ref[ft.Row]()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def save_tasa(e):
        try:
            nueva = float(tasa_field.value.replace(",", "."))
            db.update_config({"tasa_dolar_bs": nueva})
            tasa_label.value = f"Tasa: {nueva} Bs/$"
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ Tasa actualizada a {nueva} Bs/$", color="#4ade80"),
                bgcolor="#1e293b"
            )
            page.snack_bar.open = True
            page.update()
        except ValueError:
            page.snack_bar = ft.SnackBar(
                ft.Text("Valor inválido", color="#ef4444"), bgcolor="#1e293b"
            )
            page.snack_bar.open = True
            page.update()

    def get_stats(habitaciones):
        stats = {"Libre": 0, "Ocupada": 0, "Reservada": 0,
                 "Aseo": 0, "Mantenimiento": 0}
        for h in habitaciones:
            stats[h["estado"]] = stats.get(h["estado"], 0) + 1
        return stats

    def build_stats_bar(habitaciones):
        stats  = get_stats(habitaciones)
        total  = len(habitaciones)
        colors = {
            "Libre":         "#1a6b3c",
            "Ocupada":       "#7f1d1d",
            "Reservada":     "#78350f",
            "Aseo":          "#374151",
            "Mantenimiento": "#1c1917",
        }
        chips = []
        for estado, count in stats.items():
            chips.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Container(width=10, height=10,
                                         bgcolor=colors[estado],
                                         border_radius=5),
                            ft.Text(f"{estado}: {count}", size=11, color="#cbd5e1"),
                        ],
                        spacing=4,
                    ),
                    bgcolor="#1e293b",
                    border_radius=6,
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                )
            )
        chips.append(
            ft.Text(f"Total: {total}", size=12,
                    color="#94a3b8", weight=ft.FontWeight.W_600)
        )
        return chips

    def reload_grid(e=None):
        habitaciones = db.get_all_habitaciones()
        filtro = filter_estado.current.value if filter_estado.current else "Todas"

        if filtro and filtro != "Todas":
            habitaciones = [h for h in habitaciones if h["estado"] == filtro]

        if grid_ref.current:
            grid_ref.current.controls = [
                RoomCard(h, on_room_click) for h in habitaciones
            ]

        # Siempre mostrar stats del total
        all_habs = db.get_all_habitaciones()
        if stats_ref.current:
            stats_ref.current.controls = build_stats_bar(all_habs)

        page.update()

    def on_room_click(hab):
        estado = hab["estado"]
        numero = hab["numero"]

        if estado == "Ocupada":
            # Ir a vista de pagos/checkout
            navigate("/checkin", selected_room=numero, checkin_mode="checkout")
        elif estado in ("Aseo", "Mantenimiento", "Reservada"):
            open_estado_dialog(hab)
        else:  # Libre
            navigate("/checkin", selected_room=numero, checkin_mode="checkin")

    def open_estado_dialog(hab):
        numero = hab["numero"]
        estado_actual = hab["estado"]
        opciones = ESTADOS_CYCLE.get(estado_actual, ["Libre"])

        dd = ft.Dropdown(
            label="Cambiar estado",
            value=estado_actual,
            options=[ft.dropdown.Option(o) for o in opciones],
            border_color="#334155",
            color="#f1f5f9",
        )

        def confirm(e):
            nuevo_estado = dd.value
            if nuevo_estado != estado_actual:
                db.set_estado_habitacion(numero, nuevo_estado)
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"Hab. {numero} → {nuevo_estado}", color="#4ade80"),
                    bgcolor="#1e293b"
                )
                page.snack_bar.open = True
            dialog.open = False
            reload_grid()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Habitación #{numero} — {estado_actual}",
                          color="#f1f5f9"),
            bgcolor="#1e293b",
            content=ft.Column(
                controls=[
                    ft.Text(f"Tipo: {hab['tipo']} | ${hab['precio_usd']:.0f}/noche",
                            color="#94a3b8", size=13),
                    dd,
                ],
                tight=True, spacing=12,
            ),
            actions=[
                ft.TextButton("Cancelar",
                              on_click=lambda e: (setattr(dialog, "open", False), page.update()),
                              style=ft.ButtonStyle(color={"": "#94a3b8"})),
                ft.ElevatedButton("Guardar", on_click=confirm,
                                  style=ft.ButtonStyle(
                                      bgcolor={"": "#3b82f6"},
                                      color={"": "#ffffff"},
                                  )),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.dialog = dialog
        dialog.open  = True
        page.update()

    def open_turno_dialog(e):
        user_id     = user["id"]
        turno_inicio = page.session.get("turno_inicio") or db.get_config().get("turno_inicio", "")
        transacciones = db.get_transacciones_turno(user_id, turno_inicio)

        total_usd   = sum(t["monto_usd"] for t in transacciones if t["tipo"] == "Pago")
        total_bs    = sum(t["monto_bs"]  for t in transacciones if t["tipo"] == "Pago")
        metodos     = {}
        for t in transacciones:
            if t["tipo"] == "Pago":
                m = t["metodo_pago"]
                metodos[m] = metodos.get(m, 0) + t["monto_usd"]

        rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(m,      color="#cbd5e1", size=12)),
                ft.DataCell(ft.Text(f"${v:.2f}", color="#4ade80", size=12)),
            ])
            for m, v in metodos.items()
        ]

        def do_cierre(e):
            db.registrar_cierre_turno(user_id, turno_inicio, total_usd, total_bs,
                                       {"metodos": metodos, "total": total_usd})
            from datetime import datetime
            nueva_apertura = datetime.now().isoformat()
            page.session.set("turno_inicio", nueva_apertura)
            dialog.open = False
            page.snack_bar = ft.SnackBar(
                ft.Text(f"✓ Turno cerrado. Total: ${total_usd:.2f}", color="#4ade80"),
                bgcolor="#1e293b"
            )
            page.snack_bar.open = True
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Cierre de Turno", color="#f1f5f9"),
            bgcolor="#1e293b",
            content=ft.Column(
                controls=[
                    ft.Text(f"Usuario: {user['nombre']}", color="#94a3b8", size=13),
                    ft.Text(f"Desde: {turno_inicio[:16]}", color="#94a3b8", size=12),
                    ft.Divider(color="#334155"),
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("Método", color="#64748b", size=12)),
                            ft.DataColumn(ft.Text("Total USD", color="#64748b", size=12)),
                        ],
                        rows=rows,
                    ) if rows else ft.Text("Sin transacciones en este turno.", color="#64748b"),
                    ft.Divider(color="#334155"),
                    ft.Text(f"TOTAL: ${total_usd:.2f}  |  Bs. {total_bs:,.2f}",
                            color="#4ade80", size=15, weight=ft.FontWeight.BOLD),
                ],
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
                width=380,
            ),
            actions=[
                ft.TextButton("Cancelar",
                              on_click=lambda e: (setattr(dialog, "open", False), page.update()),
                              style=ft.ButtonStyle(color={"": "#94a3b8"})),
                ft.ElevatedButton("Cerrar Turno", on_click=do_cierre,
                                  style=ft.ButtonStyle(
                                      bgcolor={"": "#dc2626"},
                                      color={"": "#ffffff"},
                                  )),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.dialog = dialog
        dialog.open  = True
        page.update()

    def do_logout(e):
        page.session.set("current_user", None)
        page.go("/login")

    # ── Construcción inicial ───────────────────────────────────────────────────
    habitaciones = db.get_all_habitaciones()
    all_stats    = build_stats_bar(habitaciones)
    room_cards   = [RoomCard(h, on_room_click) for h in habitaciones]

    grid = ft.GridView(
        ref=grid_ref,
        controls=room_cards,
        runs_count=6,
        max_extent=180,
        child_aspect_ratio=1.05,
        spacing=8,
        run_spacing=8,
        expand=True,
    )

    top_bar = ft.Container(
        content=ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(ft.icons.HOTEL, color="#3b82f6", size=24),
                        ft.Text(cfg.get("nombre_hotel", "Mi Hotel"),
                                size=18, weight=ft.FontWeight.BOLD,
                                color="#f1f5f9"),
                    ],
                    spacing=8,
                ),
                ft.Row(
                    controls=[
                        # Filtro
                        ft.Dropdown(
                            ref=filter_estado,
                            label="Filtrar",
                            value="Todas",
                            options=[ft.dropdown.Option(o) for o in
                                     ["Todas", "Libre", "Ocupada", "Reservada",
                                      "Aseo", "Mantenimiento"]],
                            width=130,
                            dense=True,
                            border_color="#334155",
                            color="#f1f5f9",
                            label_style=ft.TextStyle(color="#64748b", size=11),
                            on_change=reload_grid,
                        ),
                        # Tasa
                        ft.Row(
                            controls=[
                                tasa_field,
                                ft.IconButton(
                                    ft.icons.SAVE_OUTLINED,
                                    icon_color="#3b82f6",
                                    tooltip="Guardar tasa",
                                    on_click=save_tasa,
                                ),
                            ],
                            spacing=2,
                        ),
                        ft.IconButton(
                            ft.icons.REFRESH,
                            icon_color="#94a3b8",
                            tooltip="Actualizar",
                            on_click=reload_grid,
                        ),
                        ft.IconButton(
                            ft.icons.SETTINGS_OUTLINED,
                            icon_color="#94a3b8",
                            tooltip="Configuración",
                            on_click=lambda e: navigate("/config"),
                        ),
                        ft.IconButton(
                            ft.icons.RECEIPT_LONG_OUTLINED,
                            icon_color="#fbbf24",
                            tooltip="Cierre de turno",
                            on_click=open_turno_dialog,
                        ),
                        ft.IconButton(
                            ft.icons.LOGOUT,
                            icon_color="#ef4444",
                            tooltip="Cerrar sesión",
                            on_click=do_logout,
                        ),
                    ],
                    spacing=4,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        bgcolor="#1e293b",
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        border=ft.border.only(bottom=ft.BorderSide(1, "#334155")),
    )

    stats_bar = ft.Container(
        content=ft.Row(
            ref=stats_ref,
            controls=all_stats,
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=ft.padding.symmetric(horizontal=16, vertical=6),
        bgcolor="#0f172a",
    )

    usuario_badge = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(ft.icons.PERSON_OUTLINE, size=14, color="#64748b"),
                ft.Text(f"{user['nombre']} ({user['rol']})",
                        size=12, color="#64748b"),
            ],
            spacing=4,
        ),
        padding=ft.padding.symmetric(horizontal=16, vertical=4),
        bgcolor="#0f172a",
    )

    legend = ft.Container(
        content=ft.Row(
            controls=[
                ft.Text("Leyenda:", size=11, color="#475569"),
                *[
                    ft.Row(controls=[
                        ft.Container(width=12, height=12, bgcolor=c, border_radius=3),
                        ft.Text(l, size=11, color="#64748b"),
                    ], spacing=3)
                    for l, c in [("Libre", "#1a6b3c"), ("Ocupada", "#7f1d1d"),
                                 ("Reservada", "#78350f"), ("Aseo", "#374151"),
                                 ("Mantenimiento", "#1c1917")]
                ],
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=ft.padding.symmetric(horizontal=16, vertical=4),
        bgcolor="#0f172a",
    )

    return ft.View(
        route="/dashboard",
        bgcolor="#0f172a",
        padding=0,
        controls=[
            ft.Column(
                controls=[
                    top_bar,
                    stats_bar,
                    usuario_badge,
                    legend,
                    ft.Container(
                        content=grid,
                        expand=True,
                        padding=12,
                    ),
                ],
                expand=True,
                spacing=0,
            )
        ],
    )
