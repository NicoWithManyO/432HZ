from django.contrib import messages
from django.db import transaction
from django.db.models import Max, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)
from easy_thumbnails.files import get_thumbnailer

from apps.accounts.models import Invitation, Profile
from apps.accounts.permissions import OwnerRequiredMixin, ValidatedRequiredMixin
from apps.common.models import DRAFT, PUBLISHED
from apps.events.models import Event
from apps.gestion.forms import (
    EventForm,
    HomeContentForm,
    InvitationForm,
    NewsForm,
    TickerItemForm,
)
from apps.media.forms import ImageMetaForm, ImageUploadForm
from apps.media.models import Image
from apps.news.models import News
from apps.pages.models import HomeContent, TickerItem


class DashboardView(ValidatedRequiredMixin, TemplateView):
    """Tableau de bord : point d'entrée de la gestion + édition des contenus du site
    (hero de l'accueil, bandeau défilant)."""

    template_name = "gestion/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["ticker_items"] = TickerItem.objects.all()
        context["ticker_form"] = TickerItemForm()
        context["home_form"] = HomeContentForm(instance=HomeContent.load())
        return context


# --- Contenus du site (hero accueil + bandeau) ---


class HomeContentUpdateView(ValidatedRequiredMixin, View):
    def post(self, request):
        form = HomeContentForm(request.POST, instance=HomeContent.load())
        if form.is_valid():
            form.save()
        else:
            # PRG : on redirige, donc on signale l'échec via les messages (sinon perdu).
            messages.error(request, "Hero non enregistré :\n" + form.errors.as_text())
        return redirect("gestion:dashboard")


class TickerItemCreateView(ValidatedRequiredMixin, View):
    def post(self, request):
        form = TickerItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            # Nouvel item ajouté en fin de bandeau.
            last = TickerItem.objects.aggregate(Max("order"))["order__max"]
            item.order = last + 1 if last is not None else 0
            item.save()
        else:
            messages.error(request, "Phrase non ajoutée :\n" + form.errors.as_text())
        return redirect("gestion:dashboard")


class TickerItemDeleteView(ValidatedRequiredMixin, View):
    def post(self, request, pk):
        get_object_or_404(TickerItem, pk=pk).delete()
        return redirect("gestion:dashboard")


