"""Données SEO injectées dans tous les templates publics.

On expose un petit dict explicite plutôt que `context_processors.settings` (qui
fuiterait tout l'objet settings). Les URLs absolues sont dérivées de la requête
(`build_absolute_uri`) : aucun domaine codé en dur, le host vient du déploiement.
"""

from django.templatetags.static import static

SITE_NAME = "432 Hz"

# Description par défaut (reprise du `{% block meta_description %}` de base.html) ;
# sert de repli Open Graph pour les pages qui ne surchargent pas la description.
DEFAULT_DESCRIPTION = (
    "432 Hz, association culturelle à Annecy : spectacle vivant, concerts, "
    "performances et fêtes de quartier."
)


def seo(request):
    logo_url = request.build_absolute_uri(static("brand/logo-432hz.png"))
    return {
        "SITE_NAME": SITE_NAME,
        # Canonical = URL absolue de la page, sans query string (évite les doublons).
        "canonical_url": request.build_absolute_uri(request.path),
        # Défauts Open Graph (les vues détail les surchargent dans le contexte).
        "og_type": "website",
        "og_title": SITE_NAME,
        "og_description": DEFAULT_DESCRIPTION,
        "og_image_url": logo_url,
        # JSON-LD Organization (minimal : nom + site + logo), rendu une fois site-wide.
        "organization_schema": {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": SITE_NAME,
            "url": request.build_absolute_uri("/"),
            "logo": logo_url,
        },
    }
