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
    # Contenus du site (hero accueil + bandeau défilant)
    path("accueil/textes/", views.HomeContentUpdateView.as_view(), name="home-content-update"),
    path(
        "accueil/affichage/",
        views.HomeDisplayUpdateView.as_view(),
        name="home-display-update",
    ),
    path("bandeau/ajouter/", views.TickerItemCreateView.as_view(), name="ticker-create"),
    path(
        "bandeau/<uuid:pk>/supprimer/",
        views.TickerItemDeleteView.as_view(),
        name="ticker-delete",
    ),
    path(
        "bandeau/<uuid:pk>/mise-en-avant/",
        views.TickerItemToggleHighlightView.as_view(),
        name="ticker-toggle-highlight",
    ),
    path("bandeau/<uuid:pk>/deplacer/", views.TickerItemMoveView.as_view(), name="ticker-move"),
    # Contenu page L'asso (textes) + listes ordonnées génériques (missions, chiffres, …)
    path("asso/textes/", views.AssoContentUpdateView.as_view(), name="asso-content-update"),
    # Contenu page Contact (textes & coordonnées) — réseaux via les listes génériques
    path(
        "contact/textes/",
        views.ContactContentUpdateView.as_view(),
        name="contact-content-update",
    ),
    path(
        "listes/<str:key>/ajouter/",
        views.OrderedListCreateView.as_view(),
        name="list-create",
    ),
    path(
        "listes/<str:key>/<uuid:pk>/modifier/",
        views.OrderedListUpdateView.as_view(),
        name="list-update",
    ),
    path(
        "listes/<str:key>/<uuid:pk>/supprimer/",
        views.OrderedListDeleteView.as_view(),
        name="list-delete",
    ),
    path(
        "listes/<str:key>/<uuid:pk>/deplacer/",
        views.OrderedListMoveView.as_view(),
        name="list-move",
    ),
    path("connexion/", LoginView.as_view(template_name="gestion/login.html"), name="login"),
    path("deconnexion/", LogoutView.as_view(), name="logout"),
    path("invitation/<str:token>/", accept_invitation, name="accept-invitation"),
    # Médiathèque
    path("medias/", views.MediaListView.as_view(), name="media-list"),
    path("medias/ajouter/", views.ImageUploadView.as_view(), name="media-upload"),
    path("medias/televerser/", views.ImageQuickUploadView.as_view(), name="media-quick-upload"),
    path("medias/<uuid:pk>/modifier/", views.ImageUpdateView.as_view(), name="media-update"),
    path("medias/<uuid:pk>/supprimer/", views.ImageDeleteView.as_view(), name="media-delete"),
    # Events
    path("events/", views.EventListView.as_view(), name="event-list"),
    path("events/ajouter/", views.EventCreateView.as_view(), name="event-create"),
    path("events/<uuid:pk>/modifier/", views.EventUpdateView.as_view(), name="event-update"),
    path("events/<uuid:pk>/supprimer/", views.EventDeleteView.as_view(), name="event-delete"),
    path("events/<uuid:pk>/publier/", views.EventPublishView.as_view(), name="event-publish"),
    path("events/<uuid:pk>/depublier/", views.EventUnpublishView.as_view(), name="event-unpublish"),
    # Actus
    path("actus/", views.NewsListView.as_view(), name="news-list"),
    path("actus/ajouter/", views.NewsCreateView.as_view(), name="news-create"),
    path("actus/<uuid:pk>/modifier/", views.NewsUpdateView.as_view(), name="news-update"),
    path("actus/<uuid:pk>/supprimer/", views.NewsDeleteView.as_view(), name="news-delete"),
    path("actus/<uuid:pk>/publier/", views.NewsPublishView.as_view(), name="news-publish"),
    path("actus/<uuid:pk>/depublier/", views.NewsUnpublishView.as_view(), name="news-unpublish"),
    # Comptes & invitations (owner)
    path("comptes/", views.AccountListView.as_view(), name="accounts-list"),
    path(
        "comptes/invitations/<uuid:pk>/regenerer/",
        views.InvitationRegenerateView.as_view(),
        name="invitation-regenerate",
    ),
    path(
        "comptes/profils/<int:pk>/validation/",
        views.ProfileToggleValidationView.as_view(),
        name="profile-toggle-validation",
    ),
]
