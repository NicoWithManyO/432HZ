"""Données de pages injectées dans tous les templates (header + footer site-wide).

`base.html` affiche sur chaque page les réseaux sociaux (footer) et les boutons d'action
de la barre de navigation (header) : on les expose ici plutôt que de les coder en dur.
Les QuerySets sont **lazy** (non évalués tant qu'on ne les itère pas).
"""

from apps.pages.models import CallToAction, SocialLink


def footer_social_links(request):
    # Seuls les liens cochés « afficher dans le footer ».
    return {"footer_social_links": SocialLink.objects.filter(show_in_footer=True)}


def nav_ctas(request):
    # Boutons d'action de la barre de navigation (après les liens fixes), réordonnables.
    return {"nav_ctas": CallToAction.objects.filter(page=CallToAction.NAV)}
