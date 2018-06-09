from django import template
from utilities.util import parse_float
register = template.Library()


@register.filter
def round(value) -> float:
    """
        >>> round(123412)
        123.412
        >>> round("123579")
        123.579
        >>> round(1234567)
        1.234567
    """
    try:
        value_int = parse_float(value, nullable=False)
        if value_int > 1000000:
            return value_int / 1000000.0
        elif value_int > 1000:
            return value_int / 1000.0
        return value_int
    except ValueError:
        return '?'


@register.filter
def units(value) -> str:
    """
        >>> units(999)
        ''
        >>> units("999999")
        'K'
        >>> units(1234567)
        'M'
    """
    try:
        value_int = parse_float(value, nullable=False)
        if value_int > 1000000.0:
            return 'M'
        elif value_int > 1000.0:
            return 'K'
        return ''
    except ValueError:
        return ''
