"""Tags/filtres des contenus éditables du site (bandeau + hero)."""

import html

from django import template
from django.utils.html import strip_tags

from apps.pages.models import TickerItem
from apps.pages.punchline import render_punchline

register = template.Library()


@register.filter(name="punchline")
def punchline(text):
    """Rend la balise légère `[r]…[/r]` du hero (cf punchline.py)."""
    return render_punchline(text)


@register.filter(name="plain_excerpt")
def plain_excerpt(value):
    """Texte brut depuis une description HTML sanitizée (cartes/extraits).

    On retire les balises PUIS on décode les entités (`&amp;`→`&`) : sinon l'auto-échappement
    Django les ré-échapperait (« &amp; » affiché). Le résultat est ré-échappé normalement."""
    return html.unescape(strip_tags(value))


@register.inclusion_tag("public/_ticker.html")
def ticker_bar():
    """Bandeau défilant site-wide. Une seule requête, rendue côté serveur ; le bloc
    est neutralisé en gestion (base_gestion.html) donc cette requête n'y a pas lieu."""
    return {"items": TickerItem.objects.all()}
