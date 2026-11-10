from django import template

register = template.Library()

@register.filter(name='class_name')
def class_name(obj):
    """Devuelve el nombre de la clase de un objeto"""
    if obj is None:
        return ''
    return obj.__class__.__name__

@register.filter(name='split')
def split_filter(value, delimiter=','):
    """Divide un string por un delimitador"""
    if not value:
        return []
    return value.split(delimiter)
