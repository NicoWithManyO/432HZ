"""Routage racine du projet 432 Hz."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("gestion/", include("apps.gestion.urls")),
    path("", include("apps.pages.urls")),
]

# En dev, Django sert les médias uploadés (en prod c'est Nginx).
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
