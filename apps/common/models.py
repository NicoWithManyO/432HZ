"""Briques de modèles réutilisables (clé UUID, horodatage, publication, slug).

Les apps métier (events, news, …) composent ces mixins abstraits plutôt que de
redéfinir la même mécanique. On garde les mixins atomiques : chacun fait une seule
chose et coopère via `super().save()`.
"""

import uuid

from django.db import models
from django.utils import timezone
from django.utils.text import slugify

DRAFT = "draft"
PUBLISHED = "published"
STATUS_CHOICES = [
    (DRAFT, "Brouillon"),
    (PUBLISHED, "Publié"),
]


class UUIDModel(models.Model):
    """Clé primaire UUID (pas d'ID séquentiel exposé)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """Dates de création et de dernière modification automatiques."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PublishableQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=PUBLISHED)


class PublishableModel(models.Model):
    """Bascule brouillon/publié. `published_at` est posé à la 1re publication et
    jamais réécrit ensuite (dépublier puis republier conserve la date d'origine)."""

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=DRAFT)
    published_at = models.DateTimeField(null=True, blank=True, editable=False)

    objects = PublishableQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.status == PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
            # Si l'appelant restreint les champs écrits, on y ajoute published_at
            # pour qu'il soit bien persisté lors d'une publication.
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = {*update_fields, "published_at"}
        super().save(*args, **kwargs)


class SluggedModel(models.Model):
    """Slug dérivé d'un champ source à la création, unique, stable ensuite.

    Les sous-classes surchargent `SLUG_SOURCE` si le champ n'est pas `title`.
    """

    slug = models.SlugField(max_length=200, unique=True, blank=True)

    SLUG_SOURCE = "title"

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._build_unique_slug()
        super().save(*args, **kwargs)

    def _build_unique_slug(self):
        base = slugify(getattr(self, self.SLUG_SOURCE))[:200] or "item"
        slug = base
        model = type(self)
        counter = 2
        while model.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            suffix = f"-{counter}"
            slug = f"{base[:200 - len(suffix)]}{suffix}"
            counter += 1
        return slug
