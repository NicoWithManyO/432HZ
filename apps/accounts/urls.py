from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from . import views

app_name = "gestion"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("connexion/", LoginView.as_view(template_name="gestion/login.html"), name="login"),
    path("deconnexion/", LogoutView.as_view(), name="logout"),
    path("invitation/<str:token>/", views.accept_invitation, name="accept-invitation"),
]
