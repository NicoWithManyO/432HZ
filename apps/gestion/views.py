from django.views.generic import TemplateView

from apps.accounts.permissions import ValidatedRequiredMixin


class DashboardView(ValidatedRequiredMixin, TemplateView):
    """Tableau de bord : point d'entrée de la gestion conviviale."""

    template_name = "gestion/dashboard.html"
