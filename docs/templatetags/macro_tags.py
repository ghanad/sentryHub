from django import template
from django.utils.safestring import mark_safe
from ..models import Macro

register = template.Library()

@register.filter
def apply_macros(text):
    """Replace [[KEY]] tokens with values from Macro objects."""
    if not text:
        return ""
    macros = Macro.objects.all()
    for macro in macros:
        text = text.replace(f"[[{macro.key}]]", macro.value)
    return mark_safe(text)
