import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image as PILImage

from apps.media.forms import ImageMetaForm, ImageUploadForm
from apps.media.models import Image, image_upload_to
from apps.media.validators import (
    MAX_IMAGE_SIZE,
    MAX_VIDEO_SIZE,
    validate_image_file,
    validate_video_file,
)


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


def test_validate_rejects_too_many_pixels(monkeypatch):
    # Borne en pixels abaissée pour le test (sinon il faudrait générer une image énorme).
    monkeypatch.setattr("apps.media.validators.MAX_IMAGE_PIXELS", 4)
    with pytest.raises(ValidationError):
        validate_image_file(make_image_file(size=(64, 64)))  # 4096 px > 4


def test_model_field_carries_validator():
    # Filet defense-in-depth : la validation vit aussi sur le champ (chemins hors form).
    assert validate_image_file in Image._meta.get_field("file").validators


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


# --- Validateur vidéo ---


def _video_upload(name="clip.mp4", content_type="video/mp4", content=b"fake-video"):
    return SimpleUploadedFile(name, content, content_type=content_type)


@pytest.mark.parametrize(
    "name,content_type",
    [("clip.mp4", "video/mp4"), ("clip.webm", "video/webm")],
)
def test_validate_video_accepts_mp4_and_webm(name, content_type):
    validate_video_file(_video_upload(name=name, content_type=content_type))


def test_validate_video_rejects_disallowed_extension():
    with pytest.raises(ValidationError):
        validate_video_file(_video_upload(name="clip.mov", content_type="video/quicktime"))


def test_validate_video_rejects_disallowed_content_type():
    # Bonne extension mais content-type incohérent → refusé.
    with pytest.raises(ValidationError):
        validate_video_file(_video_upload(name="clip.mp4", content_type="application/octet-stream"))


def test_validate_video_rejects_oversize():
    upload = _video_upload()
    upload.size = MAX_VIDEO_SIZE + 1  # gros fichier simulé sans générer 100 Mo
    with pytest.raises(ValidationError):
        validate_video_file(upload)


def test_home_media_field_carries_video_validator():
    from apps.pages.models import HomeMedia

    assert validate_video_file in HomeMedia._meta.get_field("video_file").validators


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
