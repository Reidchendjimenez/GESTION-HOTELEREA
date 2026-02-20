"""
views/config.py - Configuración del Hotel, Habitaciones y Usuarios
"""
import flet as ft
import database as db


def ConfigView(page: ft.Page, navigate) -> ft.View:
    user = page.session.get("current_user")
    cfg  = db.get_config()

    tab_idx = ft.Ref[ft.Tabs]()

    def snack(msg, color="#4ade80"):
        page.snack_bar = ft.SnackBar(ft.Text(msg, color=color), bgcolor="#1e293b")
        page.snack_bar.open = True
        page.update()

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 1: CONFIGURACIÓN GENERAL
    # ═══════════════════════════════════════════════════════════════════════════
    f_hotel = ft.TextField(
        label="Nombre del Hotel",
        value=cfg.get("nombre_hotel", ""),
        border_color="#334155", focused_border_color="#3b82f6",
        text_style=ft.TextStyle(color="#f1f5f9"),
        label_style=ft.TextStyle(color="#94a3b8"),
    )
    f_tasa = ft.TextField(
        label="Tasa Dólar (Bs/$)",
        value=str(cfg.get("tasa_dolar_bs", 36.0)),
        keyboard_type=ft.KeyboardType.NUMBER,
        border_color="#334155", focused_border_color="#3b82f6",
        text_style=ft.TextStyle(color="#f1f5f9"),
        label_style=ft.TextStyle(color="#94a3b8"),
    )

    def save_general(e):
        try:
            tasa = float(f_tasa.value.replace(",", "."))
        except ValueError:
            snack("Tasa inválida.", "#ef4444")
            return
        db.update_config({
            "nombre_hotel":  f_hotel.value.strip(),
            "tasa_dolar_bs": tasa,
        })
        snack("✓ Configuración guardada.")

    tab_general = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Parámetros Generales", size=15, color="#f1f5f9",
                        weight=ft.FontWeight.W_600),
                f_hotel,
                f_tasa,
                ft.Text(
                    "La tasa se aplica globalmente a todas las conversiones Bs/USD.",
                    color="#64748b", size=12,
                ),
                ft.ElevatedButton(
                    "Guardar",
                    icon=ft.icons.SAVE,
                    on_click=save_general,
                    style=ft.ButtonStyle(bgcolor={"": "#3b82f6"}, color={"": "#ffffff"}),
                ),
                ft.Divider(color="#334155", height=24),
                ft.Text("Historial de Cierres de Turno", size=14, color="#f1f5f9",
                        weight=ft.FontWeight.W_600),
                _build_cierres_table(),
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=16,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 2: HABITACIONES
    # ═══════════════════════════════════════════════════════════════════════════
    rooms_col = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)

    def load_rooms():
        habs = db.get_all_habitaciones()
        rooms_col.controls = []
        for h in habs:
            rooms_col.controls.append(_room_edit_row(h, reload_rooms))

    def reload_rooms():
        load_rooms()
        page.update()

    load_rooms()

    tab_rooms = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Gestión de Habitaciones",
                        size=15, color="#f1f5f9", weight=ft.FontWeight.W_600),
                ft.Text("Haz clic en el ícono de editar para modificar precio y tipo.",
                        size=12, color="#64748b"),
                rooms_col,
            ],
            spacing=10,
            expand=True,
        ),
        padding=16,
        expand=True,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 3: USUARIOS
    # ═══════════════════════════════════════════════════════════════════════════
    users_col = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)

    def load_users():
        users = db.get_all_users()
        users_col.controls = []
        for u in users:
            users_col.controls.append(_user_row(u, reload_users))

    def reload_users():
        load_users()
        page.update()

    def open_new_user(e):
        un = ft.TextField(label="Usuario", border_color="#334155",
                          focused_border_color="#3b82f6",
                          text_style=ft.TextStyle(color="#f1f5f9"),
                          label_style=ft.TextStyle(color="#94a3b8"))
        pw = ft.TextField(label="Contraseña", password=True, can_reveal_password=True,
                          border_color="#334155", focused_border_color="#3b82f6",
                          text_style=ft.TextStyle(color="#f1f5f9"),
                          label_style=ft.TextStyle(color="#94a3b8"))
        nm = ft.TextField(label="Nombre completo", border_color="#334155",
                          focused_border_color="#3b82f6",
                          text_style=ft.TextStyle(color="#f1f5f9"),
                          label_style=ft.TextStyle(color="#94a3b8"))
        rol = ft.Dropdown(
            label="Rol",
            value="recepcionista",
            options=[ft.dropdown.Option("admin"), ft.dropdown.Option("recepcionista")],
            border_color="#334155", color="#f1f5f9",
            label_style=ft.TextStyle(color="#94a3b8"),
        )
        err = ft.Text("", color="#ef4444", size=12)

        def confirm(ev):
            if not un.value.strip() or not pw.value.strip() or not nm.value.strip():
                err.value = "Todos los campos son obligatorios."
                page.update()
                return
            try:
                db.create_user({"username": un.value.strip(),
                                "password": pw.value.strip(),
                                "nombre":   nm.value.strip(),
                                "rol":      rol.value})
                dialog.open = False
                reload_users()
                snack("✓ Usuario creado.")
            except Exception as ex:
                err.value = f"Error: {ex}"
                page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Nuevo Usuario", color="#f1f5f9"),
            bgcolor="#1e293b",
            content=ft.Column(controls=[un, pw, nm, rol, err], spacing=8, tight=True),
            actions=[
                ft.TextButton("Cancelar",
                              on_click=lambda ev: (setattr(dialog, "open", False), page.update()),
                              style=ft.ButtonStyle(color={"": "#94a3b8"})),
                ft.ElevatedButton("Crear", on_click=confirm,
                                  style=ft.ButtonStyle(bgcolor={"": "#3b82f6"},
                                                       color={"": "#ffffff"})),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.dialog = dialog
        dialog.open  = True
        page.update()

    load_users()

    tab_users = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Gestión de Usuarios", size=15, color="#f1f5f9",
                                weight=ft.FontWeight.W_600),
                        ft.ElevatedButton(
                            "+ Nuevo Usuario",
                            icon=ft.icons.PERSON_ADD,
                            on_click=open_new_user,
                            style=ft.ButtonStyle(bgcolor={"": "#3b82f6"},
                                                 color={"": "#ffffff"}),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                users_col,
            ],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=16,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # LAYOUT
    # ═══════════════════════════════════════════════════════════════════════════
    header = ft.Container(
        content=ft.Row(
            controls=[
                ft.IconButton(ft.icons.ARROW_BACK, icon_color="#94a3b8",
                              on_click=lambda e: navigate("/dashboard")),
                ft.Text("Configuración del Sistema", size=18, color="#f1f5f9",
                        weight=ft.FontWeight.BOLD),
            ],
            spacing=8,
        ),
        bgcolor="#1e293b",
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        border=ft.border.only(bottom=ft.BorderSide(1, "#334155")),
    )

    tabs = ft.Tabs(
        ref=tab_idx,
        selected_index=0,
        animation_duration=200,
        tabs=[
            ft.Tab(text="General",    icon=ft.icons.SETTINGS,
                   content=tab_general),
            ft.Tab(text="Habitaciones", icon=ft.icons.HOTEL,
                   content=tab_rooms),
            ft.Tab(text="Usuarios",   icon=ft.icons.PEOPLE,
                   content=tab_users),
        ],
        expand=True,
        indicator_color="#3b82f6",
        label_color="#f1f5f9",
        unselected_label_color="#64748b",
    )

    return ft.View(
        route="/config",
        bgcolor="#0f172a",
        padding=0,
        controls=[
            ft.Column(
                controls=[header, tabs],
                expand=True,
                spacing=0,
            )
        ],
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _build_cierres_table():
    cierres = db.get_historial_cierres()
    if not cierres:
        return ft.Text("Sin cierres registrados.", color="#64748b", size=12)

    rows = [
        ft.DataRow(cells=[
            ft.DataCell(ft.Text(c["usuario_nombre"], color="#cbd5e1", size=12)),
            ft.DataCell(ft.Text(c["fecha_cierre"][:16], color="#94a3b8", size=11)),
            ft.DataCell(ft.Text(f"${c['total_usd']:.2f}", color="#4ade80", size=12,
                                weight=ft.FontWeight.W_600)),
            ft.DataCell(ft.Text(f"Bs.{c['total_bs']:,.0f}", color="#22d3ee", size=12)),
        ])
        for c in cierres
    ]

    return ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Usuario", color="#64748b", size=11)),
            ft.DataColumn(ft.Text("Fecha",   color="#64748b", size=11)),
            ft.DataColumn(ft.Text("Total $", color="#64748b", size=11)),
            ft.DataColumn(ft.Text("Total Bs",color="#64748b", size=11)),
        ],
        rows=rows,
        border=ft.border.all(1, "#334155"),
        border_radius=8,
        heading_row_color=ft.colors.with_opacity(0.05, "#ffffff"),
    )


