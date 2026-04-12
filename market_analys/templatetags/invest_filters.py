# market_analysis/templatetags/invest_filters.py

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Dictionary dan key bo'yicha qiymat olish"""
    if dictionary and key:
        return dictionary.get(key, '#999')
    return '#999'
