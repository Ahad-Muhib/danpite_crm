from django import template
from core.models import CurrencySettings, CURRENCY_SYMBOLS

register = template.Library()


@register.filter(name='currency')
def currency(value):
    try:
        settings = CurrencySettings.load()
        symbol = settings.symbol
    except Exception:
        symbol = '৳'
    try:
        return f"{symbol}{value:,.2f}"
    except (ValueError, TypeError):
        return f"{symbol}0.00"


@register.simple_tag
def get_currency_symbol():
    try:
        settings = CurrencySettings.load()
        return settings.symbol
    except Exception:
        return '৳'


@register.simple_tag
def get_currency_code():
    try:
        settings = CurrencySettings.load()
        return settings.currency_code
    except Exception:
        return 'BDT'


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    query = context['request'].GET.copy()
    for k, v in kwargs.items():
        query[k] = v
    return query.urlencode()


@register.filter
def next_order(order):
    return 'asc' if order == 'desc' else 'desc'


@register.filter
def signed(value):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return value
    sign = '+' if v > 0 else ''
    return f"{sign}{v:.1f}"


@register.filter(name='render_rich_text')
def render_rich_text(value):
    if not value:
        return ''
    val = str(value).strip()
    from django.utils.safestring import mark_safe
    from django.template.defaultfilters import linebreaksbr
    if any(tag in val for tag in ('<p>', '<ul>', '<ol>', '<br>', '<div>', '<strong>', '<em>', '<li>')):
        return mark_safe(val)
    return mark_safe(linebreaksbr(val))

