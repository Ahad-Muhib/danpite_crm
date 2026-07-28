from django import template
from core.models import CurrencySettings, CURRENCY_SYMBOLS

register = template.Library()


@register.filter(name='currency')
def currency(value):
    try:
        settings = CurrencySettings.load()
        symbol = settings.symbol
    except Exception:
        symbol = '$'
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
        return '$'


@register.simple_tag
def get_currency_code():
    try:
        settings = CurrencySettings.load()
        return settings.currency_code
    except Exception:
        return 'USD'
