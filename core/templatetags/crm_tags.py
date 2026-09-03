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
    import re
    # Check if empty HTML (e.g. <p><br></p>, <p></p>, <p>&nbsp;</p>, etc.)
    text_content = re.sub(r'<[^>]*>', '', val).replace('&nbsp;', ' ').replace('&#160;', ' ').strip()
    if not text_content and not any(tag in val.lower() for tag in ('<img', '<hr', '<table', '<iframe')):
        return ''
    from django.utils.safestring import mark_safe
    from django.template.defaultfilters import linebreaksbr
    if any(tag in val.lower() for tag in ('<p>', '<ul>', '<ol>', '<br>', '<br/>', '<br />', '<div>', '<strong>', '<em>', '<li>', '<span>', '<h1', '<h2', '<h3', '<h4', '<h5', '<h6', '<table>')):
        return mark_safe(val)
    return mark_safe(linebreaksbr(val))



@register.filter(name='normalize_pricing_table')
def normalize_pricing_table(pricing_plans):
    """
    Normalizes pricing_plans JSON data (dict with columns/rows or legacy list)
    into a standardized dict: {'columns': [...], 'rows': [{'is_selected': bool, 'cells': [...]}]}
    """
    if not pricing_plans:
        return None
    if isinstance(pricing_plans, dict):
        cols = pricing_plans.get('columns', [])
        raw_rows = pricing_plans.get('rows', [])
        valid_rows = []
        for r in raw_rows:
            cells = r.get('cells', [])
            if any(str(c).strip() for c in cells):
                valid_rows.append({
                    'is_selected': bool(r.get('is_selected', False)),
                    'cells': cells
                })
        if cols and valid_rows:
            return {'columns': cols, 'rows': valid_rows}
        return None
    elif isinstance(pricing_plans, list):
        cols = ['Package', 'License', 'Price', 'Delivery Time']
        valid_rows = []
        for p in pricing_plans:
            pkg = p.get('package', '')
            lic = p.get('license', '')
            prc = p.get('price', '')
            dt = p.get('delivery_time', '')
            if pkg or prc:
                valid_rows.append({
                    'is_selected': bool(p.get('is_selected', False)),
                    'cells': [pkg, lic, prc, dt]
                })
        if valid_rows:
            return {'columns': cols, 'rows': valid_rows}
        return None
    return None

