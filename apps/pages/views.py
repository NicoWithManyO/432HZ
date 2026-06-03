from django.contrib.contenttypes.models import ContentType
from django.db.models import Prefetch
from django.http import Http404
from django.shortcuts import redirect
from django.utils.text import Truncator
from django.views.generic import DetailView, ListView, TemplateView
from easy_thumbnails.exceptions import InvalidImageFormatError
from easy_thumbnails.files import get_thumbnailer

from apps.common.models import SlugHistory
from apps.events.models import Event, EventImage
from apps.news.models import News, NewsImage
from apps.pages.models import (
    AssoContent,
    CallToAction,
    ContactContent,
    HomeContent,
    HomeMedia,
    HomeMediaImage,
    KeyFigure,
    MentionsContent,
    Mission,
    SocialLink,
)
from apps.pages.templatetags.pages import plain_excerpt


class HomeView(TemplateView):
    """Accueil enrichi (P3.3) : hero piloté par HomeContent + à l'affiche, actus."""

    template_name = "public/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        home = HomeContent.load()
        context["home"] = home
        context["home_ctas"] = CallToAction.objects.filter(page=CallToAction.HOME)
        # Bloc média à côté de l'intro. Prefetch des images du carrousel (image comprise)
        # → la galerie est servie en requêtes constantes, sans N+1 ni .all() répétés.
        context["home_media"] = (
            HomeMedia.objects.prefetch_related(
                Prefetch("image_items", queryset=HomeMediaImage.objects.select_related("image"))
            ).first()
        )

        # Nombres affichés, configurés en gestion (repli sur les défauts du modèle si la base
        # n'a pas encore de contenu). Exposés au template pour masquer la section Actus à 0.
        events_count = (
            home.events_count if home else HomeContent._meta.get_field("events_count").default
        )
        news_count = (
            home.news_count if home else HomeContent._meta.get_field("news_count").default
        )
        context["news_count"] = news_count

        # À venir, du plus proche au plus lointain (cover préchargée → pas de N+1).
        upcoming = (
            Event.objects.published().upcoming().select_related("cover").order_by("starts_at")
        )
        # Vedette = l'event coché « à la une » le plus proche, sinon le prochain event
        # (indépendante de `events_count` : elle s'affiche toujours si elle existe).
        featured = upcoming.filter(is_featured=True).first() or upcoming.first()
        context["featured_event"] = featured
        # Grille = les events suivants, hors vedette (limitée au nombre configuré).
        context["upcoming_events"] = (
            list(upcoming.exclude(pk=featured.pk)[:events_count]) if featured else []
        )

        context["recent_news"] = list(News.objects.published()[:news_count])
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


class SlugRedirectMixin:
    """Redirige en 301 une ancienne URL de détail vers le slug courant.

    Sur 404 (slug introuvable), consulte l'historique des slugs : si l'ancien slug
    pointe vers un objet toujours publié, on redirige définitivement vers son URL.
    Une cible dépubliée garde le 404, cohérent avec l'URL courante.
    """

    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except Http404:
            target = self._resolve_old_slug(kwargs.get(self.slug_url_kwarg))
            if target is not None:
                return redirect(target.get_absolute_url(), permanent=True)
            raise

    def _resolve_old_slug(self, slug):
        model = self.get_queryset().model
        ct = ContentType.objects.get_for_model(model)
        entry = SlugHistory.objects.filter(content_type=ct, old_slug=slug).first()
        if entry is None:
            return None
        # Requête légère (sans le select_related/prefetch de la vue, inutile pour une
        # simple URL). Même filtre `published()` → pas de redirection vers un brouillon.
        return model.objects.published().filter(pk=entry.object_id).first()


class ArticleOpenGraphMixin:
    """Métadonnées Open Graph « article » communes aux détails event/actu.

    Pose `og_type=article`, titre, extrait, image cover (URL absolue, vignette `og`)
    et date de publication. Surcharge les défauts « website » du context processor SEO.
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.object
        context["og_type"] = "article"
        context["og_title"] = obj.title
        # On ne pose une description que si l'extrait porte vraiment du texte : un HTML
        # « vide » (ex. <p></p>) donnerait sinon une description vide au lieu du défaut.
        excerpt = plain_excerpt(obj.description) if obj.description else ""
        if excerpt:
            context["og_description"] = Truncator(excerpt).words(30)
        if obj.published_at:
            context["article_published_time"] = obj.published_at.isoformat()
        cover_url = self._absolute_cover_url(obj.cover)
        if cover_url:
            context["og_image_url"] = cover_url
            context["og_cover_url"] = cover_url  # réutilisé par le JSON-LD
        return context

    def _absolute_cover_url(self, cover):
        """URL absolue de la vignette Open Graph, ou None si pas de cover / vignette
        non générable (fichier disque manquant) → on garde le logo par défaut."""
        if not cover or not cover.file:
            return None
        try:
            thumb = get_thumbnailer(cover.file)["og"]
        except InvalidImageFormatError:
            return None
        return self.request.build_absolute_uri(thumb.url)


class EventDetailView(SlugRedirectMixin, ArticleOpenGraphMixin, DetailView):
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["event_jsonld"] = self._build_jsonld(self.object, context.get("og_cover_url"))
        return context

    def _build_jsonld(self, event, image_url):
        """Données structurées Schema.org Event (cf https://schema.org/Event)."""
        data = {
            "@context": "https://schema.org",
            "@type": "Event",
            "name": event.title,
            "startDate": event.starts_at.isoformat(),
            "eventStatus": "https://schema.org/EventScheduled",
            "url": self.request.build_absolute_uri(event.get_absolute_url()),
        }
        if event.ends_at:
            data["endDate"] = event.ends_at.isoformat()
        if event.location:
            data["location"] = {"@type": "Place", "name": event.location}
        if event.description:
            data["description"] = plain_excerpt(event.description)
        if image_url:
            data["image"] = [image_url]
        if event.price:
            # `price` est un texte libre (« Entrée libre », « 8 € ») : on le décrit
            # comme une offre sans prétendre à un montant numérique normalisé.
            data["offers"] = {"@type": "Offer", "description": event.price}
        return data


class ActusListView(ListView):
    """Actus publiques : actus publiées, de la plus récente à la plus ancienne."""

    template_name = "public/news_list.html"
    context_object_name = "news_list"
    paginate_by = 15

    def get_queryset(self):
        # La ligne d'actu n'affiche pas de cover → pas de select_related nécessaire ici.
        return News.objects.published()


class NewsDetailView(SlugRedirectMixin, ArticleOpenGraphMixin, DetailView):
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["asso"] = AssoContent.load()
        context["missions"] = Mission.objects.all()
        context["key_figures"] = KeyFigure.objects.all()
        context["asso_ctas"] = CallToAction.objects.filter(page=CallToAction.ASSO)
        return context


class AdhererView(TemplateView):
    template_name = "public/adherer.html"


class ContactView(TemplateView):
    template_name = "public/contact.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contact"] = ContactContent.load()
        # Seuls les liens cochés « afficher sur la page » (le footer a son propre filtre).
        context["social_links"] = SocialLink.objects.filter(show_on_page=True)
        return context


class MentionsView(TemplateView):
    """Mentions légales + confidentialité regroupées sur une seule page (contenu éditable
    en gestion ; les titres de section restent figés au template)."""

    template_name = "public/mentions_legales.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["mentions"] = MentionsContent.load()
        return context
