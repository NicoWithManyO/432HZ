from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    TemplateView,
    UpdateView,
)

from apps.accounts.permissions import ValidatedRequiredMixin
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
