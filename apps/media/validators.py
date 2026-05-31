"""Validation des fichiers image de la médiathèque.

On ne fait pas confiance à l'extension : Pillow doit reconnaître un format
autorisé. La logique est isolée ici pour être réutilisée (form, futurs imports)."""

from django.core.exceptions import ValidationError
from PIL import Image as PILImage
from PIL import UnidentifiedImageError

# Poids maximal accepté (~8 Mo).
MAX_IMAGE_SIZE = 8 * 1024 * 1024

# Formats réellement acceptés (sortie en WebP gérée par easy-thumbnails).
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}


def validate_image_file(upload):
    """Refuse les fichiers trop lourds ou qui ne sont pas une image d'un format autorisé."""
    if upload.size > MAX_IMAGE_SIZE:
        max_mo = MAX_IMAGE_SIZE // (1024 * 1024)
        raise ValidationError(f"Image trop lourde ({max_mo} Mo maximum).")

    try:
        with PILImage.open(upload) as img:
            image_format = img.format
            img.verify()  # contrôle d'intégrité (le fichier est ensuite inutilisable)
    except (UnidentifiedImageError, OSError) as exc:
        raise ValidationError("Fichier invalide : ce n'est pas une image lisible.") from exc
    finally:
        # verify() consomme le flux : on le rembobine pour la sauvegarde ultérieure.
        upload.seek(0)

    if image_format not in ALLOWED_IMAGE_FORMATS:
        formats = ", ".join(sorted(ALLOWED_IMAGE_FORMATS))
        raise ValidationError(f"Format non supporté. Formats acceptés : {formats}.")
