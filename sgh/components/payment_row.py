"""
components/payment_row.py
Fila de pago individual para el módulo de pagos multi-método.
"""
import flet as ft

METODOS = ["Efectivo USD", "Efectivo BS", "Pago Móvil", "Transferencia", "Zelle", "Otro"]
REQUIRE_REF = {"Pago Móvil", "Transferencia", "Zelle"}


def PaymentRow(index: int, on_remove, on_change, tasa: float) -> ft.Card:
    """
    Componente fila de pago. Llama on_change(index, data) cuando cambia.
    data = {"metodo": str, "monto_usd": float, "monto_bs": float, "referencia": str}
    """
    state = {
        "metodo":    "Efectivo USD",
        "monto_raw": 0.0,
        "monto_usd": 0.0,
        "monto_bs":  0.0,
        "referencia": "",
        "es_bs":     False,
    }

    ref_field  = ft.Ref[ft.TextField]()
    bs_display = ft.Ref[ft.Text]()
    ref_row    = ft.Ref[ft.Row]()

    def recalculate(e=None):
        try:
            raw = float(monto_field.value.replace(",", ".")) if monto_field.value else 0.0
        except ValueError:
            raw = 0.0

        if state["es_bs"]:
            state["monto_bs"]  = raw
            state["monto_usd"] = round(raw / tasa, 4) if tasa else 0.0
        else:
            state["monto_usd"] = raw
            state["monto_bs"]  = round(raw * tasa, 2)

        state["monto_raw"] = raw
        if bs_display.current:
            bs_display.current.value = f"≈ Bs. {state['monto_bs']:,.2f}" if not state["es_bs"] \
                else f"≈ $ {state['monto_usd']:.4f}"
            bs_display.current.update()

        on_change(index, {
            "metodo":     state["metodo"],
            "monto_usd":  state["monto_usd"],
            "monto_bs":   state["monto_bs"],
            "referencia": state["referencia"],
        })

    def on_metodo_change(e):
        metodo = e.control.value
        state["metodo"]  = metodo
        state["es_bs"]   = (metodo == "Efectivo BS")

        # Mostrar/ocultar campo referencia
        if ref_row.current:
            ref_row.current.visible = metodo in REQUIRE_REF
            ref_row.current.update()

        recalculate()

    def on_ref_change(e):
        state["referencia"] = e.control.value
        on_change(index, {
            "metodo":     state["metodo"],
            "monto_usd":  state["monto_usd"],
            "monto_bs":   state["monto_bs"],
            "referencia": state["referencia"],
        })

    monto_field = ft.TextField(
        label="Monto",
        value="",
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=2,
        on_change=recalculate,
        border_color="#475569",
        focused_border_color="#3b82f6",
        text_style=ft.TextStyle(color="#f1f5f9"),
        label_style=ft.TextStyle(color="#94a3b8"),
        dense=True,
        suffix_text="USD",
    )

    metodo_dd = ft.Dropdown(
        label="Método",
        value="Efectivo USD",
        options=[ft.dropdown.Option(m) for m in METODOS],
        expand=2,
        on_change=on_metodo_change,
        border_color="#475569",
        focused_border_color="#3b82f6",
        color="#f1f5f9",
        label_style=ft.TextStyle(color="#94a3b8"),
    )

    ref_field_ctrl = ft.TextField(
        label="Referencia *",
        ref=ref_field,
        expand=True,
        on_change=on_ref_change,
        border_color="#475569",
        focused_border_color="#3b82f6",
        text_style=ft.TextStyle(color="#f1f5f9"),
        label_style=ft.TextStyle(color="#94a3b8"),
        dense=True,
    )

    return ft.Card(
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text(f"Pago #{index + 1}",
                                    size=12, color="#64748b",
                                    weight=ft.FontWeight.W_600),
                            ft.Text(ref=bs_display, value="≈ Bs. 0.00",
                                    size=12, color="#22d3ee"),
                            ft.IconButton(
                                icon=ft.icons.DELETE_OUTLINE,
                                icon_color="#ef4444",
                                icon_size=18,
                                tooltip="Eliminar",
                                on_click=lambda e: on_remove(index),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Row(controls=[metodo_dd, monto_field], spacing=8),
                    ft.Row(
                        ref=ref_row,
                        controls=[ref_field_ctrl],
                        visible=False,
                    ),
                ],
                spacing=6,
            ),
            padding=10,
        ),
        elevation=2,
        color="#1e293b",
    )
