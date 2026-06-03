from urllib.parse import urlsplit

from django.core.validators import MaxValueValidator
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
    # Nombre d'items affichés sur l'accueil (0 = section masquée, plafonné à 12). La vedette
    # « à la une » est indépendante de `events_count` (elle s'affiche toujours si elle existe).
    events_count = models.PositiveSmallIntegerField(default=3, validators=[MaxValueValidator(12)])
    news_count = models.PositiveSmallIntegerField(default=4, validators=[MaxValueValidator(12)])

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
    """Bouton d'appel à l'action, libre et réordonnable. Sert le hero de l'accueil, la
    page L'asso et la barre de navigation (`page`), avec deux styles : rouge plein
    (principal) ou contour (ghost)."""

    HOME = "home"
    ASSO = "asso"
    NAV = "nav"
    PAGE_CHOICES = [(HOME, "Accueil"), (ASSO, "L'asso"), (NAV, "Menu")]

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

    @property
    def is_external(self):
        """Vrai pour un lien externe (http/https) → à ouvrir dans un nouvel onglet."""
        return self.url.startswith("http")


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


class ContactContent(SingletonModel, SanitizedHTMLModel, UUIDModel):
    """Singleton : contenu textuel de la page « Contact » (structure figée au template,
    seul le contenu est éditable). L'intro est du HTML léger sanitizé."""

    kicker = models.CharField(max_length=80)
    title = models.CharField(max_length=120)
    intro = models.TextField()
    coordinates_title = models.CharField(max_length=80)
    email = models.EmailField()
    address = models.CharField(max_length=200)
    networks_title = models.CharField(max_length=80)

    RICH_TEXT_FIELDS = ("intro",)

    def __str__(self):
        return self.title


class SocialLink(UUIDModel):
    """Un lien de réseau social. Le lien est rendu tel quel dans un href : `URLField`
    n'accepte que http(s)/ftp(s) (donc pas de `javascript:`). Chaque lien s'affiche
    indépendamment sur la page Contact et/ou dans le footer (les deux par défaut)."""

    # Domaine connu → slug d'icône (cf sprite SVG local, repli « link » sinon). Les
    # sous-domaines sont couverts (ex. open.spotify.com, artiste.bandcamp.com).
    ICON_DOMAINS = {
        "instagram.com": "instagram",
        "facebook.com": "facebook",
        "fb.com": "facebook",
        "soundcloud.com": "soundcloud",
        "youtube.com": "youtube",
        "youtu.be": "youtube",
        "twitter.com": "x",
        "x.com": "x",
        "tiktok.com": "tiktok",
        "bandcamp.com": "bandcamp",
        "spotify.com": "spotify",
        "linkedin.com": "linkedin",
    }

    label = models.CharField(max_length=60)
    url = models.URLField()
    show_on_page = models.BooleanField(default=True)  # bloc « Réseaux » de la page Contact
    show_in_footer = models.BooleanField(default=True)  # colonne « Réseaux » du footer
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.label

    @property
    def icon(self):
        """Slug d'icône déduit du domaine de l'URL (repli « link » si inconnu)."""
        host = (urlsplit(self.url).hostname or "").lower()
        for domain, slug in self.ICON_DOMAINS.items():
            if host == domain or host.endswith("." + domain):
                return slug
        return "link"


class MentionsContent(SingletonModel, SanitizedHTMLModel, UUIDModel):
    """Singleton : contenu de la page « Mentions légales » (structure figée au template,
    seul le contenu est éditable). Un champ HTML léger sanitizé par section ; les titres
    de section restent codés au template."""

    kicker = models.CharField(max_length=80)
    title = models.CharField(max_length=120)
    editor_html = models.TextField()  # section « Éditeur du site »
    hosting_html = models.TextField()  # section « Hébergement »
    intellectual_property_html = models.TextField()  # section « Propriété intellectuelle »
    privacy_html = models.TextField()  # section « Confidentialité »

    RICH_TEXT_FIELDS = (
        "editor_html", "hosting_html", "intellectual_property_html", "privacy_html",
    )

    def __str__(self):
        return self.title
