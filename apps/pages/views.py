from django.db.models import Prefetch
from django.views.generic import DetailView, ListView, TemplateView

from apps.events.models import Event, EventImage
from apps.news.models import News, NewsImage
from apps.pages.models import HomeContent


class HomeView(TemplateView):
    """Accueil — gabarit de fondation (P0). Le hero est piloté par HomeContent."""

    template_name = "public/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["home"] = HomeContent.load()
        return context


class AgendaListView(ListView):
    """Agenda public : events publiés, scindés à venir / passés (`?when=upcoming|past`)."""

    template_name = "public/agenda_list.html"
    context_object_name = "events"
    paginate_by = 12

    def get_queryset(self):
        # `select_related('cover')` : la carte affiche la cover → évite un N+1 sur la liste.
        events = Event.objects.published().select_related("cover")
        if self.request.GET.get("when") == "past":
            # Passés : du plus récent au plus ancien (ordre par défaut du modèle).
            return events.past()
        # À venir (défaut) : le plus proche d'abord.
        return events.upcoming().order_by("starts_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_when"] = "past" if self.request.GET.get("when") == "past" else "upcoming"
        return context


class EventDetailView(DetailView):
    """Détail d'un event publié (404 sur brouillon ou slug inconnu)."""

    # `published()` → 404 auto sur draft. select_related/prefetch : cover + galerie en
    # 2 requêtes constantes (sinon N+1 sur les images de la galerie).
    queryset = (
        Event.objects.published()
        .select_related("cover")
        .prefetch_related(
            Prefetch("gallery_items", queryset=EventImage.objects.select_related("image"))
        )
    )
    template_name = "public/agenda_detail.html"


class ActusListView(ListView):
    """Actus publiques : actus publiées, de la plus récente à la plus ancienne."""

    template_name = "public/news_list.html"
    context_object_name = "news_list"
    paginate_by = 15

    def get_queryset(self):
        # La ligne d'actu n'affiche pas de cover → pas de select_related nécessaire ici.
        return News.objects.published()


class NewsDetailView(DetailView):
    """Détail d'une actu publiée (404 sur brouillon ou slug inconnu)."""

    queryset = (
        News.objects.published()
        .select_related("cover")
        .prefetch_related(
            Prefetch("gallery_items", queryset=NewsImage.objects.select_related("image"))
        )
    )
    template_name = "public/news_detail.html"


# --- Pages fixes (P3.2) : contenu statique en template, aucune donnée dynamique ---


class AssoView(TemplateView):
    template_name = "public/asso.html"


class AdhererView(TemplateView):
    template_name = "public/adherer.html"


class ContactView(TemplateView):
    template_name = "public/contact.html"


class MentionsView(TemplateView):
    """Mentions légales + confidentialité regroupées sur une seule page."""

    template_name = "public/mentions_legales.html"
