from django.db import models
from django.utils import timezone

from apps.common.models import (
    PublishableModel,
    SluggedModel,
    TimeStampedModel,
    UUIDModel,
)
from apps.common.sanitize import clean_html


class Event(UUIDModel, TimeStampedModel, SluggedModel, PublishableModel):
    title = models.CharField(max_length=200)
    kind = models.CharField(max_length=40, blank=True, help_text="Concert, performance, spectacle…")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=200, blank=True)
    price = models.CharField(max_length=80, blank=True, help_text="Ex. « Entrée libre », « 8 € ».")
    description = models.TextField(blank=True, help_text="HTML léger sanitizé (nh3).")
    cover = models.ForeignKey(
        "media.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    gallery = models.ManyToManyField(
        "media.Image",
        through="events.EventImage",
        related_name="events",
        blank=True,
    )

    class Meta:
        ordering = ["-starts_at"]

    def save(self, *args, **kwargs):
        # Barrière XSS au niveau modèle : la description est sanitizée quel que soit
        # le chemin d'écriture (form, shell, import futur). Idempotent.
        self.description = clean_html(self.description)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def is_past(self):
        # Un event est passé une fois sa fin écoulée (ou son début, si pas de fin).
        reference = self.ends_at or self.starts_at
        return reference < timezone.now()


class EventImage(models.Model):
    """Table de liaison ordonnée entre un event et les images de sa galerie."""

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="gallery_items")
    image = models.ForeignKey("media.Image", on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["event", "image"], name="unique_event_image"),
        ]

    def __str__(self):
        return f"{self.event} · {self.image}"
