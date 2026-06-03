"""Validation des fichiers image et vidéo de la médiathèque.

On ne fait pas confiance à l'extension : pour les images, Pillow doit reconnaître un
format autorisé. La logique est isolée ici pour être réutilisée (form, futurs imports)."""

from pathlib import Path

from django.core.exceptions import ValidationError
from PIL import Image as PILImage
from PIL import UnidentifiedImageError

# Poids maximal accepté (~8 Mo).
MAX_IMAGE_SIZE = 8 * 1024 * 1024

# Surface maximale en pixels (~50 Mpx) : borne le coût de décodage en aval
# (génération des vignettes par easy-thumbnails) et neutralise les « bombes » de
# décompression — un petit fichier déclarant des dimensions énormes.
MAX_IMAGE_PIXELS = 50_000_000

# Formats réellement acceptés (sortie en WebP gérée par easy-thumbnails).
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}


def validate_image_file(upload):
    """Refuse les fichiers trop lourds, trop grands en pixels, ou qui ne sont pas une
    image d'un format autorisé (JPEG / PNG / WEBP)."""
    if upload.size > MAX_IMAGE_SIZE:
        max_mo = MAX_IMAGE_SIZE // (1024 * 1024)
        raise ValidationError(f"Image trop lourde ({max_mo} Mo maximum).")

    try:
        with PILImage.open(upload) as img:
            image_format = img.format
            width, height = img.size  # connu dès l'en-tête, sans décoder les pixels
            img.verify()  # contrôle d'intégrité (le fichier est ensuite inutilisable)
    except PILImage.DecompressionBombError as exc:
        raise ValidationError("Image trop grande : dimensions excessives.") from exc
    except (UnidentifiedImageError, OSError) as exc:
        raise ValidationError("Fichier invalide : ce n'est pas une image lisible.") from exc
    finally:
        # verify() consomme le flux : on le rembobine pour la sauvegarde ultérieure.
        upload.seek(0)

    if width * height > MAX_IMAGE_PIXELS:
        max_mpx = MAX_IMAGE_PIXELS // 1_000_000
        raise ValidationError(f"Image trop grande ({max_mpx} Mpx maximum).")

    if image_format not in ALLOWED_IMAGE_FORMATS:
        formats = ", ".join(sorted(ALLOWED_IMAGE_FORMATS))
        raise ValidationError(f"Format non supporté. Formats acceptés : {formats}.")


# Poids maximal accepté pour une vidéo auto-hébergée (~100 Mo). Au-delà, l'embed
# YouTube/Vimeo reste préférable (pas de charge serveur ni de bande passante).
MAX_VIDEO_SIZE = 100 * 1024 * 1024

# On se limite à deux conteneurs lisibles nativement par <video> sur tous les navigateurs.
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm"}
ALLOWED_VIDEO_CONTENT_TYPES = {"video/mp4", "video/webm"}


def validate_video_file(upload):
    """Refuse les vidéos trop lourdes ou d'un conteneur non autorisé (MP4 / WebM).

    Contrairement aux images, pas d'inspection binaire (pas d'équivalent Pillow léger) :
    on s'appuie sur le poids, l'extension et le content-type déclaré (choix KISS assumé)."""
    if upload.size > MAX_VIDEO_SIZE:
        max_mo = MAX_VIDEO_SIZE // (1024 * 1024)
        raise ValidationError(f"Vidéo trop lourde ({max_mo} Mo maximum).")

    extension = Path(upload.name).suffix.lower()
    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        formats = ", ".join(sorted(ALLOWED_VIDEO_EXTENSIONS))
        raise ValidationError(f"Format non supporté. Formats acceptés : {formats}.")

    content_type = getattr(upload, "content_type", "")
    if content_type and content_type not in ALLOWED_VIDEO_CONTENT_TYPES:
        raise ValidationError("Le fichier ne déclare pas un type vidéo MP4 / WebM valide.")