class TickerItemToggleHighlightView(ValidatedRequiredMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(TickerItem, pk=pk)
        item.highlighted = not item.highlighted
        item.save(update_fields=["highlighted"])
        return redirect("gestion:dashboard")


class TickerItemMoveView(ValidatedRequiredMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(TickerItem, pk=pk)
        # Échange l'ordre avec le voisin immédiat dans le sens demandé.
        direction = request.GET.get("dir")
        if direction == "up":
            neighbor = (
                TickerItem.objects.filter(order__lt=item.order).order_by("-order").first()
            )
        elif direction == "down":
            neighbor = (
                TickerItem.objects.filter(order__gt=item.order).order_by("order").first()
            )
        else:
            neighbor = None
        if neighbor is not None:
            item.order, neighbor.order = neighbor.order, item.order
            # Les deux écritures forment un tout : sinon un échec partiel laisserait
            # deux phrases au même `order`.
            with transaction.atomic():
                TickerItem.objects.bulk_update([item, neighbor], ["order"])
        return redirect("gestion:dashboard")


# --- Médiathèque ---


class MediaListView(ValidatedRequiredMixin, ListView):
    """Grille des médias, du plus récent au plus ancien."""

    model = Image
    template_name = "gestion/media/list.html"
    context_object_name = "images"
    paginate_by = 24


class ImageUploadView(ValidatedRequiredMixin, CreateView):
    model = Image
    form_class = ImageUploadForm
    template_name = "gestion/media/form.html"
    success_url = reverse_lazy("gestion:media-list")

    def form_valid(self, form):
        # Trace l'auteur du dépôt (SET_NULL si le compte disparaît).
        form.instance.uploaded_by = self.request.user
        return super().form_valid(form)


class ImageUpdateView(ValidatedRequiredMixin, UpdateView):
    model = Image
    form_class = ImageMetaForm
    template_name = "gestion/media/form.html"
    success_url = reverse_lazy("gestion:media-list")


class ImageDeleteView(ValidatedRequiredMixin, DeleteView):
    model = Image
    template_name = "gestion/media/confirm_delete.html"
    success_url = reverse_lazy("gestion:media-list")

    def get_context_data(self, **kwargs):
        # La suppression d'un média le retire de force des galeries (FK en CASCADE) :
        # on liste les events/actus impactés pour que l'éditeur supprime en connaissance.
        context = super().get_context_data(**kwargs)
        image = self.object
        context["events_using"] = Event.objects.filter(
            Q(cover=image) | Q(gallery=image)
        ).distinct()
        context["news_using"] = News.objects.filter(
            Q(cover=image) | Q(gallery=image)
        ).distinct()
        return context


class ImageQuickUploadView(ValidatedRequiredMixin, View):
    """Upload AJAX d'une image depuis un formulaire event/actu : crée le média (donc il
    rejoint la médiathèque) et renvoie son id + sa vignette, pour que le picker l'ajoute à
    la galerie sans quitter la page. Même validation serveur que l'upload classique."""

    def post(self, request):
        form = ImageUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return JsonResponse({"errors": form.errors}, status=400)
        image = form.save(commit=False)
        image.uploaded_by = request.user
        image.save()
        return JsonResponse(
            {
                "id": str(image.pk),
                "thumb": get_thumbnailer(image.file)["card"].url,
                "label": image.title or image.alt or "Sans titre",
                "caption": image.caption,
            }
        )


# --- Galerie (events + actus) ---


class GallerySaveMixin:
    """Vues Create/Update d'objets à galerie : sauve l'objet puis synchronise les lignes
    *through* via le formulaire, et expose le pool d'images de la médiathèque au picker."""

    def form_valid(self, form):
        # Objet + lignes *through* dans une même transaction : si la synchro de la galerie
        # échoue, on ne laisse pas l'objet sauvé avec une galerie à moitié reconstruite.
        with transaction.atomic():
            response = super().form_valid(form)  # sauve self.object (pk disponible ensuite)
            form.save_gallery(self.object)
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["available_images"] = Image.objects.all()
        return context


# --- Events ---


class EventListView(ValidatedRequiredMixin, ListView):
    model = Event
    template_name = "gestion/events/list.html"
    context_object_name = "events"
    paginate_by = 30

    def get_queryset(self):
        # Filtres de confort : à venir / passés / brouillons (tout par défaut).
        # upcoming()/past() = scope métier partagé avec l'agenda public (aligné sur is_past).
        events = Event.objects.all()
        return {
            "upcoming": events.upcoming(),
            "past": events.past(),
            "drafts": events.filter(status=DRAFT),
        }.get(self.request.GET.get("filter"), events)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_filter"] = self.request.GET.get("filter", "all")
        return context


class EventCreateView(GallerySaveMixin, ValidatedRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = "gestion/events/form.html"
    success_url = reverse_lazy("gestion:event-list")


class EventUpdateView(GallerySaveMixin, ValidatedRequiredMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = "gestion/events/form.html"
    success_url = reverse_lazy("gestion:event-list")


class EventDeleteView(ValidatedRequiredMixin, DeleteView):
    model = Event
    template_name = "gestion/events/confirm_delete.html"
    success_url = reverse_lazy("gestion:event-list")


class EventPublishView(ValidatedRequiredMixin, View):
    def post(self, request, pk):
        get_object_or_404(Event, pk=pk).publish()
        return redirect("gestion:event-list")


class EventUnpublishView(ValidatedRequiredMixin, View):
    def post(self, request, pk):
        get_object_or_404(Event, pk=pk).unpublish()
        return redirect("gestion:event-list")


# --- Actus ---


class NewsListView(ValidatedRequiredMixin, ListView):
    model = News
    template_name = "gestion/news/list.html"
    context_object_name = "news_list"
    paginate_by = 30

    def get_queryset(self):
        # Filtres de confort : publiées / brouillons (tout par défaut).
        news = News.objects.all()
        return {
            "published": news.filter(status=PUBLISHED),
            "drafts": news.filter(status=DRAFT),
        }.get(self.request.GET.get("filter"), news)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_filter"] = self.request.GET.get("filter", "all")
        return context


class NewsCreateView(GallerySaveMixin, ValidatedRequiredMixin, CreateView):
    model = News
    form_class = NewsForm
    template_name = "gestion/news/form.html"
    success_url = reverse_lazy("gestion:news-list")


class NewsUpdateView(GallerySaveMixin, ValidatedRequiredMixin, UpdateView):
    model = News
    form_class = NewsForm
    template_name = "gestion/news/form.html"
    success_url = reverse_lazy("gestion:news-list")


class NewsDeleteView(ValidatedRequiredMixin, DeleteView):
    model = News
    template_name = "gestion/news/confirm_delete.html"
    success_url = reverse_lazy("gestion:news-list")


class NewsPublishView(ValidatedRequiredMixin, View):
    def post(self, request, pk):
        get_object_or_404(News, pk=pk).publish()
        return redirect("gestion:news-list")


class NewsUnpublishView(ValidatedRequiredMixin, View):
    def post(self, request, pk):
        get_object_or_404(News, pk=pk).unpublish()
        return redirect("gestion:news-list")


# --- Comptes & invitations (owner) ---


class AccountListView(OwnerRequiredMixin, CreateView):
    """Hub comptes (owner) : crée des invitations et liste éditeurs + invitations."""

    model = Invitation
    form_class = InvitationForm
    template_name = "gestion/accounts/list.html"
    success_url = reverse_lazy("gestion:accounts-list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["profiles"] = Profile.objects.select_related("user").order_by(
            "role", "user__username"
        )
        context["invitations"] = Invitation.objects.all()
        return context


class InvitationRegenerateView(OwnerRequiredMixin, View):
    def post(self, request, pk):
        invitation = get_object_or_404(Invitation, pk=pk)
        # Une invitation consommée le reste : régénérer ne ferait qu'émettre un lien
        # mort (le nouveau jeton resterait `used`). On ne touche que les invitations vives.
        if not invitation.is_used:
            invitation.regenerate()
        return redirect("gestion:accounts-list")


class ProfileToggleValidationView(OwnerRequiredMixin, View):
    def post(self, request, pk):
        profile = get_object_or_404(Profile, pk=pk)
        # Les owners restent toujours validés (anti-lockout) : seuls les éditeurs basculent.
        if not profile.is_owner:
            profile.is_validated = not profile.is_validated
            profile.save(update_fields=["is_validated"])
        return redirect("gestion:accounts-list")
