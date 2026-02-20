"""
views/checkin.py - Flujo completo de Check-in y Check-out
"""
import flet as ft
from datetime import datetime, date, timedelta
import database as db
from components.payment_row import REQUIRE_REF


def _field(label, value="", multiline=False, expand=1, keyboard=ft.KeyboardType.TEXT,
           hint="", read_only=False):
    return ft.TextField(
        label=label,
        value=str(value),
        expand=expand,
        multiline=multiline,
        min_lines=2 if multiline else 1,
        keyboard_type=keyboard,
        hint_text=hint,
        read_only=read_only,
        border_color="#334155",
        focused_border_color="#3b82f6",
        text_style=ft.TextStyle(color="#f1f5f9"),
        label_style=ft.TextStyle(color="#94a3b8"),
        dense=True,
    )


def CheckinView(page: ft.Page, room_number: int, navigate, checkin_mode: str = "checkin") -> ft.View:
    user     = page.session.get("current_user")
    hab      = db.get_habitacion(room_number)
    cfg      = db.get_config()
    tasa     = cfg.get("tasa_dolar_bs", 36.0)
    hoy      = date.today()

    # ── Estado ───────────────────────────────────────────────────────────────
    state = {
        "huesped":      None,    # dict del huésped principal
        "registro":     None,    # dict del registro activo (checkout mode)
        "acompanantes": [],
        "step":         1,       # 1=buscar, 2=datos, 3=configurar, 4=prefactura
    }

    if checkin_mode == "checkout":
        reg = db.get_registro_activo(room_number)
        if reg:
            state["registro"]     = reg
            state["huesped"]      = db.get_huesped_by_id(reg["guest_id"])
            state["acompanantes"] = db.get_acompanantes(reg["id"])
            state["step"]         = 4   # Ir directo a factura

    # ── Refs y controles ─────────────────────────────────────────────────────
    content_area  = ft.Ref[ft.Column]()
    step_indicator = ft.Ref[ft.Row]()

    # ── STEP 1: Búsqueda ─────────────────────────────────────────────────────
    search_field = ft.TextField(
        label="Cédula / Pasaporte",
        autofocus=True,
        width=300,
        border_color="#334155",
        focused_border_color="#3b82f6",
        text_style=ft.TextStyle(color="#f1f5f9"),
        label_style=ft.TextStyle(color="#94a3b8"),
        prefix_icon=ft.icons.SEARCH,
    )
    search_result = ft.Text("", color="#94a3b8", size=13)

    # ── STEP 2: Formulario huésped ────────────────────────────────────────────
    f_doc   = _field("Documento *", hint="V-12345678")
    f_nom   = _field("Nombres y Apellidos *")
    f_tel   = _field("Teléfono", keyboard=ft.KeyboardType.PHONE)
    f_nac   = _field("Fecha Nacimiento", hint="YYYY-MM-DD")
    f_nacio = ft.Dropdown(
        label="Nacionalidad",
        value="Venezolano",
        options=[ft.dropdown.Option(n) for n in
                 ["Venezolano", "Colombiano", "Peruano", "Ecuatoriano",
                  "Panameño", "Estadounidense", "Otro"]],
        expand=1,
        border_color="#334155",
        color="#f1f5f9",
        label_style=ft.TextStyle(color="#94a3b8"),
    )
    f_prof  = _field("Profesión", expand=1)
    f_vehi  = _field("Vehículo (placa)", expand=1)

    # ── STEP 3: Configurar estancia ────────────────────────────────────────────
    fecha_entrada_ctrl = ft.TextField(
        label="Fecha Entrada",
        value=hoy.strftime("%Y-%m-%d"),
        read_only=True,
        expand=1,
        border_color="#334155",
        text_style=ft.TextStyle(color="#f1f5f9"),
        label_style=ft.TextStyle(color="#94a3b8"),
    )
    fecha_salida_ctrl = ft.TextField(
        label="Fecha Salida Prevista",
        value=(hoy + timedelta(days=1)).strftime("%Y-%m-%d"),
        expand=1,
        border_color="#334155",
        focused_border_color="#3b82f6",
        text_style=ft.TextStyle(color="#f1f5f9"),
        label_style=ft.TextStyle(color="#94a3b8"),
        hint_text="YYYY-MM-DD",
    )
    notas_ctrl = _field("Notas / Observaciones", multiline=True)
    acompanantes_list = ft.Column(spacing=4)
    resumen_estancia  = ft.Text("", color="#94a3b8", size=13)

    # ── STEP 4: Pre-factura ────────────────────────────────────────────────────
    prefactura_col = ft.Column(spacing=6)

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════════

    def snack(msg, color="#4ade80"):
        page.snack_bar = ft.SnackBar(ft.Text(msg, color=color), bgcolor="#1e293b")
        page.snack_bar.open = True
        page.update()

    def calcular_dias(entrada_str: str, salida_str: str) -> int:
        try:
            e = datetime.strptime(entrada_str, "%Y-%m-%d").date()
            s = datetime.strptime(salida_str,  "%Y-%m-%d").date()
            d = (s - e).days
            return max(d, 1)
        except Exception:
            return 1

    def calcular_total() -> dict:
        dias    = calcular_dias(fecha_entrada_ctrl.value, fecha_salida_ctrl.value)
        precio  = hab["precio_usd"]
        subtotal= dias * precio
        saldo   = state["huesped"]["saldo_acumulado"] if state["huesped"] else 0.0
        deuda   = abs(saldo) if saldo < 0 else 0.0
        favor   = saldo if saldo > 0 else 0.0
        total   = subtotal + deuda - favor
        total   = max(total, 0.0)
        return {
            "dias":     dias,
            "precio":   precio,
            "subtotal": subtotal,
            "deuda":    deuda,
            "favor":    favor,
            "total":    total,
            "total_bs": db.usd_to_bs(total),
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # RENDERIZAR PASOS
    # ═══════════════════════════════════════════════════════════════════════════

    def update_step_indicator():
        if not step_indicator.current:
            return
        steps = ["Buscar", "Datos", "Estancia", "Factura"]
        controls = []
        for i, s in enumerate(steps, 1):
            active = (i == state["step"])
            done   = (i < state["step"])
            controls.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Container(
                                content=ft.Text(str(i) if not done else "✓",
                                                color="#ffffff", size=12,
                                                weight=ft.FontWeight.BOLD),
                                width=28, height=28,
                                bgcolor="#3b82f6" if active else ("#1a6b3c" if done else "#334155"),
                                border_radius=14,
                                alignment=ft.alignment.center,
                            ),
                            ft.Text(s, size=10,
                                    color="#f1f5f9" if active else "#64748b"),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=3,
                    ),
                )
            )
            if i < len(steps):
                controls.append(ft.Container(
                    width=40, height=2,
                    bgcolor="#3b82f6" if done else "#334155",
                    margin=ft.margin.only(bottom=14),
                ))
        step_indicator.current.controls = controls

    def render_step():
        update_step_indicator()
        if not content_area.current:
            return

        step = state["step"]
        if step == 1:
            content_area.current.controls = [build_step1()]
        elif step == 2:
            content_area.current.controls = [build_step2()]
        elif step == 3:
            content_area.current.controls = [build_step3()]
        elif step == 4:
            content_area.current.controls = [build_step4()]
        page.update()

    # ─── PASO 1 ───────────────────────────────────────────────────────────────
    def build_step1():
        def do_search(e):
            doc = search_field.value.strip().upper()
            if not doc:
                search_result.value = "Ingrese un documento."
                page.update()
                return
            huesped = db.get_huesped_by_documento(doc)
            if huesped:
                state["huesped"] = huesped
                # Rellenar formulario
                f_doc.value   = huesped["documento"]
                f_nom.value   = huesped["nombres"]
                f_tel.value   = huesped.get("telefono", "")
                f_nac.value   = huesped.get("fecha_nacimiento", "")
                f_nacio.value = huesped.get("nacionalidad", "Venezolano")
                f_prof.value  = huesped.get("profesion", "")
                f_vehi.value  = huesped.get("vehiculo", "")
                saldo = huesped["saldo_acumulado"]
                saldo_str = (f"Saldo a favor: ${saldo:.2f}" if saldo > 0
                             else f"Deuda pendiente: ${abs(saldo):.2f}" if saldo < 0
                             else "Sin saldo previo")
                search_result.value = f"✓ Huésped encontrado: {huesped['nombres']}  |  {saldo_str}"
                search_result.color = "#4ade80"
                state["step"] = 3  # Ya tenemos datos, saltar a configurar
                render_step()
            else:
                search_result.value = f"Huésped nuevo. Complete el formulario de registro."
                search_result.color = "#fbbf24"
                f_doc.value = doc
                state["step"] = 2
                render_step()

        search_field.on_submit = do_search

        return ft.Column(
            controls=[
                ft.Text("Buscar Huésped", size=16, color="#f1f5f9",
                        weight=ft.FontWeight.W_600),
                ft.Row(
                    controls=[
                        search_field,
                        ft.ElevatedButton(
                            "Buscar",
                            icon=ft.icons.SEARCH,
                            on_click=do_search,
                            style=ft.ButtonStyle(
                                bgcolor={"": "#3b82f6"},
                                color={"": "#ffffff"},
                            ),
                        ),
                    ],
                    spacing=8,
                ),
                search_result,
            ],
            spacing=12,
        )

    # ─── PASO 2 ───────────────────────────────────────────────────────────────
    def build_step2():
        def save_huesped(e):
            if not f_doc.value.strip() or not f_nom.value.strip():
                snack("Documento y Nombre son obligatorios.", "#ef4444")
                return
            data = {
                "documento":        f_doc.value.strip().upper(),
                "nombres":          f_nom.value.strip(),
                "telefono":         f_tel.value.strip(),
                "fecha_nacimiento": f_nac.value.strip(),
                "nacionalidad":     f_nacio.value,
                "profesion":        f_prof.value.strip(),
                "vehiculo":         f_vehi.value.strip(),
            }
            # Verificar si ya existe (puede venir de búsqueda)
            existing = db.get_huesped_by_documento(data["documento"])
            if existing:
                data["id"] = existing["id"]
                db.update_huesped(data)
                state["huesped"] = db.get_huesped_by_id(existing["id"])
            else:
                hid = db.create_huesped(data)
                state["huesped"] = db.get_huesped_by_id(hid)
            state["step"] = 3
            render_step()

        return ft.Column(
            controls=[
                ft.Text("Datos del Huésped", size=16, color="#f1f5f9",
                        weight=ft.FontWeight.W_600),
                ft.Row(controls=[f_doc, f_nom], spacing=8),
                ft.Row(controls=[f_tel, f_nac], spacing=8),
                ft.Row(controls=[f_nacio, f_prof, f_vehi], spacing=8),
                ft.Row(
                    controls=[
                        ft.TextButton("← Volver",
                                      on_click=lambda e: (state.update({"step": 1}), render_step()),
                                      style=ft.ButtonStyle(color={"": "#94a3b8"})),
                        ft.ElevatedButton(
                            "Guardar y Continuar →",
                            icon=ft.icons.ARROW_FORWARD,
                            on_click=save_huesped,
                            style=ft.ButtonStyle(
                                bgcolor={"": "#3b82f6"}, color={"": "#ffffff"},
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ],
            spacing=12,
        )

    # ─── PASO 3 ───────────────────────────────────────────────────────────────
    def build_step3():
        def add_acompanante_dialog(e):
            doc_f = ft.TextField(
                label="Documento acompañante",
                border_color="#334155",
                focused_border_color="#3b82f6",
                text_style=ft.TextStyle(color="#f1f5f9"),
                label_style=ft.TextStyle(color="#94a3b8"),
                autofocus=True,
            )
            nom_f = ft.TextField(
                label="Nombres (si es nuevo)",
                border_color="#334155",
                focused_border_color="#3b82f6",
                text_style=ft.TextStyle(color="#f1f5f9"),
                label_style=ft.TextStyle(color="#94a3b8"),
            )
            msg_f = ft.Text("", color="#94a3b8", size=12)

            def confirm_acomp(e):
                doc = doc_f.value.strip().upper()
                if not doc:
                    return
                hg = db.get_huesped_by_documento(doc)
                if not hg:
                    if not nom_f.value.strip():
                        msg_f.value = "Ingrese nombre para crear nuevo huésped."
                        page.update()
                        return
                    hid = db.create_huesped({
                        "documento": doc,
                        "nombres":   nom_f.value.strip(),
                        "telefono": "", "fecha_nacimiento": "",
                        "nacionalidad": "Venezolano",
                        "profesion": "", "vehiculo": "",
                    })
                    hg = db.get_huesped_by_id(hid)

                if any(a["id"] == hg["id"] for a in state["acompanantes"]):
                    msg_f.value = "Ya está en la lista."
                    page.update()
                    return
                if hg["id"] == state["huesped"]["id"]:
                    msg_f.value = "Es el huésped principal."
                    page.update()
                    return

                state["acompanantes"].append(hg)
                dialog.open = False
                refresh_acompanantes()
                page.update()

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Agregar Acompañante", color="#f1f5f9"),
                bgcolor="#1e293b",
                content=ft.Column(controls=[doc_f, nom_f, msg_f], spacing=8, tight=True),
                actions=[
                    ft.TextButton("Cancelar",
                                  on_click=lambda e: (setattr(dialog, "open", False), page.update()),
                                  style=ft.ButtonStyle(color={"": "#94a3b8"})),
                    ft.ElevatedButton("Agregar", on_click=confirm_acomp,
                                      style=ft.ButtonStyle(bgcolor={"": "#3b82f6"},
                                                           color={"": "#ffffff"})),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
            page.dialog = dialog
            dialog.open  = True
            page.update()

        def refresh_acompanantes():
            acompanantes_list.controls = []
            for a in state["acompanantes"]:
                acompanantes_list.controls.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.icons.PERSON_OUTLINE, size=14, color="#94a3b8"),
                                ft.Text(f"{a['nombres']} ({a['documento']})",
                                        color="#cbd5e1", size=12, expand=True),
                                ft.IconButton(
                                    ft.icons.CLOSE, icon_size=14, icon_color="#ef4444",
                                    on_click=lambda e, hid=a["id"]: remove_acomp(hid),
                                ),
                            ],
                        ),
                        bgcolor="#1e293b", border_radius=6,
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    )
                )
            page.update()

        def remove_acomp(hid):
            state["acompanantes"] = [a for a in state["acompanantes"] if a["id"] != hid]
            refresh_acompanantes()

        def update_resumen(e=None):
            t = calcular_total()
            resumen_estancia.value = (
                f"Habitación #{room_number} ({hab['tipo']})  |  "
                f"{t['dias']} noche(s) × ${t['precio']:.0f} = ${t['subtotal']:.2f}  |  "
                f"Total: ${t['total']:.2f}  (Bs. {t['total_bs']:,.2f})"
            )
            page.update()

        fecha_salida_ctrl.on_change = update_resumen
        update_resumen()
        refresh_acompanantes()

        def go_prefactura(e):
            fs = fecha_salida_ctrl.value.strip()
            try:
                datetime.strptime(fs, "%Y-%m-%d")
            except ValueError:
                snack("Fecha de salida inválida (YYYY-MM-DD).", "#ef4444")
                return
            state["step"] = 4
            render_step()

        return ft.Column(
            controls=[
                ft.Text("Configurar Estancia", size=16, color="#f1f5f9",
                        weight=ft.FontWeight.W_600),
                ft.Container(
                    content=ft.Column(controls=[
                        ft.Text(f"Huésped: {state['huesped']['nombres']}",
                                color="#94a3b8", size=13),
                        ft.Text(f"Habitación #{room_number} — {hab['tipo']} (${hab['precio_usd']:.0f}/noche)",
                                color="#94a3b8", size=13),
                    ], spacing=4),
                    bgcolor="#1e293b", border_radius=8,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                ),
                ft.Row(controls=[fecha_entrada_ctrl, fecha_salida_ctrl], spacing=8),
                notas_ctrl,
                resumen_estancia,
                ft.Divider(color="#334155"),
                ft.Row(
                    controls=[
                        ft.Text("Acompañantes", size=13, color="#cbd5e1",
                                weight=ft.FontWeight.W_500),
                        ft.OutlinedButton(
                            "+ Agregar",
                            icon=ft.icons.PERSON_ADD_OUTLINED,
                            on_click=add_acompanante_dialog,
                            style=ft.ButtonStyle(color={"": "#3b82f6"},
                                                 side=ft.BorderSide(1, "#3b82f6")),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                acompanantes_list,
                ft.Row(
                    controls=[
                        ft.TextButton("← Volver",
                                      on_click=lambda e: (state.update({"step": 2}), render_step()),
                                      style=ft.ButtonStyle(color={"": "#94a3b8"})),
                        ft.ElevatedButton(
                            "Ver Pre-Factura →",
                            icon=ft.icons.RECEIPT_OUTLINED,
                            on_click=go_prefactura,
                            style=ft.ButtonStyle(
                                bgcolor={"": "#3b82f6"}, color={"": "#ffffff"},
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ],
            spacing=10,
        )

    # ─── PASO 4 ───────────────────────────────────────────────────────────────
    def build_step4():
        huesped = state["huesped"]
        t       = calcular_total()
        saldo   = huesped["saldo_acumulado"]

        if checkin_mode == "checkout" and state["registro"]:
            reg = state["registro"]
            # Recalcular con registro existente
            dias  = calcular_dias(reg["fecha_entrada"], reg["fecha_salida_prevista"])
            subtotal = dias * hab["precio_usd"]
            ya_pagado = db.get_total_pagado_usd(reg["id"])
            pendiente = max(subtotal - ya_pagado + (abs(saldo) if saldo < 0 else 0)
                            - (saldo if saldo > 0 else 0), 0.0)
        else:
            pendiente = t["total"]
            ya_pagado = 0.0

        # Filas de la pre-factura
        rows_data = [
            (f"Habitación #{room_number} ({hab['tipo']})",
             f"{t['dias']} noche(s) × ${t['precio']:.2f}",
             f"${t['subtotal']:.2f}"),
        ]
        if t["favor"] > 0:
            rows_data.append(("Saldo a Favor", "Aplicado automáticamente",
                              f"-${t['favor']:.2f}"))
        if t["deuda"] > 0:
            rows_data.append(("Deuda Anterior", "Cargo adicional",
                              f"+${t['deuda']:.2f}"))
        if checkin_mode == "checkout" and ya_pagado > 0:
            rows_data.append(("Ya Pagado", "", f"-${ya_pagado:.2f}"))

        table_rows = [
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(d[0], color="#cbd5e1", size=13)),
                ft.DataCell(ft.Text(d[1], color="#94a3b8", size=12)),
                ft.DataCell(ft.Text(d[2], color="#4ade80" if d[2].startswith("-") else "#f1f5f9",
                                    size=13, weight=ft.FontWeight.W_600)),
            ])
            for d in rows_data
        ]

        def do_checkin(e):
            try:
                reg_id = db.create_registro(
                    huesped["id"], room_number,
                    fecha_entrada_ctrl.value, fecha_salida_ctrl.value,
                    notas_ctrl.value
                )
                for ac in state["acompanantes"]:
                    db.add_acompanante(reg_id, ac["id"])

                # Registrar cargo
                now = datetime.now().isoformat()
                db.create_transaccion({
                    "registro_id": reg_id,
                    "monto_usd":   t["subtotal"],
                    "tasa_cambio": tasa,
                    "monto_bs":    db.usd_to_bs(t["subtotal"]),
                    "metodo_pago": "Cargo",
                    "tipo":        "Cargo",
                    "fecha_hora":  now,
                    "usuario_id":  user["id"],
                    "referencia":  "",
                    "descripcion": f"Cargo estancia {t['dias']} noche(s)",
                })

                # Navegar a pagos
                page.session.set("selected_room",    room_number)
                page.session.set("active_registro_id", reg_id)
                navigate("/payments")
            except Exception as ex:
                snack(f"Error: {ex}", "#ef4444")

        def do_checkout(e):
            navigate("/payments",
                     selected_room=room_number,
                     active_registro_id=state["registro"]["id"])

        action_btn = ft.ElevatedButton(
            "Confirmar Check-in y Registrar Pago →" if checkin_mode == "checkin"
            else "Ir a Pagos / Check-out →",
            icon=ft.icons.PAYMENTS_OUTLINED,
            on_click=do_checkin if checkin_mode == "checkin" else do_checkout,
            style=ft.ButtonStyle(
                bgcolor={"": "#16a34a" if checkin_mode == "checkin" else "#9333ea"},
                color={"": "#ffffff"},
            ),
        )

        return ft.Column(
            controls=[
                ft.Text("Pre-Factura", size=16, color="#f1f5f9",
                        weight=ft.FontWeight.W_600),
                ft.Container(
                    content=ft.Column(controls=[
                        ft.Text(f"Huésped: {huesped['nombres']}",
                                color="#f1f5f9", size=14),
                        ft.Text(f"Documento: {huesped['documento']}",
                                color="#94a3b8", size=12),
                        ft.Text(f"Acompañantes: {len(state['acompanantes'])}",
                                color="#94a3b8", size=12),
                    ], spacing=4),
                    bgcolor="#1e293b", border_radius=8,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                ),
                ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text("Concepto", color="#64748b", size=12)),
                        ft.DataColumn(ft.Text("Detalle",  color="#64748b", size=12)),
                        ft.DataColumn(ft.Text("Monto",    color="#64748b", size=12)),
                    ],
                    rows=table_rows,
                    border=ft.border.all(1, "#334155"),
                    border_radius=8,
                    data_row_color={"hovered": "#1e293b"},
                ),
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text("TOTAL A PAGAR", size=12, color="#94a3b8"),
                                    ft.Text(f"${pendiente:.2f}",
                                            size=28, color="#4ade80",
                                            weight=ft.FontWeight.BOLD),
                                    ft.Text(f"Bs. {db.usd_to_bs(pendiente):,.2f}",
                                            size=14, color="#22d3ee"),
                                ],
                                spacing=2,
                            )
                        ],
                    ),
                    bgcolor="#1e293b", border_radius=8,
                    padding=ft.padding.symmetric(horizontal=16, vertical=12),
                ),
                ft.Row(
                    controls=[
                        ft.TextButton("← Modificar",
                                      on_click=lambda e: (state.update({"step": 3}), render_step()),
                                      style=ft.ButtonStyle(color={"": "#94a3b8"})),
                        action_btn,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
            ],
            spacing=12,
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # LAYOUT
    # ═══════════════════════════════════════════════════════════════════════════

    step_row = ft.Row(
        ref=step_indicator,
        controls=[],
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    main_col = ft.Column(
        ref=content_area,
        controls=[],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    header = ft.Container(
        content=ft.Row(
            controls=[
                ft.IconButton(
                    ft.icons.ARROW_BACK,
                    icon_color="#94a3b8",
                    on_click=lambda e: navigate("/dashboard"),
                ),
                ft.Column(
                    controls=[
                        ft.Text(
                            "Check-in" if checkin_mode == "checkin" else "Check-out / Gestión",
                            size=18, color="#f1f5f9", weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            f"Habitación #{room_number} — {hab['tipo']} | "
                            f"${hab['precio_usd']:.0f}/noche | Tasa: {tasa} Bs/$",
                            size=12, color="#64748b",
                        ),
                    ],
                    spacing=2,
                ),
            ],
            spacing=8,
        ),
        bgcolor="#1e293b",
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        border=ft.border.only(bottom=ft.BorderSide(1, "#334155")),
    )

    # Renderizar paso inicial
    update_step_indicator()

    view = ft.View(
        route="/checkin",
        bgcolor="#0f172a",
        padding=0,
        controls=[
            ft.Column(
                controls=[
                    header,
                    ft.Container(content=step_row, padding=12, bgcolor="#0f172a"),
                    ft.Container(
                        content=main_col,
                        expand=True,
                        padding=ft.padding.symmetric(horizontal=20, vertical=10),
                    ),
                ],
                expand=True,
                spacing=0,
            )
        ],
    )

    # Renderizar primer paso DESPUÉS de crear la vista
    def post_render(e=None):
        render_step()

    page.on_view_pop = lambda e: None

    # Defer rendering
    import threading
    def deferred():
        import time
        time.sleep(0.05)
        render_step()
    threading.Thread(target=deferred, daemon=True).start()

    return view
