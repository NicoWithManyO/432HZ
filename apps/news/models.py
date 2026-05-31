from django.db import models

from apps.common.models import (
    PublishableModel,
    SluggedModel,
    TimeStampedModel,
    UUIDModel,
)


class News(UUIDModel, TimeStampedModel, SluggedModel, PublishableModel):
    title = models.CharField(max_length=200)
    category = models.CharField(
        max_length=60, blank=True, help_text="Ex. Appel, Atelier, Partenariat."
    )
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
        through="news.NewsImage",
        related_name="news",
        blank=True,
    )

    class Meta:
        verbose_name_plural = "news"
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title


class NewsImage(models.Model):
    """Table de liaison ordonnée entre une actu et les images de sa galerie."""

    news = models.ForeignKey(News, on_delete=models.CASCADE, related_name="gallery_items")
    image = models.ForeignKey("media.Image", on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["news", "image"], name="unique_news_image"),
        ]

    def __str__(self):
        return f"{self.news} · {self.image}"
