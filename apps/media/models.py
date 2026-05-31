from django.conf import settings
from django.db import models

from apps.common.models import UUIDModel


class Image(UUIDModel):
    """Image de la médiathèque, réutilisable comme cover ou en galerie."""

    file = models.ImageField(upload_to="images/%Y/%m/")
    alt = models.CharField(max_length=200, blank=True)
    title = models.CharField(max_length=200, blank=True, help_text="Titre interne (médiathèque).")
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
