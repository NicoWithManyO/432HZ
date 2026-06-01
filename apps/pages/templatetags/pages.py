"""Tags/filtres des contenus éditables du site (bandeau + hero)."""

from django import template

from apps.pages.models import TickerItem
from apps.pages.punchline import render_punchline

register = template.Library()


@register.filter(name="punchline")
def punchline(text):
    """Rend la balise légère `[r]…[/r]` du hero (cf punchline.py)."""
    return render_punchline(text)


@register.inclusion_tag("public/_ticker.html")
def ticker_bar():
    """Bandeau défilant site-wide. Une seule requête, rendue côté serveur ; le bloc
    est neutralisé en gestion (base_gestion.html) donc cette requête n'y a pas lieu."""
    return {"items": TickerItem.objects.all()}
