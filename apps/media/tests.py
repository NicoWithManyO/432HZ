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


# --- Ré-encodage à l'upload (P5) ---


@pytest.mark.django_db
def test_save_strips_exif_metadata(settings, tmp_path):
    # Un EXIF embarqué (ex. géolocalisation, légende) ne doit pas survivre à l'upload.
    settings.MEDIA_ROOT = tmp_path
    exif = PILImage.Exif()
    exif[0x010E] = "Légende secrète"  # ImageDescription
    buffer = io.BytesIO()
    PILImage.new("RGB", (64, 64), "red").save(buffer, format="JPEG", exif=exif)
    upload = SimpleUploadedFile("p.jpg", buffer.getvalue(), content_type="image/jpeg")

    image = Image.objects.create(file=upload)

    image.refresh_from_db()
    with image.file.open("rb") as fh, PILImage.open(fh) as stored:
        assert 0x010E not in stored.getexif()


@pytest.mark.django_db
def test_save_drops_appended_bytes(settings, tmp_path):
    # Polyglotte : des octets greffés après une image valide doivent disparaître.
    settings.MEDIA_ROOT = tmp_path
    buffer = io.BytesIO()
    PILImage.new("RGB", (64, 64), "red").save(buffer, format="PNG")
    payload = buffer.getvalue() + b"<?php evil(); ?>"
    upload = SimpleUploadedFile("p.png", payload, content_type="image/png")

    image = Image.objects.create(file=upload)

    image.refresh_from_db()
    with image.file.open("rb") as fh:
        assert b"<?php" not in fh.read()


@pytest.mark.django_db
def test_save_applies_exif_orientation(settings, tmp_path):
    # Photo avec orientation EXIF (typique d'un téléphone) : on redresse les pixels à
    # l'upload, sinon — l'EXIF étant retiré — l'image s'afficherait de travers.
    settings.MEDIA_ROOT = tmp_path
    exif = PILImage.Exif()
    exif[0x0112] = 6  # Orientation = rotation 90° → largeur/hauteur échangées à l'affichage
    buffer = io.BytesIO()
    PILImage.new("RGB", (40, 20), "red").save(buffer, format="JPEG", exif=exif)
    upload = SimpleUploadedFile("p.jpg", buffer.getvalue(), content_type="image/jpeg")

    image = Image.objects.create(file=upload)

    image.refresh_from_db()
    with image.file.open("rb") as fh, PILImage.open(fh) as stored:
        assert stored.size == (20, 40)  # pixels redressés
        assert 0x0112 not in stored.getexif()  # tag d'orientation retiré


@pytest.mark.django_db
def test_save_preserves_format(settings, tmp_path):
    # Le ré-encodage conserve le format d'origine (PNG reste PNG).
    settings.MEDIA_ROOT = tmp_path
    image = Image.objects.create(file=make_image_file(name="p.png", fmt="PNG"))

    image.refresh_from_db()
    with image.file.open("rb") as fh, PILImage.open(fh) as stored:
        assert stored.format == "PNG"


@pytest.mark.django_db
def test_metadata_edit_does_not_reprocess_stored_file(settings, tmp_path):
    # Une édition de métadonnées ne doit pas ré-encoder ni réécrire le fichier stocké.
    settings.MEDIA_ROOT = tmp_path
    image = Image.objects.create(file=make_image_file())
    image.refresh_from_db()
    stored_name = image.file.name
    with image.file.open("rb") as fh:
        original = fh.read()

    form = ImageMetaForm(
        data={"alt": "Affiche", "title": "Concert", "caption": "Ouverture"},
        instance=image,
    )
    assert form.is_valid(), form.errors
    form.save()

    image.refresh_from_db()
    assert image.file.name == stored_name  # pas de nouvelle écriture
    with image.file.open("rb") as fh:
        assert fh.read() == original  # octets inchangés


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
