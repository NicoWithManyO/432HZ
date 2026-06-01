"""Sitemaps publics. La vue `sitemap` de Django bâtit les URLs absolues à partir
du host de la requête (fallback `RequestSite` puisque `django.contrib.sites` n'est
pas installé) — aucun domaine à configurer ici."""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.events.models import Event
from apps.news.models import News


class StaticViewSitemap(Sitemap):
    """Pages fixes (accueil, listes, pages éditoriales) référencées par leur nom d'URL."""

    changefreq = "weekly"

    def items(self):
        return ["home", "agenda", "actus", "asso", "adherer", "contact", "mentions"]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return 1.0 if item == "home" else 0.6


class EventSitemap(Sitemap):
    """Events publiés. Aucune relation suivie → une seule requête (pas de N+1)."""

    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Event.objects.published()

    def lastmod(self, obj):
        return obj.updated_at


class NewsSitemap(Sitemap):
    """Actus publiées."""

    changefreq = "weekly"
    priority = 0.5

    def items(self):
        return News.objects.published()

    def lastmod(self, obj):
        return obj.updated_at


sitemaps = {
    "static": StaticViewSitemap,
    "events": EventSitemap,
    "news": NewsSitemap,
}
