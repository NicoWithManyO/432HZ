from django import forms

from .models import Image
from .validators import validate_image_file


class ImageUploadForm(forms.ModelForm):
    """Dépôt d'un média : le fichier est validé sur son type réel (cf validators)."""

    class Meta:
        model = Image
        fields = ["file", "alt", "title", "caption"]

    def clean_file(self):
        file = self.cleaned_data["file"]
        validate_image_file(file)
        return file


class ImageMetaForm(forms.ModelForm):
    """Édition des métadonnées d'un média existant (le fichier ne change pas)."""

    class Meta:
        model = Image
        fields = ["alt", "title", "caption"]
