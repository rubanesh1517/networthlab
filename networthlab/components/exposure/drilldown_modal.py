"""In-page modal listing per-position contribution rows for a (dimension, bucket)."""

import reflex as rx

from ...state.exposure_state import ExposureState
from ...styles.theme import COLORS


def _header() -> rx.Component:
    return rx.flex(
        rx.text(
            rx.cond(
                ExposureState.drilldown_bucket != "",
                ExposureState.drilldown_dimension + " — " + ExposureState.drilldown_bucket,
                ExposureState.drilldown_dimension,
            ),
            font_size="18px",
            font_weight="600",
        ),
        rx.button("Close", on_click=ExposureState.close_drilldown, variant="ghost"),
        justify="between",
        align="center",
        width="100%",
        margin_bottom="12px",
    )


def _row(row: rx.Var) -> rx.Component:
    return rx.table.row(
        rx.table.cell(row["bucket"]),
        rx.table.cell(row["source_position"]),
        rx.table.cell(row["source_account_id"]),
        rx.table.cell(row["value_cad_fmt"], text_align="right"),
        rx.table.cell(row["weight_pct"], text_align="right"),
        rx.table.cell(row["source"]),
    )


def _sortable_header(label: str, sort_key: str) -> rx.Component:
    """Column header that toggles sort on click. Shows ↑/↓ when active."""
    is_active = ExposureState.drilldown_sort_key == sort_key
    return rx.table.column_header_cell(
        rx.hstack(
            rx.text(label, font_weight="600"),
            rx.cond(
                is_active,
                rx.text(rx.cond(ExposureState.drilldown_sort_desc, "↓", "↑")),
                rx.fragment(),
            ),
            spacing="1",
            cursor="pointer",
            on_click=ExposureState.set_drilldown_sort(sort_key),
        )
    )


def drilldown_modal() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            _header(),
            rx.box(
                rx.table.root(
                    rx.table.header(
                        rx.table.row(
                            _sortable_header("Bucket", "bucket"),
                            _sortable_header("Position", "source_position"),
                            _sortable_header("Account", "source_account_id"),
                            _sortable_header("Value (CAD)", "value_cad_num"),
                            _sortable_header("Weight", "weight_num"),
                            _sortable_header("Source", "source"),
                        )
                    ),
                    rx.table.body(
                        rx.foreach(ExposureState.drilldown_rows, _row),
                    ),
                ),
                max_height="60vh",
                overflow_y="auto",
            ),
            max_width="900px",
            background=COLORS["bg_primary"],
        ),
        open=ExposureState.drilldown_open,
        on_open_change=ExposureState.set_drilldown_open,
    )
