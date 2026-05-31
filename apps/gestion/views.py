from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)

from apps.accounts.permissions import ValidatedRequiredMixin
from apps.common.models import DRAFT
from apps.events.models import Event
from apps.gestion.forms import EventForm
from apps.media.forms import ImageMetaForm, ImageUploadForm
from apps.media.models import Image


class DashboardView(ValidatedRequiredMixin, TemplateView):
    """Tableau de bord : point d'entrée de la gestion conviviale."""

    template_name = "gestion/dashboard.html"


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


# --- Events ---


class EventListView(ValidatedRequiredMixin, ListView):
    model = Event
    template_name = "gestion/events/list.html"
    context_object_name = "events"
    paginate_by = 30

    def get_queryset(self):
        # Filtres de confort : à venir / passés / brouillons (tout par défaut).
        events = Event.objects.all()
        now = timezone.now()
        return {
            "upcoming": events.filter(starts_at__gte=now),
            "past": events.filter(starts_at__lt=now),
            "drafts": events.filter(status=DRAFT),
        }.get(self.request.GET.get("filter"), events)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_filter"] = self.request.GET.get("filter", "all")
        return context


class EventCreateView(ValidatedRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = "gestion/events/form.html"
    success_url = reverse_lazy("gestion:event-list")


class EventUpdateView(ValidatedRequiredMixin, UpdateView):
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
