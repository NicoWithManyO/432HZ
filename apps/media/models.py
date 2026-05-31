import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import UUIDModel


def image_upload_to(instance, filename):
    """Range les médias par mois et randomise le nom (anti-collision, pas de fuite
    du nom d'origine). Le type réel est validé en amont (cf media.validators)."""
    ext = Path(filename).suffix.lower()
    return f"images/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{ext}"


class Image(UUIDModel):
    """Image de la médiathèque, réutilisable comme cover ou en galerie."""

    file = models.ImageField(upload_to=image_upload_to)
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

    def __str__(self):
        return self.title or self.alt or str(self.id)
