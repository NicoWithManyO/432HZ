"""Routage racine du projet 432 Hz."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from apps.seo.sitemaps import sitemaps
from apps.seo.views import robots_txt

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("gestion/", include("apps.gestion.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("robots.txt", robots_txt, name="robots"),
    path("", include("apps.pages.urls")),
]

# En dev, Django sert les médias uploadés (en prod c'est Nginx).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