def _room_edit_row(hab: dict, on_saved):
    is_editing = ft.Ref[ft.Container]()
    view_row   = ft.Ref[ft.Row]()

    tipo_options = ["Estándar", "Doble", "Matrimonial", "Suite", "Presidencial"]

    f_tipo = ft.Dropdown(
        value=hab["tipo"],
        options=[ft.dropdown.Option(t) for t in tipo_options],
        width=130, dense=True, border_color="#334155", color="#f1f5f9",
    )
    f_precio = ft.TextField(
        value=str(hab["precio_usd"]),
        keyboard_type=ft.KeyboardType.NUMBER,
        width=90, dense=True, border_color="#334155",
        text_style=ft.TextStyle(color="#f1f5f9"),
        suffix_text="$",
    )
    f_desc = ft.TextField(
        value=hab.get("descripcion", ""),
        width=180, dense=True, border_color="#334155",
        text_style=ft.TextStyle(color="#f1f5f9"),
    )

    estado_color = {
        "Libre":         "#1a6b3c", "Ocupada": "#7f1d1d",
        "Reservada":     "#78350f", "Aseo":    "#374151",
        "Mantenimiento": "#1c1917",
    }.get(hab["estado"], "#334155")

    def save(e):
        try:
            precio = float(f_precio.value.replace(",", "."))
        except ValueError:
            return
        db.update_habitacion(hab["numero"], {
            "tipo":        f_tipo.value,
            "precio_usd":  precio,
            "descripcion": f_desc.value.strip(),
        })
        if is_editing.current:
            is_editing.current.visible = False
        if view_row.current:
            view_row.current.visible = True
        on_saved()

    def toggle_edit(e):
        if is_editing.current:
            is_editing.current.visible = not is_editing.current.visible
        if view_row.current:
            view_row.current.visible = not is_editing.current.visible
        e.page.update()

    view = ft.Row(
        ref=view_row,
        controls=[
            ft.Container(
                content=ft.Text(f"#{hab['numero']}", color="#f1f5f9",
                                size=13, weight=ft.FontWeight.W_600),
                width=36,
            ),
            ft.Container(
                content=ft.Text(hab["estado"], color="#ffffff", size=10),
                bgcolor=estado_color, border_radius=4,
                padding=ft.padding.symmetric(horizontal=5, vertical=2),
                width=80,
            ),
            ft.Text(hab["tipo"], color="#cbd5e1", size=12, width=100),
            ft.Text(f"${hab['precio_usd']:.2f}/noche", color="#4ade80", size=12, width=100),
            ft.Text(hab.get("descripcion", ""), color="#64748b", size=11, expand=True),
            ft.IconButton(ft.icons.EDIT_OUTLINED, icon_size=16,
                          icon_color="#3b82f6", on_click=toggle_edit),
        ],
        spacing=8,
        visible=True,
    )

    edit = ft.Container(
        ref=is_editing,
        content=ft.Row(
            controls=[
                ft.Text(f"#{hab['numero']}", color="#f1f5f9",
                        size=13, weight=ft.FontWeight.W_600, width=36),
                f_tipo, f_precio, f_desc,
                ft.IconButton(ft.icons.CHECK, icon_size=16,
                              icon_color="#4ade80", on_click=save),
                ft.IconButton(ft.icons.CLOSE, icon_size=16,
                              icon_color="#ef4444", on_click=toggle_edit),
            ],
            spacing=6,
        ),
        visible=False,
    )

    return ft.Container(
        content=ft.Column(controls=[view, edit], spacing=0),
        bgcolor="#1e293b",
        border_radius=6,
        padding=ft.padding.symmetric(horizontal=10, vertical=6),
    )


