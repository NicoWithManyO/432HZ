"""Filtre de rendu JSON-LD sûr.

`django.utils.html.json_script` impose `type="application/json"` (non reconnu comme
données structurées) ; on reproduit donc son échappement anti-évasion de balise tout
en laissant le template choisir `type="application/ld+json"`.
"""

import json

from django import template
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.safestring import mark_safe

register = template.Library()

# Mêmes substitutions que json_script : empêchent `</script>` de s'échapper et neutralisent
# les séparateurs de ligne U+2028/U+2029 (invalides en JS hors chaîne).
_ESCAPES = {
    ord(">"): "\\u003E",
    ord("<"): "\\u003C",
    ord("&"): "\\u0026",
    0x2028: "\\u2028",
    0x2029: "\\u2029",
}


@register.filter(name="ld_json")
def ld_json(value):
    """Sérialise un dict en JSON sûr à injecter dans un <script type="application/ld+json">."""
    return mark_safe(json.dumps(value, cls=DjangoJSONEncoder).translate(_ESCAPES))
