import re
import uuid
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models
from django.utils import timezone

from apps.common.models import SanitizedHTMLModel, SingletonModel, UUIDModel
from apps.media.validators import validate_video_file


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

    AUTO = "auto"
    BLANK = "blank"
    SELF = "self"
    TARGET_CHOICES = [
        (AUTO, "Automatique (lien externe = nouvel onglet)"),
        (BLANK, "Nouvel onglet"),
        (SELF, "Même onglet"),
    ]

    page = models.CharField(max_length=20, choices=PAGE_CHOICES)
    label = models.CharField(max_length=60)
    url = models.CharField(max_length=200)  # chemin interne (/adherer/) ou URL externe
    variant = models.CharField(max_length=10, choices=VARIANT_CHOICES, default=RED)
    target = models.CharField(max_length=10, choices=TARGET_CHOICES, default=AUTO)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.label

    @property
    def is_external(self):
        """Vrai pour un lien externe (http/https)."""
        return self.url.startswith("http")

    @property
    def opens_in_new_tab(self):
        """Ouverture en nouvel onglet : forcée par `target`, sinon déduite du lien (auto :
        externe → nouvel onglet). Pilote target="_blank" rel="noopener noreferrer"."""
        if self.target == self.BLANK:
            return True
        if self.target == self.SELF:
            return False
        return self.is_external


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


def video_upload_to(instance, filename):
    """Range les vidéos par mois et randomise le nom (anti-collision, pas de fuite du nom
    d'origine). Calque `media.image_upload_to`. Type validé en amont (validate_video_file)."""
    ext = Path(filename).suffix.lower()
    return f"videos/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{ext}"


def build_embed_src(url):
    """URL d'iframe normalisée (YouTube-nocookie / Vimeo player) déduite d'un lien
    YouTube ou Vimeo, ou None si le lien n'est pas reconnu.

    L'`src` est TOUJOURS reconstruite à partir de l'identifiant extrait (jamais l'URL
    brute) : une URL forgée ne peut donc pas injecter d'attributs ni pointer ailleurs.
    YouTube est servi via youtube-nocookie.com (pas de cookie tant que la vidéo n'est
    pas lue → click-to-load RGPD côté template)."""
    parts = urlsplit(url or "")
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]

    if host in {"youtube.com", "m.youtube.com", "youtube-nocookie.com"}:
        if parts.path == "/watch":
            video_id = parse_qs(parts.query).get("v", [""])[0]
        else:
            match = re.fullmatch(r"/(?:embed|shorts)/([\w-]+)", parts.path)
            video_id = match.group(1) if match else ""
        video_id = video_id if re.fullmatch(r"[\w-]{1,32}", video_id or "") else ""
        if video_id:
            return f"https://www.youtube-nocookie.com/embed/{video_id}"
    elif host == "youtu.be":
        video_id = parts.path.lstrip("/")
        if re.fullmatch(r"[\w-]{1,32}", video_id or ""):
            return f"https://www.youtube-nocookie.com/embed/{video_id}"
    elif host == "vimeo.com":
        match = re.match(r"/(\d+)", parts.path)
        if match:
            return f"https://player.vimeo.com/video/{match.group(1)}"
    elif host == "player.vimeo.com":
        match = re.match(r"/video/(\d+)", parts.path)
        if match:
            return f"https://player.vimeo.com/video/{match.group(1)}"

    return None


class HomeMedia(SingletonModel, UUIDModel):
    """Singleton : bloc média à côté de l'intro de l'accueil. Exclusif via `mode` :
    OFF (rien), PHOTOS (carrousel des images liées) ou VIDEO (fichier téléversé OU
    embed YouTube/Vimeo). La cohérence du mode est garantie par `clean()`."""

    OFF = "off"
    PHOTOS = "photos"
    VIDEO = "video"
    MODE_CHOICES = [(OFF, "Désactivé"), (PHOTOS, "Photos"), (VIDEO, "Vidéo")]

    FILE = "file"
    EMBED = "embed"
    VIDEO_KIND_CHOICES = [(FILE, "Fichier téléversé"), (EMBED, "Lien YouTube / Vimeo")]

    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default=OFF)

    video_kind = models.CharField(max_length=10, choices=VIDEO_KIND_CHOICES, default=FILE)
    video_file = models.FileField(
        upload_to=video_upload_to, blank=True, validators=[validate_video_file]
    )
    # max_length relevé : les liens de partage YouTube/Vimeo (paramètres list, index,
    # pp…) dépassent souvent les 200 caractères par défaut d'URLField.
    video_url = models.URLField(max_length=500, blank=True, help_text="Lien YouTube ou Vimeo.")
    video_caption = models.CharField(max_length=255, blank=True)

    images = models.ManyToManyField(
        "media.Image", through="pages.HomeMediaImage", related_name="+", blank=True
    )

    def __str__(self):
        return self.get_mode_display()

    def clean(self):
        super().clean()
        # En mode vidéo, la source choisie doit être renseignée (l'autre reste conservée
        # mais inerte : on ne purge rien au changement de mode).
        if self.mode == self.VIDEO:
            if self.video_kind == self.FILE and not self.video_file:
                raise ValidationError({"video_file": "Téléversez un fichier vidéo."})
            if self.video_kind == self.EMBED and not self.video_url:
                raise ValidationError({"video_url": "Collez un lien YouTube ou Vimeo."})

    @property
    def embed_src(self):
        """URL d'iframe normalisée pour le mode embed (cf build_embed_src), ou None."""
        return build_embed_src(self.video_url)

    @property
    def embed_play_src(self):
        """URL d'embed avec lecture auto en sourdine. L'iframe n'étant créée qu'au clic
        (click-to-load), l'autoplay est déclenché par l'utilisateur ; le muet est requis
        par les navigateurs pour autoriser l'autoplay. Paramètre selon le lecteur
        (YouTube : `mute=1` / Vimeo : `muted=1`)."""
        src = self.embed_src
        if not src:
            return None
        mute = "mute=1" if "youtube" in src else "muted=1"
        return f"{src}?autoplay=1&{mute}"

    @property
    def video_mime(self):
        """Type MIME déduit de l'extension du fichier vidéo (pour l'attribut <source type>)."""
        ext = Path(self.video_file.name).suffix.lower() if self.video_file else ""
        return {".mp4": "video/mp4", ".webm": "video/webm"}.get(ext, "")

    @property
    def is_active(self):
        """Vrai seulement si le bloc a un média réellement affichable. Sinon l'accueil
        reste pleine largeur (un mode photos sans photo, ou une source vidéo vide, ne doit
        pas activer la mise en page 2 colonnes). On lit `image_items.all` (et non
        `.exists()`) pour profiter du prefetch de la vue et éviter une requête."""
        if self.mode == self.PHOTOS:
            return bool(self.image_items.all())
        if self.mode == self.VIDEO:
            if self.video_kind == self.FILE:
                return bool(self.video_file)
            return self.embed_src is not None
        return False


class HomeMediaImage(models.Model):
    """Table de liaison ordonnée entre le bloc média de l'accueil et les images du carrousel."""

    home_media = models.ForeignKey(
        HomeMedia, on_delete=models.CASCADE, related_name="image_items"
    )
    image = models.ForeignKey("media.Image", on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(fields=["home_media", "image"], name="unique_home_media_image"),
        ]

    def __str__(self):
        return f"{self.home_media} · {self.image}"
