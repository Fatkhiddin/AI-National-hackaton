from django import template

register = template.Library()


@register.filter
def format_duration(seconds):
    """Sekundlarni mm:ss formatiga o'girish"""
    if not seconds:
        return "0:00"
    
    mins = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{mins}:{secs:02d}"
