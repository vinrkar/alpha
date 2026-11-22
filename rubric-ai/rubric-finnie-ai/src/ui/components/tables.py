import streamlit as st

def render_sortable_table(
        table_id: str,
        items: list[dict],
        columns_config: list[dict],
        sort_key_state: str,
        sort_asc_state: str,
        default_sort: str = "pct_port",
        default_asc: bool = False,
        limit: int | None = None,
) -> tuple[list[dict], list[float]]:
    """Renders sortable column headers and returns sorted items and column widths."""
    if sort_key_state not in st.session_state:
        st.session_state[sort_key_state] = default_sort
    if sort_asc_state not in st.session_state:
        st.session_state[sort_asc_state] = default_asc

    active_sort_col = st.session_state[sort_key_state]
    active_sort_asc = st.session_state[sort_asc_state]

    def _toggle_sort(col_key: str) -> None:
        if st.session_state[sort_key_state] == col_key:
            st.session_state[sort_asc_state] = not st.session_state[sort_asc_state]
        else:
            st.session_state[sort_key_state] = col_key
            st.session_state[sort_asc_state] = default_asc

    try:
        sorted_items = sorted(
            items,
            key=lambda x: x.get(active_sort_col, 0),
            reverse=not active_sort_asc,
        )
    except TypeError:
        sorted_items = items

    if limit is not None:
        sorted_items = sorted_items[:limit]

    widths = [cfg["width"] for cfg in columns_config]
    header_cols = st.columns(widths)

    for hc, cfg in zip(header_cols, columns_config):
        key = cfg["key"]
        lbl = cfg["label"]
        with hc:
            if key == "idx":
                st.markdown(
                    f"<div style='font-size: 10px; font-weight: 700; color: #38bdf8; text-transform: uppercase;'>{lbl}</div>",
                    unsafe_allow_html=True,
                )
            else:
                arrow = ""
                if active_sort_col == key:
                    arrow = " ▲" if active_sort_asc else " ▼"
                st.button(
                    f"{lbl}{arrow}",
                    key=f"sort_{table_id}_{key}",
                    use_container_width=True,
                    on_click=_toggle_sort,
                    args=(key,),
                )

    st.markdown(
        "<hr style='margin: 4px 0 6px 0; border: 0; height: 2px; background: linear-gradient(90deg, #38bdf8 0%, rgba(56, 189, 248, 0.2) 100%);'>",
        unsafe_allow_html=True,
    )
    return sorted_items, widths

def render_table_cell(
        text: str,
        align: str = "left",
        color: str = "#cbd5e1",
        font_weight: str = "400",
        truncate: bool = False,
        monospace: bool = False,
        title: str | None = None,
) -> None:
    justify = {
        "left": "flex-start",
        "right": "flex-end",
        "center": "center",
    }.get(align, "flex-start")
    css_class = "table-cell-truncate" if truncate else "table-cell-nowrap"
    font_family = "font-family: monospace;" if monospace else ""
    title_attr = f' title="{title}"' if title else ""
    st.markdown(
        f"<div style='display: flex; align-items: center; justify-content: {justify}; height: 22px; margin: 0; padding: 0;'>"
        f"<span class='{css_class}' style='color: {color}; font-weight: {font_weight}; {font_family} margin: 0; padding: 0;'{title_attr}>{text}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

def render_row_divider() -> None:
    st.markdown(
        "<hr style='margin: 1px 0; padding: 0; border: 0; height: 1px; background-color: rgba(255, 255, 255, 0.06);'>",
        unsafe_allow_html=True,
    )