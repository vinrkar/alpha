from datetime import datetime
from typing import Mapping, Optional


def filter_closes_by_date_range(
        closes_dict: Mapping[str, float],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
) -> dict[str, float]:
    """Filters a {date_str: price} mapping inclusively to [start_date, end_date] when provided."""
    if not closes_dict:
        return {}
    if not start_date and not end_date:
        return dict(closes_dict)

    filtered: dict[str, float] = {}
    for date_str, price in closes_dict.items():
        clean_date = str(date_str).split(" ")[0]
        if start_date and clean_date < start_date:
            continue
        if end_date and clean_date > end_date:
            continue
        filtered[clean_date] = price
    return filtered


def format_daywise_price_table(
        closes_dict: Mapping[str, float],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
) -> str:
    """Formats historical closing prices into a clean Markdown table."""
    scoped_closes = filter_closes_by_date_range(closes_dict, start_date, end_date)
    if not scoped_closes:
        return ""

    lines = [
        "| Date | Closing Price |",
        "|---|---|",
    ]
    items = list(scoped_closes.items())
    display_items = items[:5] + [("...", None)] + items[-10:] if len(items) > 15 else items

    for date_str, price in display_items:
        if date_str == "...":
            lines.append("| ... | ... |")
            continue

        clean_date = str(date_str).split(" ")[0]
        try:
            formatted_date = datetime.strptime(clean_date, "%Y-%m-%d").strftime("%b %d, %Y")
        except ValueError:
            formatted_date = clean_date

        lines.append(f"| {formatted_date} | ${float(price):.2f} |")

    return "\n".join(lines)