import re
import uuid

from django import forms

from apps.accounts.models import Invitation
from apps.events.models import Event
from apps.media.models import Image
from apps.news.models import News
from apps.pages.models import (
    AssoContent,
    CallToAction,
    ContactContent,
    HomeContent,
    KeyFigure,
    MentionsContent,
    Mission,
    SocialLink,
    TickerItem,
)

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
            "title", "slug", "kind", "is_featured", "starts_at", "ends_at",
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


class TickerItemForm(forms.ModelForm):
    """Ajout d'une phrase du bandeau (l'ordre est posé par la vue)."""

    class Meta:
        model = TickerItem
        fields = ["text", "highlighted"]


class HomeContentForm(forms.ModelForm):
    """Édition des trois textes du hero de l'accueil."""

    class Meta:
        model = HomeContent
        fields = ["subtitle", "punchline", "intro"]
        help_texts = {
            "punchline": "Entourez des mots de [r]…[/r] pour les afficher en rouge.",
        }
        widgets = {
            "intro": forms.Textarea(attrs={"rows": 3}),
        }


class HomeDisplayForm(forms.ModelForm):
    """Réglage de l'affichage de l'accueil : combien d'events et d'actus on montre
    (0 = section masquée, plafond posé par les validateurs du modèle)."""

    class Meta:
        model = HomeContent
        fields = ["events_count", "news_count"]
        labels = {
            "events_count": "Nombre d'events à venir",
            "news_count": "Nombre d'actus",
        }
        help_texts = {
            "events_count": "0 masque la grille des events suivants (la une reste affichée).",
            "news_count": "0 masque la section Actus.",
        }


class AssoContentForm(forms.ModelForm):
    """Édition des textes de la page L'asso (manifeste en HTML léger via l'éditeur riche)."""

    class Meta:
        model = AssoContent
        fields = [
            "kicker", "title", "manifesto", "missions_kicker", "missions_title",
        ]
        widgets = {
            "manifesto": forms.Textarea(attrs={"rows": 6, "data-richtext": True}),
        }


class CallToActionForm(forms.ModelForm):
    """Ajout d'un bouton (la page et l'ordre sont posés par la vue)."""

    class Meta:
        model = CallToAction
        fields = ["label", "url", "variant"]
        help_texts = {
            "url": "Chemin interne (ex. /adherer/) ou URL externe.",
        }

    def clean_url(self):
        # Le lien est rendu tel quel dans un href : on bloque les schémas dangereux
        # (javascript:, data:…) qui seraient une XSS au clic. On autorise un chemin
        # interne (/…), une ancre (#…) ou un schéma sûr.
        url = self.cleaned_data["url"].strip()
        if url.startswith(("/", "#")) or re.match(r"^(https?|mailto|tel):", url, re.IGNORECASE):
            return url
        raise forms.ValidationError(
            "Utilisez un chemin interne (/…), une ancre (#…) ou une URL http(s)/mailto/tel."
        )


class MissionForm(forms.ModelForm):
    """Ajout d'une mission (l'ordre est posé par la vue)."""

    class Meta:
        model = Mission
        fields = ["title", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class KeyFigureForm(forms.ModelForm):
    """Ajout d'un chiffre-clé (l'ordre est posé par la vue)."""

    class Meta:
        model = KeyFigure
        fields = ["text"]


class ContactContentForm(forms.ModelForm):
    """Édition des textes et coordonnées de la page Contact (intro en HTML léger via
    l'éditeur riche)."""

    class Meta:
        model = ContactContent
        fields = [
            "kicker", "title", "intro", "coordinates_title", "email", "address",
            "networks_title",
        ]
        widgets = {
            "intro": forms.Textarea(attrs={"rows": 4, "data-richtext": True}),
        }


class SocialLinkForm(forms.ModelForm):
    """Ajout d'un lien de réseau social (l'ordre est posé par la vue)."""

    # `assume_scheme="https"` : schéma par défaut d'une URL sans protocole (et défaut
    # explicite de Django 6.0 → silence le warning de transition).
    url = forms.URLField(assume_scheme="https", max_length=200)

    class Meta:
        model = SocialLink
        fields = ["label", "url"]


class MentionsContentForm(forms.ModelForm):
    """Édition des textes de la page Mentions légales (une section en HTML léger par
    champ via l'éditeur riche ; les titres de section restent figés au template)."""

    class Meta:
        model = MentionsContent
        fields = [
            "kicker", "title", "editor_html", "hosting_html",
            "intellectual_property_html", "privacy_html",
        ]
        labels = {
            "editor_html": "Éditeur du site",
            "hosting_html": "Hébergement",
            "intellectual_property_html": "Propriété intellectuelle",
            "privacy_html": "Confidentialité",
        }
        widgets = {
            "editor_html": forms.Textarea(attrs={"rows": 5, "data-richtext": True}),
            "hosting_html": forms.Textarea(attrs={"rows": 3, "data-richtext": True}),
            "intellectual_property_html": forms.Textarea(
                attrs={"rows": 4, "data-richtext": True}
            ),
            "privacy_html": forms.Textarea(attrs={"rows": 5, "data-richtext": True}),
        }
