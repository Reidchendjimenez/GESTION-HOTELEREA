"""
views/payments.py - Módulo de Pagos Multi-Método y Check-out
"""
import flet as ft
from datetime import datetime
import database as db
from components.payment_row import PaymentRow, REQUIRE_REF, METODOS


def PaymentsView(page: ft.Page, navigate) -> ft.View:
    user       = page.session.get("current_user")
    room_num   = page.session.get("selected_room")
    reg_id     = page.session.get("active_registro_id")
    cfg        = db.get_config()
    tasa       = cfg.get("tasa_dolar_bs", 36.0)

    reg        = db.get_registro_by_id(reg_id) if reg_id else None
    if not reg:
        navigate("/dashboard")
        return ft.View(route="/payments", controls=[ft.Text("Error")])

    huesped    = db.get_huesped_by_id(reg["guest_id"])
    precio_hab = reg.get("precio_usd", reg.get("precio_usd", 30.0))
    fecha_e    = reg["fecha_entrada"]
    fecha_s    = reg["fecha_salida_prevista"]

    try:
        dias = max((datetime.strptime(fecha_s, "%Y-%m-%d") -
                    datetime.strptime(fecha_e, "%Y-%m-%d")).days, 1)
    except Exception:
        dias = 1

    subtotal   = dias * precio_hab
    ya_pagado  = db.get_total_pagado_usd(reg_id)
    saldo_hues = huesped["saldo_acumulado"]
    deuda_ant  = abs(saldo_hues) if saldo_hues < 0 else 0.0
    favor_ant  = saldo_hues if saldo_hues > 0 else 0.0
    total_debe = max(subtotal + deuda_ant - favor_ant - ya_pagado, 0.0)

    # ── Estado ────────────────────────────────────────────────────────────────
    pagos_state  = {}   # index -> {"metodo", "monto_usd", "monto_bs", "referencia"}
    next_idx     = [0]

    pagos_col    = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO)
    total_text   = ft.Text(f"${total_debe:.2f}", size=30, color="#4ade80",
                           weight=ft.FontWeight.BOLD)
    total_bs_txt = ft.Text(f"Bs. {db.usd_to_bs(total_debe):,.2f}",
                           size=15, color="#22d3ee")
    suma_pagos_t = ft.Text("Suma pagos: $0.00", size=14, color="#94a3b8")
    restante_t   = ft.Text(f"Restante: ${total_debe:.2f}", size=14, color="#fbbf24")
    sobrante_t   = ft.Text("", size=13, color="#4ade80")
    btn_finalizar = ft.Ref[ft.ElevatedButton]()

    historial_col = ft.Column(spacing=4)

    def load_historial():
        txns = db.get_transacciones_registro(reg_id)
        historial_col.controls = []
        for t in txns:
            tipo_color = "#4ade80" if t["tipo"] == "Pago" else "#f87171"
            historial_col.controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Text(t["tipo"], size=11,
                                    color=tipo_color, width=55),
                            ft.Text(t["metodo_pago"], size=11,
                                    color="#cbd5e1", expand=True),
                            ft.Text(f"${t['monto_usd']:.2f}", size=12,
                                    color="#f1f5f9", weight=ft.FontWeight.W_600),
                            ft.Text(f"Bs.{t['monto_bs']:,.0f}", size=11,
                                    color="#64748b"),
                            ft.Text(t["referencia"] or "", size=10, color="#475569"),
                        ],
                        spacing=6,
                    ),
                    bgcolor="#1e293b", border_radius=6,
                    padding=ft.padding.symmetric(horizontal=10, vertical=5),
                )
            )

    def recalc_totales():
        suma_usd = sum(p.get("monto_usd", 0) for p in pagos_state.values())
        restante = total_debe - suma_usd
        sobrante = max(suma_usd - total_debe, 0.0)

        suma_pagos_t.value = f"Suma pagos: ${suma_usd:.2f}"
        restante_t.value   = (f"Restante: ${restante:.2f}"
                              if restante > 0 else "✓ Monto completo")
        restante_t.color   = "#fbbf24" if restante > 0 else "#4ade80"
        sobrante_t.value   = (f"Sobrante (irá a saldo a favor): ${sobrante:.2f}"
                              if sobrante > 0.01 else "")

        if btn_finalizar.current:
            btn_finalizar.current.disabled = suma_usd < total_debe - 0.001
        page.update()

    def on_payment_change(idx, data):
        pagos_state[idx] = data
        recalc_totales()

    def add_payment_row(e=None):
        idx = next_idx[0]
        next_idx[0] += 1

        def on_remove(remove_idx):
            if remove_idx in pagos_state:
                del pagos_state[remove_idx]
            # Remove widget
            pagos_col.controls = [
                c for c in pagos_col.controls
                if not (hasattr(c, '_pago_idx') and c._pago_idx == remove_idx)
            ]
            recalc_totales()
            page.update()

        row = PaymentRow(idx, on_remove, on_payment_change, tasa)
        row._pago_idx = idx
        pagos_col.controls.append(row)
        pagos_state[idx] = {"metodo": "Efectivo USD", "monto_usd": 0.0,
                             "monto_bs": 0.0, "referencia": ""}
        recalc_totales()
        page.update()

    def validate_refs() -> str | None:
        """Retorna mensaje de error si falta referencia obligatoria."""
        for idx, p in pagos_state.items():
            if p["metodo"] in REQUIRE_REF and not p.get("referencia", "").strip():
                return f"El pago #{idx + 1} ({p['metodo']}) requiere número de referencia."
        return None

    def finalizar(e):
        error = validate_refs()
        if error:
            page.snack_bar = ft.SnackBar(ft.Text(error, color="#ef4444"),
                                          bgcolor="#1e293b")
            page.snack_bar.open = True
            page.update()
            return

        suma_usd = sum(p.get("monto_usd", 0) for p in pagos_state.values())
        sobrante = max(suma_usd - total_debe, 0.0)
        now = datetime.now().isoformat()

        # Registrar cada pago
        for p in pagos_state.values():
            if p["monto_usd"] <= 0:
                continue
            db.create_transaccion({
                "registro_id": reg_id,
                "monto_usd":   round(p["monto_usd"], 4),
                "tasa_cambio": tasa,
                "monto_bs":    round(p["monto_bs"], 2),
                "metodo_pago": p["metodo"],
                "tipo":        "Pago",
                "fecha_hora":  now,
                "usuario_id":  user["id"],
                "referencia":  p.get("referencia", ""),
                "descripcion": f"Hab.{room_num} - {dias}n",
            })

        # Check-out y actualización de saldo
        nuevo_saldo = round(saldo_hues + sobrante, 2)
        db.checkout_registro(reg_id, room_num, huesped["id"], nuevo_saldo)

        # Mensaje de confirmación
        msg = f"✓ Check-out completado. Total cobrado: ${suma_usd:.2f}"
        if sobrante > 0.01:
            msg += f" | Saldo a favor: ${sobrante:.2f}"
        elif nuevo_saldo < 0:
            msg += f" | Deuda registrada: ${abs(nuevo_saldo):.2f}"

        open_receipt(suma_usd, sobrante, nuevo_saldo)

    def open_receipt(cobrado, sobrante, saldo_nuevo):
        txns = db.get_transacciones_registro(reg_id)
        rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(t["metodo_pago"], color="#cbd5e1", size=12)),
                ft.DataCell(ft.Text(f"${t['monto_usd']:.2f}", color="#4ade80", size=12)),
                ft.DataCell(ft.Text(f"Bs.{t['monto_bs']:,.0f}", color="#22d3ee", size=12)),
                ft.DataCell(ft.Text(t.get("referencia", "") or "", color="#64748b", size=11)),
            ])
            for t in txns if t["tipo"] == "Pago"
        ]

        saldo_color = "#4ade80" if saldo_nuevo >= 0 else "#ef4444"
        saldo_label = (f"Saldo a favor: ${saldo_nuevo:.2f}"
                       if saldo_nuevo > 0
                       else f"Deuda registrada: ${abs(saldo_nuevo):.2f}"
                       if saldo_nuevo < 0
                       else "Sin saldo")

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row(controls=[
                ft.Icon(ft.icons.CHECK_CIRCLE, color="#4ade80"),
                ft.Text("Check-out Completado", color="#f1f5f9"),
            ], spacing=8),
            bgcolor="#1e293b",
            content=ft.Column(
                controls=[
                    ft.Text(f"{huesped['nombres']}", color="#f1f5f9", size=14,
                            weight=ft.FontWeight.W_600),
                    ft.Text(f"Hab. #{room_num} | {dias} noche(s)", color="#94a3b8", size=12),
                    ft.Divider(color="#334155"),
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("Método", color="#64748b", size=11)),
                            ft.DataColumn(ft.Text("USD",    color="#64748b", size=11)),
                            ft.DataColumn(ft.Text("Bs.",    color="#64748b", size=11)),
                            ft.DataColumn(ft.Text("Ref.",   color="#64748b", size=11)),
                        ],
                        rows=rows,
                    ),
                    ft.Divider(color="#334155"),
                    ft.Text(f"Total cobrado: ${cobrado:.2f}",
                            size=16, color="#4ade80", weight=ft.FontWeight.BOLD),
                    ft.Text(saldo_label, size=13, color=saldo_color),
                ],
                scroll=ft.ScrollMode.AUTO,
                width=420,
                spacing=8,
            ),
            actions=[
                ft.ElevatedButton(
                    "Ir al Dashboard",
                    icon=ft.icons.DASHBOARD,
                    on_click=lambda e: (setattr(dialog, "open", False),
                                        navigate("/dashboard")),
                    style=ft.ButtonStyle(bgcolor={"": "#3b82f6"}, color={"": "#ffffff"}),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.dialog = dialog
        dialog.open  = True
        page.update()

    def cobro_parcial(e):
        """Registrar pago parcial sin hacer checkout."""
        error = validate_refs()
        if error:
            page.snack_bar = ft.SnackBar(ft.Text(error, color="#ef4444"),
                                          bgcolor="#1e293b")
            page.snack_bar.open = True
            page.update()
            return

        now = datetime.now().isoformat()
        for p in pagos_state.values():
            if p["monto_usd"] <= 0:
                continue
            db.create_transaccion({
                "registro_id": reg_id,
                "monto_usd":   round(p["monto_usd"], 4),
                "tasa_cambio": tasa,
                "monto_bs":    round(p["monto_bs"], 2),
                "metodo_pago": p["metodo"],
                "tipo":        "Pago",
                "fecha_hora":  now,
                "usuario_id":  user["id"],
                "referencia":  p.get("referencia", ""),
                "descripcion": f"Pago parcial Hab.{room_num}",
            })

        # Limpiar pagos actuales
        pagos_state.clear()
        pagos_col.controls.clear()
        page.snack_bar = ft.SnackBar(
            ft.Text("✓ Pago parcial registrado.", color="#4ade80"),
            bgcolor="#1e293b"
        )
        page.snack_bar.open = True
        load_historial()
        recalc_totales()
        page.update()

    # ── Init ──────────────────────────────────────────────────────────────────
    load_historial()
    add_payment_row()

    # ── Layout ────────────────────────────────────────────────────────────────
    header = ft.Container(
        content=ft.Row(
            controls=[
                ft.IconButton(
                    ft.icons.ARROW_BACK, icon_color="#94a3b8",
                    on_click=lambda e: navigate("/dashboard"),
                ),
                ft.Column(
                    controls=[
                        ft.Text("Módulo de Pagos", size=18, color="#f1f5f9",
                                weight=ft.FontWeight.BOLD),
                        ft.Text(
                            f"Hab. #{room_num} — {huesped['nombres']}  |  "
                            f"Tasa: {tasa} Bs/$",
                            size=12, color="#64748b",
                        ),
                    ], spacing=2,
                ),
            ], spacing=8,
        ),
        bgcolor="#1e293b",
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        border=ft.border.only(bottom=ft.BorderSide(1, "#334155")),
    )

    resumen_card = ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Resumen de Cargo", size=13, color="#64748b",
                        weight=ft.FontWeight.W_600),
                ft.Row(
                    controls=[
                        ft.Column(
                            controls=[
                                ft.Text(f"{dias} noche(s) × ${precio_hab:.0f}",
                                        size=12, color="#94a3b8"),
                                ft.Text(f"Subtotal: ${subtotal:.2f}",
                                        size=13, color="#cbd5e1"),
                                ft.Text(f"Ya pagado: ${ya_pagado:.2f}",
                                        size=12, color="#94a3b8")
                                if ya_pagado > 0 else ft.Text(""),
                                ft.Text(f"Deuda anterior: ${deuda_ant:.2f}",
                                        size=12, color="#ef4444")
                                if deuda_ant > 0 else ft.Text(""),
                                ft.Text(f"Saldo a favor: -${favor_ant:.2f}",
                                        size=12, color="#4ade80")
                                if favor_ant > 0 else ft.Text(""),
                            ], spacing=3, expand=True,
                        ),
                        ft.Column(
                            controls=[
                                ft.Text("TOTAL", size=11, color="#64748b"),
                                total_text,
                                total_bs_txt,
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                            spacing=2,
                        ),
                    ],
                ),
                ft.Divider(color="#334155"),
                suma_pagos_t,
                restante_t,
                sobrante_t,
            ],
            spacing=6,
        ),
        bgcolor="#1e293b",
        border_radius=10,
        padding=14,
        border=ft.border.all(1, "#334155"),
    )

    left_panel = ft.Container(
        content=ft.Column(
            controls=[
                resumen_card,
                ft.Divider(color="#334155", height=16),
                ft.Text("Pagos Registrados en esta Estancia",
                        size=12, color="#64748b", weight=ft.FontWeight.W_600),
                historial_col,
            ],
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        ),
        expand=1,
        padding=ft.padding.only(right=8),
    )

    right_panel = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Agregar Líneas de Pago",
                                size=14, color="#f1f5f9",
                                weight=ft.FontWeight.W_600),
                        ft.OutlinedButton(
                            "+ Línea",
                            icon=ft.icons.ADD,
                            on_click=add_payment_row,
                            style=ft.ButtonStyle(
                                color={"": "#3b82f6"},
                                side=ft.BorderSide(1, "#3b82f6"),
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                pagos_col,
                ft.Divider(color="#334155", height=16),
                ft.Row(
                    controls=[
                        ft.OutlinedButton(
                            "Pago Parcial",
                            icon=ft.icons.PAYMENT,
                            on_click=cobro_parcial,
                            tooltip="Registrar pago sin hacer check-out",
                            style=ft.ButtonStyle(
                                color={"": "#fbbf24"},
                                side=ft.BorderSide(1, "#fbbf24"),
                            ),
                        ),
                        ft.ElevatedButton(
                            ref=btn_finalizar,
                            text="Finalizar y Check-out",
                            icon=ft.icons.CHECK_CIRCLE_OUTLINE,
                            on_click=finalizar,
                            disabled=True,
                            style=ft.ButtonStyle(
                                bgcolor={"": "#16a34a", ft.MaterialState.DISABLED: "#1e3a2f"},
                                color={"": "#ffffff",  ft.MaterialState.DISABLED: "#4b7a5a"},
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        ),
        expand=1,
        padding=ft.padding.only(left=8),
    )

    body = ft.Row(
        controls=[left_panel, ft.VerticalDivider(color="#334155"), right_panel],
        expand=True,
        spacing=0,
    )

    return ft.View(
        route="/payments",
        bgcolor="#0f172a",
        padding=0,
        controls=[
            ft.Column(
                controls=[
                    header,
                    ft.Container(content=body, expand=True,
                                 padding=ft.padding.symmetric(horizontal=16, vertical=12)),
                ],
                expand=True,
                spacing=0,
            )
        ],
    )
