"""
views/login.py - Pantalla de inicio de sesión
"""
import flet as ft
import database as db


def LoginView(page: ft.Page, on_login_success) -> ft.View:
    status_text = ft.Text("", color="#ef4444", size=13)
    username_field = ft.TextField(
        label="Usuario",
        autofocus=True,
        border_color="#334155",
        focused_border_color="#3b82f6",
        text_style=ft.TextStyle(color="#f1f5f9"),
        label_style=ft.TextStyle(color="#94a3b8"),
        prefix_icon=ft.icons.PERSON_OUTLINE,
        width=340,
    )
    password_field = ft.TextField(
        label="Contraseña",
        password=True,
        can_reveal_password=True,
        border_color="#334155",
        focused_border_color="#3b82f6",
        text_style=ft.TextStyle(color="#f1f5f9"),
        label_style=ft.TextStyle(color="#94a3b8"),
        prefix_icon=ft.icons.LOCK_OUTLINE,
        width=340,
    )

    def do_login(e):
        status_text.value = ""
        username = username_field.value.strip()
        password = password_field.value.strip()
        if not username or not password:
            status_text.value = "Ingrese usuario y contraseña."
            page.update()
            return
        user = db.login(username, password)
        if user:
            on_login_success(user)
        else:
            status_text.value = "Credenciales incorrectas."
            password_field.value = ""
            page.update()

    password_field.on_submit = do_login

    cfg = db.get_config()
    hotel_name = cfg.get("nombre_hotel", "Mi Hotel")

    return ft.View(
        route="/login",
        bgcolor="#0f172a",
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Icon(ft.icons.HOTEL, size=56, color="#3b82f6"),
                                ft.Text(hotel_name,
                                        size=26, weight=ft.FontWeight.BOLD,
                                        color="#f1f5f9",
                                        text_align=ft.TextAlign.CENTER),
                                ft.Text("Sistema de Gestión Hotelera",
                                        size=13, color="#64748b",
                                        text_align=ft.TextAlign.CENTER),
                                ft.Divider(color="#1e293b", height=20),
                                username_field,
                                password_field,
                                status_text,
                                ft.ElevatedButton(
                                    "Iniciar Sesión",
                                    on_click=do_login,
                                    width=340,
                                    height=46,
                                    style=ft.ButtonStyle(
                                        bgcolor={"": "#3b82f6", ft.MaterialState.HOVERED: "#2563eb"},
                                        color={"": "#ffffff"},
                                        shape=ft.RoundedRectangleBorder(radius=8),
                                    ),
                                    icon=ft.icons.LOGIN,
                                ),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=14,
                        ),
                        bgcolor="#1e293b",
                        border_radius=16,
                        padding=ft.padding.symmetric(horizontal=40, vertical=36),
                        shadow=ft.BoxShadow(
                            blur_radius=40, color=ft.colors.with_opacity(0.5, "#000000")
                        ),
                    )
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        ],
    )