def _user_row(u: dict, on_change):
    activo   = bool(u["activo"])
    rol_icon = ft.icons.ADMIN_PANEL_SETTINGS if u["rol"] == "admin" else ft.icons.PERSON_OUTLINE

    def toggle(e):
        db.toggle_user_activo(u["id"])
        on_change()

    return ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon(rol_icon, size=18, color="#3b82f6"),
                ft.Column(
                    controls=[
                        ft.Text(u["nombre"], color="#f1f5f9", size=13,
                                weight=ft.FontWeight.W_500),
                        ft.Text(f"@{u['username']} — {u['rol']}",
                                color="#64748b", size=11),
                    ],
                    spacing=2, expand=True,
                ),
                ft.Container(
                    content=ft.Text("Activo" if activo else "Inactivo",
                                    size=11, color="#ffffff"),
                    bgcolor="#16a34a" if activo else "#ef4444",
                    border_radius=4,
                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                ),
                ft.IconButton(
                    ft.icons.TOGGLE_ON if activo else ft.icons.TOGGLE_OFF,
                    icon_color="#4ade80" if activo else "#6b7280",
                    tooltip="Activar/Desactivar",
                    on_click=toggle,
                ),
            ],
            spacing=10,
        ),
        bgcolor="#1e293b",
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=12, vertical=8),
    )
