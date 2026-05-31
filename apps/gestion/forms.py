import uuid

from django import forms

from apps.accounts.models import Invitation
from apps.events.models import Event
from apps.media.models import Image
from apps.news.models import News

# Format attendu/rendu par l'input HTML <input type="datetime-local">.
_DATETIME_LOCAL = "%Y-%m-%dT%H:%M"


class _DateTimeLocalInput(forms.DateTimeInput):
    input_type = "datetime-local"

    def __init__(self, attrs=None):
        super().__init__(attrs, format=_DATETIME_LOCAL)


class GalleryFormMixin:
    """Édition d'une galerie ordonnée (M2M *through* `EventImage`/`NewsImage` avec `order`).

    Django n'éditant pas un M2M *through* dans un `ModelForm`, on passe par un champ caché
    `gallery` portant les UUID d'images séparés par des virgules, dans l'ordre voulu (écrit
    par le picker JS). Le champ est injecté en `__init__` (et non en attribut de classe) pour
    rester insensible à la collecte de champs du métaclasse `ModelForm`. La synchro des lignes
    *through* est faite par `save_gallery`, appelée par la vue après la sauvegarde de l'objet."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["gallery"] = forms.CharField(required=False, widget=forms.HiddenInput)
        # Pré-remplit l'ordre courant à l'édition d'un objet existant.
        if self.instance.pk:
            ids = self.instance.gallery_items.values_list("image_id", flat=True)
            self.fields["gallery"].initial = ",".join(str(pk) for pk in ids)

    def clean_gallery(self):
        # Liste ordonnée d'UUID : ignore les ids invalides/inconnus, déduplique, garde l'ordre.
        raw = self.cleaned_data.get("gallery", "")
        ids = []
        for piece in (part.strip() for part in raw.split(",")):
            try:
                uuid.UUID(piece)
            except ValueError:
                continue
            ids.append(piece)
        by_id = {str(pk): image for pk, image in Image.objects.in_bulk(ids).items()}
        ordered, seen = [], set()
        for pk in ids:
            image = by_id.get(pk)
            if image is not None and pk not in seen:
                seen.add(pk)
                ordered.append(image)
        return ordered

    def clean(self):
        # La couverture appartient toujours à la galerie : si elle a été choisie hors galerie
        # (donnée ancienne, ou requête sans JS), on l'ajoute en fin plutôt que de la perdre.
        cleaned = super().clean()
        cover = cleaned.get("cover")
        gallery = cleaned.get("gallery")
        if cover and gallery is not None and cover not in gallery:
            gallery.append(cover)
        return cleaned

    def save_gallery(self, instance):
        # Synchro KISS : on efface puis on recrée les lignes dans l'ordre (galeries petites).
        images = self.cleaned_data.get("gallery", [])
        manager = instance.gallery
        through = manager.through
        source = manager.source_field_name  # « event » / « news »
        through.objects.filter(**{source: instance}).delete()
        through.objects.bulk_create(
            through(**{source: instance, "image": image, "order": index})
            for index, image in enumerate(images)
        )


class EventForm(GalleryFormMixin, forms.ModelForm):
    """Saisie d'un event. Le statut (brouillon/publié) se pilote via les actions
    dédiées, pas par ce formulaire."""

    class Meta:
        model = Event
        fields = [
            "title", "slug", "kind", "starts_at", "ends_at",
            "location", "price", "description", "cover",
        ]
        widgets = {
            "starts_at": _DateTimeLocalInput,
            "ends_at": _DateTimeLocalInput,
            "description": forms.Textarea(attrs={"rows": 8, "data-richtext": True}),
            # La couverture se choisit en marquant une image de la galerie (cf gallery.js).
            "cover": forms.HiddenInput,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Slug optionnel : dérivé du titre à la création s'il est laissé vide.
        self.fields["slug"].required = False
        self.fields["starts_at"].input_formats = [_DATETIME_LOCAL]
        self.fields["ends_at"].input_formats = [_DATETIME_LOCAL]


class InvitationForm(forms.ModelForm):
    """Création d'une invitation. L'e-mail est purement indicatif (le lien est
    transmis hors-ligne en v1) ; le jeton est généré par le modèle."""

    class Meta:
        model = Invitation
        fields = ["email"]


class NewsForm(GalleryFormMixin, forms.ModelForm):
    """Saisie d'une actu. Comme l'event : statut piloté hors formulaire."""

    class Meta:
        model = News
        fields = ["title", "slug", "category", "description", "cover"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 8, "data-richtext": True}),
            # La couverture se choisit en marquant une image de la galerie (cf gallery.js).
            "cover": forms.HiddenInput,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Slug optionnel : dérivé du titre à la création s'il est laissé vide.
        self.fields["slug"].required = False
