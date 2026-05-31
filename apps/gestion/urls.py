"""Routage de l'interface de gestion conviviale (`/gestion/`).

Porte le namespace `gestion`. L'authentification (login/logout/invitation) reste
servie par des vues d'`apps.accounts` (domaine comptes), simplement câblée ici.
"""

from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from apps.accounts.views import accept_invitation

from . import views

app_name = "gestion"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("connexion/", LoginView.as_view(template_name="gestion/login.html"), name="login"),
    path("deconnexion/", LogoutView.as_view(), name="logout"),
    path("invitation/<str:token>/", accept_invitation, name="accept-invitation"),
    # Médiathèque
    path("medias/", views.MediaListView.as_view(), name="media-list"),
    path("medias/ajouter/", views.ImageUploadView.as_view(), name="media-upload"),
    path("medias/<uuid:pk>/modifier/", views.ImageUpdateView.as_view(), name="media-update"),
    path("medias/<uuid:pk>/supprimer/", views.ImageDeleteView.as_view(), name="media-delete"),
    # Events
    path("events/", views.EventListView.as_view(), name="event-list"),
    path("events/ajouter/", views.EventCreateView.as_view(), name="event-create"),
    path("events/<uuid:pk>/modifier/", views.EventUpdateView.as_view(), name="event-update"),
    path("events/<uuid:pk>/supprimer/", views.EventDeleteView.as_view(), name="event-delete"),
    path("events/<uuid:pk>/publier/", views.EventPublishView.as_view(), name="event-publish"),
    path("events/<uuid:pk>/depublier/", views.EventUnpublishView.as_view(), name="event-unpublish"),
]
