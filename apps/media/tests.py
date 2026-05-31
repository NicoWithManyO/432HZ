import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image as PILImage

from apps.media.forms import ImageMetaForm, ImageUploadForm
from apps.media.models import Image, image_upload_to
from apps.media.validators import MAX_IMAGE_SIZE, validate_image_file


def make_image_file(name="photo.jpg", fmt="JPEG", size=(64, 64)):
    """Construit un fichier image valide en mémoire pour les tests."""
    buffer = io.BytesIO()
    PILImage.new("RGB", size, "red").save(buffer, format=fmt)
    buffer.seek(0)
    content_type = f"image/{fmt.lower()}"
    return SimpleUploadedFile(name, buffer.read(), content_type=content_type)


def test_validate_accepts_real_image():
    # Ne doit pas lever, et doit rembobiner le flux pour la sauvegarde.
    upload = make_image_file()
    validate_image_file(upload)
    assert upload.tell() == 0


def test_validate_rejects_non_image():
    # Un .jpg qui n'est en fait pas une image (le type réel prime sur l'extension).
    fake = SimpleUploadedFile("photo.jpg", b"ceci n'est pas une image", content_type="image/jpeg")
    with pytest.raises(ValidationError):
        validate_image_file(fake)


def test_validate_rejects_disallowed_format():
    bmp = make_image_file(name="image.bmp", fmt="BMP")
    with pytest.raises(ValidationError):
        validate_image_file(bmp)


def test_validate_rejects_oversize_file():
    upload = make_image_file()
    upload.size = MAX_IMAGE_SIZE + 1  # gros fichier simulé sans générer 8 Mo
    with pytest.raises(ValidationError):
        validate_image_file(upload)


def test_upload_to_randomizes_filename():
    path = image_upload_to(None, "Mon Affiche.JPG")
    # Nom randomisé (32 hexa), extension minuscule conservée, rangé par mois.
    assert path.startswith("images/")
    assert path.endswith(".jpg")
    assert "mon affiche" not in path.lower()
    stem = path.rsplit("/", 1)[-1].removesuffix(".jpg")
    assert len(stem) == 32


def test_upload_form_rejects_non_image():
    fake = SimpleUploadedFile("x.png", b"pas une image", content_type="image/png")
    form = ImageUploadForm(data={"alt": "", "title": ""}, files={"file": fake})
    assert not form.is_valid()
    assert "file" in form.errors


@pytest.mark.django_db
def test_upload_form_saves_valid_image():
    form = ImageUploadForm(
        data={"alt": "Affiche", "title": "Concert"},
        files={"file": make_image_file()},
    )
    assert form.is_valid(), form.errors
    image = form.save()
    assert Image.objects.filter(pk=image.pk).exists()
    assert image.file.name.endswith(".jpg")


@pytest.mark.django_db
def test_meta_form_persists_caption():
    # La légende (médiathèque) est éditable et persistée via le form de métadonnées.
    image = Image.objects.create(alt="Affiche")
    form = ImageMetaForm(
        data={"alt": "Affiche", "title": "Concert", "caption": "Concert d'ouverture, 2024"},
        instance=image,
    )
    assert form.is_valid(), form.errors
    form.save()
    image.refresh_from_db()
    assert image.caption == "Concert d'ouverture, 2024"
