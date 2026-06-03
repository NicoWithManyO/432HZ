import io
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone
from PIL import Image as PILImage
from PIL import ImageOps

from apps.common.models import UUIDModel

from .validators import validate_image_file

# Qualité de ré-encodage pour les formats avec perte (compromis poids/qualité).
_REENCODE_QUALITY = 88


def image_upload_to(instance, filename):
    """Range les médias par mois et randomise le nom (anti-collision, pas de fuite
    du nom d'origine). Le type réel est validé en amont (cf media.validators)."""
    ext = Path(filename).suffix.lower()
    return f"images/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{ext}"


def _reencode(fieldfile):
    """Ré-encode un upload via Pillow : régénère intégralement les octets (neutralise
    un polyglotte, ex. octets greffés après l'image) et n'écrit aucune métadonnée EXIF
    (le dict `info` n'est pas recopié). Le format d'origine est conservé."""
    fieldfile.seek(0)
    with PILImage.open(fieldfile) as img:
        image_format = img.format  # capturé avant transpose (qui renvoie une image sans .format)
        # Redresse selon l'orientation EXIF puis la retire : sans ça, strip EXIF +
        # pixels non transposés afficherait les photos de téléphone de travers.
        img = ImageOps.exif_transpose(img)
        save_kwargs = {"format": image_format}
        if image_format in ("JPEG", "WEBP"):
            save_kwargs["quality"] = _REENCODE_QUALITY
        elif image_format == "PNG":
            save_kwargs["optimize"] = True
        buffer = io.BytesIO()
        img.save(buffer, **save_kwargs)
    return ContentFile(buffer.getvalue(), name=fieldfile.name)


class Image(UUIDModel):
    """Image de la médiathèque, réutilisable comme cover ou en galerie."""

    file = models.ImageField(upload_to=image_upload_to, validators=[validate_image_file])
    alt = models.CharField(max_length=200, blank=True)
    title = models.CharField(max_length=200, blank=True, help_text="Titre interne (médiathèque).")
    caption = models.CharField(
        max_length=255, blank=True, help_text="Légende affichée avec l'image (galerie, public)."
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="images",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        # Ré-encodage des uploads frais uniquement (`_committed` reste False tant que
        # le fichier n'est pas en stockage) : retire l'EXIF et neutralise les polyglottes.
        # Une simple édition de métadonnées (fichier déjà stocké) ne le ré-encode pas.
        if self.file and not self.file._committed:
            self.file = _reencode(self.file)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title or self.alt or str(self.id)
