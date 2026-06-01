from django.views.generic import TemplateView

from apps.pages.models import HomeContent


class HomeView(TemplateView):
    """Accueil — gabarit de fondation (P0). Le hero est piloté par HomeContent."""

    template_name = "public/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["home"] = HomeContent.load()
        return context
