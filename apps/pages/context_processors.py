"""Données de pages injectées dans tous les templates (footer site-wide).

Le footer de `base.html` liste les réseaux sociaux sur chaque page : on les expose
ici plutôt que de les coder en dur. Le QuerySet est **lazy** (non évalué tant qu'on
ne l'itère pas) → aucune requête sur les pages qui n'affichent pas le footer.
"""

from apps.pages.models import SocialLink


def footer_social_links(request):
    # Seuls les liens cochés « afficher dans le footer ».
    return {"footer_social_links": SocialLink.objects.filter(show_in_footer=True)}
