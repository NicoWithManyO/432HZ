from django.views.generic import TemplateView


class HomeView(TemplateView):
    """Accueil — gabarit de fondation (P0). Le contenu réel arrive en P3."""

    template_name = "public/home.html"
