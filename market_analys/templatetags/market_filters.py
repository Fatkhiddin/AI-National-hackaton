from django import template
from datetime import datetime

register = template.Library()


@register.filter
def format_number(value):
    """Raqamni 1 000 000 formatda ko'rsatish (3 xonadan bo'sh joy bilan ajratish)"""
    if value is None:
        return "—"
    try:
        num = float(value)
        if num == int(num):
            return f"{int(num):,}".replace(",", " ")
        return f"{num:,.2f}".replace(",", " ")
    except (ValueError, TypeError):
        return value


@register.filter
def format_price(value):
    """Narxni $55 500 formatda ko'rsatish"""
    if value is None:
        return "—"
    try:
        num = float(value)
        if num == int(num):
            return f"${int(num):,}".replace(",", " ")
        return f"${num:,.2f}".replace(",", " ")
    except (ValueError, TypeError):
        return value


@register.filter
def list_names(value):
    """[{"id": 1, "name": "Bor"}] → "Bor" ga aylantirish"""
    if not value or not isinstance(value, list):
        return "—"
    names = [item.get('name', '') for item in value if isinstance(item, dict) and item.get('name')]
    return ", ".join(names) if names else "—"


@register.filter
def dict_name(value):
    """{"id": 1, "name": "Turar"} → "Turar" """
    if not value:
        return "—"
    if isinstance(value, dict):
        return value.get('name', '—')
    return value


@register.filter
def format_datetime(value):
    """'2026-04-11T17:56:31.289350+05:00' → '11.04.2026 17:56'"""
    if not value:
        return "—"
    try:
        dt = datetime.fromisoformat(str(value))
        return dt.strftime('%d.%m.%Y %H:%M')
    except (ValueError, TypeError):
        return value
