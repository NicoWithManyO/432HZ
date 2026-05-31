from django import forms

from apps.accounts.models import Invitation
from apps.events.models import Event
from apps.news.models import News

from .sanitize import clean_html

# Format attendu/rendu par l'input HTML <input type="datetime-local">.
_DATETIME_LOCAL = "%Y-%m-%dT%H:%M"


class _DateTimeLocalInput(forms.DateTimeInput):
    input_type = "datetime-local"

    def __init__(self, attrs=None):
        super().__init__(attrs, format=_DATETIME_LOCAL)


class EventForm(forms.ModelForm):
    """Saisie d'un event. Le statut (brouillon/publié) se pilote via les actions
    dédiées, pas par ce formulaire. La galerie ordonnée arrive dans une étape à part."""

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
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Slug optionnel : dérivé du titre à la création s'il est laissé vide.
        self.fields["slug"].required = False
        self.fields["starts_at"].input_formats = [_DATETIME_LOCAL]
        self.fields["ends_at"].input_formats = [_DATETIME_LOCAL]

    def clean_description(self):
        # Barrière serveur : on ne stocke que du HTML léger sanitizé.
        return clean_html(self.cleaned_data["description"])


class InvitationForm(forms.ModelForm):
    """Création d'une invitation. L'e-mail est purement indicatif (le lien est
    transmis hors-ligne en v1) ; le jeton est généré par le modèle."""

    class Meta:
        model = Invitation
        fields = ["email"]


class NewsForm(forms.ModelForm):
    """Saisie d'une actu. Comme l'event : statut piloté hors formulaire,
    galerie ordonnée traitée à part."""

    class Meta:
        model = News
        fields = ["title", "slug", "category", "description", "cover"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 8, "data-richtext": True}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Slug optionnel : dérivé du titre à la création s'il est laissé vide.
        self.fields["slug"].required = False

    def clean_description(self):
        # Barrière serveur : on ne stocke que du HTML léger sanitizé.
        return clean_html(self.cleaned_data["description"])
