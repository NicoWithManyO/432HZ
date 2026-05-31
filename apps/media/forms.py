from django import forms

from .models import Image


class ImageUploadForm(forms.ModelForm):
    """Dépôt d'un média. La validation du type/poids/dimensions est portée par le champ
    modèle `Image.file` (cf validators) et s'applique donc automatiquement ici."""

    class Meta:
        model = Image
        fields = ["file", "alt", "title", "caption"]


class ImageMetaForm(forms.ModelForm):
    """Édition des métadonnées d'un média existant (le fichier ne change pas)."""

    class Meta:
        model = Image
        fields = ["alt", "title", "caption"]
