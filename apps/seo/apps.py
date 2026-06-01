from django.apps import AppConfig


class SeoConfig(AppConfig):
    # App sans modèle : sitemaps, robots.txt et métadonnées SEO (Open Graph, JSON-LD).
    name = "apps.seo"
    verbose_name = "SEO"
