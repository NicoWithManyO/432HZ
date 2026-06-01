from django.db import models

from apps.common.models import UUIDModel


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
