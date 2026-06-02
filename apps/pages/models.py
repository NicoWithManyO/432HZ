from django.db import models

from apps.common.models import SanitizedHTMLModel, SingletonModel, UUIDModel


class TickerItem(UUIDModel):
    """Une phrase du bandeau défilant. `highlighted` ⇒ rendu en rouge."""

    text = models.CharField(max_length=60)
    highlighted = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "text"]

    def __str__(self):
        return self.text


class HomeContent(UUIDModel):
    """Singleton : les trois textes du hero de l'accueil (une seule ligne, garantie
    par la migration de seed et par `save()`)."""

    subtitle = models.CharField(max_length=120)
    punchline = models.CharField(max_length=200)  # balise légère [r]…[/r] pour le rouge
    intro = models.TextField()

    def __str__(self):
        return self.subtitle

    def save(self, *args, **kwargs):
        # Singleton : jamais de 2e ligne. La pk est posée par UUIDModel dès l'instanciation,
        # on détecte donc un objet neuf via `_state.adding`. S'il existe déjà une ligne, on
        # réutilise sa pk → UPDATE de l'unique ligne (on neutralise le force_insert
        # d'objects.create).
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


class AssoContent(SingletonModel, SanitizedHTMLModel, UUIDModel):
    """Singleton : contenu textuel de la page « L'asso » (structure figée au template,
    seul le contenu est éditable). Le manifeste est du HTML léger sanitizé."""

    kicker = models.CharField(max_length=80)
    title = models.CharField(max_length=120)
    manifesto = models.TextField()
    missions_kicker = models.CharField(max_length=80)
    missions_title = models.CharField(max_length=120)

    RICH_TEXT_FIELDS = ("manifesto",)

    def __str__(self):
        return self.title


class CallToAction(UUIDModel):
    """Bouton d'appel à l'action, libre et réordonnable. Sert le hero de l'accueil et la
    page L'asso (`page`), avec deux styles : rouge plein (principal) ou contour (ghost)."""

    HOME = "home"
    ASSO = "asso"
    PAGE_CHOICES = [(HOME, "Accueil"), (ASSO, "L'asso")]

    RED = "red"
    GHOST = "ghost"
    VARIANT_CHOICES = [(RED, "Rouge (principal)"), (GHOST, "Contour (secondaire)")]

    page = models.CharField(max_length=20, choices=PAGE_CHOICES)
    label = models.CharField(max_length=60)
    url = models.CharField(max_length=200)  # chemin interne (/adherer/) ou URL externe
    variant = models.CharField(max_length=10, choices=VARIANT_CHOICES, default=RED)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.label


class Mission(UUIDModel):
    """Une mission de l'asso (carte numérotée). Le numéro 01/02… est dérivé de l'ordre
    au template, pas stocké."""

    title = models.CharField(max_length=120)
    description = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title


class KeyFigure(UUIDModel):
    """Un chiffre-clé (badge) affiché sur la page L'asso."""

    text = models.CharField(max_length=60)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.text
