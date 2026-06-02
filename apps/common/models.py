"""Briques de modèles réutilisables (clé UUID, horodatage, publication, slug).

Les apps métier (events, news, …) composent ces mixins abstraits plutôt que de
redéfinir la même mécanique. On garde les mixins atomiques : chacun fait une seule
chose et coopère via `super().save()`.
"""

import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from apps.common.sanitize import clean_html

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


class SingletonModel(models.Model):
    """Modèle à ligne unique : `save()` réutilise toujours la pk de l'unique ligne
    existante (jamais de 2e ligne), `load()` renvoie cette ligne (ou None).

    Extrait du pattern de `HomeContent` pour les contenus de pages singleton (asso,
    contact, mentions). La pk UUID étant posée dès l'instanciation, on détecte un objet
    neuf via `_state.adding` et on neutralise le `force_insert` d'`objects.create`."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self._state.adding:
            existing = type(self).objects.first()
            if existing is not None:
                self.pk = existing.pk
                self._state.adding = False
                kwargs.pop("force_insert", None)
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        return cls.objects.first()


class SanitizedHTMLModel(models.Model):
    """Sanitize chaque champ riche listé dans `RICH_TEXT_FIELDS` au `save()`.

    Barrière XSS serveur (nh3), appliquée quel que soit le chemin d'écriture et
    idempotente. Généralise le `clean_html` mono-champ d'events/news à des modèles
    portant plusieurs champs HTML."""

    RICH_TEXT_FIELDS = ()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        for field in self.RICH_TEXT_FIELDS:
            # `or ""` : nh3.clean refuse None ; un champ riche vide doit rester ""
            # (cohérent avec le défaut des TextField), pas faire planter le save.
            setattr(self, field, clean_html(getattr(self, field) or ""))
        super().save(*args, **kwargs)


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

    def publish(self):
        """Passe en publié (published_at posé une seule fois, cf save())."""
        self.status = PUBLISHED
        self.save(update_fields=["status"])

    def unpublish(self):
        """Repasse en brouillon (conserve published_at d'origine)."""
        self.status = DRAFT
        self.save(update_fields=["status"])


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
        # Slug en base AVANT écriture : non-nul ⇒ mise à jour (le PK UUID, lui, est
        # déjà posé à l'instanciation et ne distingue donc pas création d'update).
        previous_slug = self._db_slug()
        # Si l'appelant restreint les champs écrits sans le slug, celui-ci n'est pas
        # persisté : on n'historise pas un changement qui n'a pas lieu en base.
        update_fields = kwargs.get("update_fields")
        slug_written = update_fields is None or "slug" in update_fields
        super().save(*args, **kwargs)
        if slug_written and previous_slug and previous_slug != self.slug:
            self._record_old_slug(previous_slug)

    def _db_slug(self):
        """Slug actuellement persisté pour cet objet, ou None s'il n'existe pas encore."""
        return type(self).objects.filter(pk=self.pk).values_list("slug", flat=True).first()

    def _record_old_slug(self, old_slug):
        """Historise un slug abandonné pour permettre une redirection 301 ultérieure."""
        ct = ContentType.objects.get_for_model(type(self))
        # L'ancien slug pointe désormais vers cet objet (écrase un mapping périmé).
        SlugHistory.objects.update_or_create(
            content_type=ct, old_slug=old_slug, defaults={"object_id": self.pk}
        )
        # Si le nouveau slug était lui-même historisé, il redevient « vivant » :
        # on retire l'entrée pour éviter une redirection en boucle.
        SlugHistory.objects.filter(content_type=ct, old_slug=self.slug).delete()

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


class SlugHistory(models.Model):
    """Anciens slugs des contenus sluggés → redirection 301 après renommage.

    Relation générique (ContentType) : un seul mécanisme pour tous les modèles
    sluggés (events, actus, …) plutôt qu'une table d'historique par modèle.
    """

    old_slug = models.SlugField(max_length=200)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey("content_type", "object_id")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Un slug ne peut désigner qu'un seul objet par type de contenu (mais peut
        # coexister entre un event et une actu). La contrainte sert aussi d'index de
        # lookup pour la redirection.
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "old_slug"], name="uniq_slug_history_ct_old_slug"
            )
        ]

    def __str__(self):
        return self.old_slug
