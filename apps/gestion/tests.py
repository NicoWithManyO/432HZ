import io
import uuid
from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image as PILImage

from apps.accounts.models import OWNER, Invitation, Profile
from apps.common.models import PUBLISHED
from apps.common.sanitize import clean_html
from apps.events.models import Event, EventImage
from apps.gestion.forms import EventForm
from apps.media.models import Image
from apps.news.models import News


def test_clean_html_keeps_allowed_tags():
    html = "<p>Un <strong>concert</strong> et <a href='/x' title='x'>un lien</a>.</p>"
    cleaned = clean_html(html)
    assert "<strong>" in cleaned
    assert "<a " in cleaned and 'href="/x"' in cleaned


def test_clean_html_strips_disallowed_tags():
    cleaned = clean_html("<script>alert(1)</script><p>ok</p>")
    assert "<script>" not in cleaned
    assert "alert(1)" not in cleaned
    assert "<p>ok</p>" in cleaned


def test_clean_html_strips_disallowed_attributes():
    cleaned = clean_html('<p onclick="evil()" class="x">texte</p>')
    assert "onclick" not in cleaned
    assert "class" not in cleaned
    assert "texte" in cleaned


def test_clean_html_strips_image_tag():
    # img n'est pas dans l'allowlist (les médias passent par la galerie).
    cleaned = clean_html('<img src="x.jpg"><p>txt</p>')
    assert "<img" not in cleaned


# --- Vues events ---


@pytest.fixture
def validated_client(client):
    user = User.objects.create_user("editor", password="pw-test-1234")
    Profile.objects.create(user=user, is_validated=True)
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_event_list_requires_login(client):
    response = client.get(reverse("gestion:event-list"))
    assert response.status_code == 302  # anonyme → login


@pytest.mark.django_db
def test_event_list_forbidden_for_unvalidated(client):
    user = User.objects.create_user("pending", password="pw-test-1234")
    Profile.objects.create(user=user, is_validated=False)
    client.force_login(user)
    assert client.get(reverse("gestion:event-list")).status_code == 403


@pytest.mark.django_db
def test_event_create_sanitizes_description(validated_client):
    response = validated_client.post(
        reverse("gestion:event-create"),
        {
            "title": "Concert test",
            "slug": "",
            "kind": "",
            "starts_at": "2026-09-01T20:30",
            "ends_at": "",
            "location": "Le Brise-Glace",
            "price": "",
            "description": "<p>Top</p><script>alert(1)</script>",
            "cover": "",
        },
    )
    assert response.status_code == 302
    event = Event.objects.get(title="Concert test")
    assert "<script>" not in event.description
    assert "<p>Top</p>" in event.description
    assert event.status == "draft"  # créé en brouillon
    assert event.slug == "concert-test"  # slug auto


@pytest.mark.django_db
def test_event_publish_and_unpublish_views(validated_client):
    event = Event.objects.create(title="x", starts_at=timezone.now())
    validated_client.post(reverse("gestion:event-publish", args=[event.pk]))
    event.refresh_from_db()
    assert event.status == PUBLISHED and event.published_at is not None

    validated_client.post(reverse("gestion:event-unpublish", args=[event.pk]))
    event.refresh_from_db()
    assert event.status == "draft"


@pytest.mark.django_db
def test_event_list_filters(validated_client):
    now = timezone.now()
    Event.objects.create(title="à venir", starts_at=now + timedelta(days=3), status=PUBLISHED)
    Event.objects.create(title="passé", starts_at=now - timedelta(days=3), status=PUBLISHED)
    Event.objects.create(title="brouillon", starts_at=now + timedelta(days=1))

    def titles(filter_value):
        response = validated_client.get(reverse("gestion:event-list"), {"filter": filter_value})
        return {e.title for e in response.context["events"]}

    assert titles("upcoming") == {"à venir", "brouillon"}
    assert titles("past") == {"passé"}
    assert titles("drafts") == {"brouillon"}
    assert titles("all") == {"à venir", "passé", "brouillon"}


# --- Galerie ordonnée (events + actus) ---


def _event_data(**extra):
    # Données minimales valides pour EventForm (statut/galerie en plus selon le test).
    data = {
        "title": "Avec galerie",
        "slug": "",
        "kind": "",
        "starts_at": "2026-09-01T20:30",
        "ends_at": "",
        "location": "",
        "price": "",
        "description": "",
        "cover": "",
    }
    data.update(extra)
    return data


@pytest.mark.django_db
def test_clean_gallery_orders_dedupes_and_drops_unknown():
    a = Image.objects.create(alt="a")
    b = Image.objects.create(alt="b")
    unknown = uuid.uuid4()
    form = EventForm(data=_event_data(gallery=f"{b.pk},{a.pk},{b.pk},{unknown},pas-un-uuid"))
    assert form.is_valid(), form.errors
    # Ordre de saisie préservé, doublon de b retiré, id inconnu/invalide ignorés.
    assert form.cleaned_data["gallery"] == [b, a]


@pytest.mark.django_db
def test_cover_outside_gallery_is_added_to_it():
    a = Image.objects.create(alt="a")
    b = Image.objects.create(alt="b")
    # Couverture choisie hors galerie : elle doit rejoindre la galerie (ajoutée en fin),
    # pas être perdue ni invalider le formulaire.
    form = EventForm(data=_event_data(cover=str(a.pk), gallery=str(b.pk)))
    assert form.is_valid(), form.errors
    assert form.cleaned_data["gallery"] == [b, a]
    assert form.cleaned_data["cover"] == a


@pytest.mark.django_db
def test_cover_already_in_gallery_is_not_duplicated():
    a = Image.objects.create(alt="a")
    b = Image.objects.create(alt="b")
    form = EventForm(data=_event_data(cover=str(a.pk), gallery=f"{a.pk},{b.pk}"))
    assert form.is_valid(), form.errors
    assert form.cleaned_data["gallery"] == [a, b]


@pytest.mark.django_db
def test_save_gallery_creates_then_reorders_then_removes():
    a = Image.objects.create(alt="a")
    b = Image.objects.create(alt="b")
    event = Event.objects.create(title="x", starts_at=timezone.now())

    # Création des lignes dans l'ordre saisi.
    form = EventForm(data=_event_data(gallery=f"{a.pk},{b.pk}"), instance=event)
    assert form.is_valid(), form.errors
    form.save_gallery(event)
    assert list(event.gallery_items.values_list("image_id", "order")) == [(a.pk, 0), (b.pk, 1)]

    # Ré-enregistrement dans un autre ordre : les `order` sont remis à jour.
    form = EventForm(data=_event_data(gallery=f"{b.pk},{a.pk}"), instance=event)
    assert form.is_valid(), form.errors
    form.save_gallery(event)
    assert list(event.gallery_items.values_list("image_id", "order")) == [(b.pk, 0), (a.pk, 1)]

    # Retrait d'une image : sa ligne disparaît.
    form = EventForm(data=_event_data(gallery=f"{b.pk}"), instance=event)
    assert form.is_valid(), form.errors
    form.save_gallery(event)
    assert list(event.gallery_items.values_list("image_id", "order")) == [(b.pk, 0)]


@pytest.mark.django_db
def test_event_create_populates_gallery(validated_client):
    a = Image.objects.create(alt="a")
    b = Image.objects.create(alt="b")
    response = validated_client.post(
        reverse("gestion:event-create"),
        _event_data(title="Galerie event", gallery=f"{a.pk},{b.pk}"),
    )
    assert response.status_code == 302
    event = Event.objects.get(title="Galerie event")
    assert list(event.gallery_items.values_list("image_id", "order")) == [(a.pk, 0), (b.pk, 1)]


@pytest.mark.django_db
def test_news_create_populates_gallery(validated_client):
    a = Image.objects.create(alt="a")
    b = Image.objects.create(alt="b")
    response = validated_client.post(
        reverse("gestion:news-create"),
        {"title": "Galerie actu", "slug": "", "category": "", "description": "",
         "cover": "", "gallery": f"{b.pk},{a.pk}"},
    )
    assert response.status_code == 302
    news = News.objects.get(title="Galerie actu")
    assert list(news.gallery_items.values_list("image_id", "order")) == [(b.pk, 0), (a.pk, 1)]


@pytest.mark.django_db
def test_event_form_renders_gallery_picker(validated_client):
    # Le partial est inclus ET le champ caché `gallery` est rendu par as_p (pont du JS).
    response = validated_client.get(reverse("gestion:event-create"))
    assert response.status_code == 200
    assert b"data-gallery" in response.content
    assert b'name="gallery"' in response.content


def _png_upload(name="x.png"):
    buffer = io.BytesIO()
    PILImage.new("RGB", (32, 32), "blue").save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type="image/png")


@pytest.mark.django_db
def test_quick_upload_creates_image_and_returns_json(validated_client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    response = validated_client.post(
        reverse("gestion:media-quick-upload"), {"file": _png_upload()}
    )
    assert response.status_code == 200
    payload = response.json()
    assert Image.objects.filter(pk=payload["id"]).exists()
    assert payload["thumb"]  # URL de vignette renvoyée pour l'affichage immédiat


@pytest.mark.django_db
def test_quick_upload_persists_metadata(validated_client, settings, tmp_path):
    # Upload depuis la galerie : titre / alt / légende saisis sont enregistrés et renvoyés.
    settings.MEDIA_ROOT = tmp_path
    response = validated_client.post(
        reverse("gestion:media-quick-upload"),
        {
            "file": _png_upload(),
            "alt": "Affiche du concert",
            "title": "Concert mai",
            "caption": "Soirée d'ouverture",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    image = Image.objects.get(pk=payload["id"])
    assert (image.alt, image.title, image.caption) == (
        "Affiche du concert",
        "Concert mai",
        "Soirée d'ouverture",
    )
    assert payload["label"] == "Concert mai"  # titre prioritaire pour l'étiquette
    assert payload["caption"] == "Soirée d'ouverture"


@pytest.mark.django_db
def test_quick_upload_rejects_non_image(validated_client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    bad = SimpleUploadedFile("x.png", b"pas une image", content_type="image/png")
    response = validated_client.post(reverse("gestion:media-quick-upload"), {"file": bad})
    assert response.status_code == 400
    assert "file" in response.json()["errors"]
    assert Image.objects.count() == 0


@pytest.mark.django_db
def test_media_delete_confirm_lists_usage(validated_client):
    # La page de confirmation avertit des events/actus dont l'image sera retirée (CASCADE).
    image = Image.objects.create(alt="affiche")
    event = Event.objects.create(title="Concert lié", starts_at=timezone.now())
    EventImage.objects.create(event=event, image=image, order=0)
    response = validated_client.get(reverse("gestion:media-delete", args=[image.pk]))
    assert response.status_code == 200
    assert list(response.context["events_using"]) == [event]
    assert "Concert lié" in response.content.decode()


# --- Vues actus ---


@pytest.mark.django_db
def test_news_list_requires_login(client):
    response = client.get(reverse("gestion:news-list"))
    assert response.status_code == 302  # anonyme → login


@pytest.mark.django_db
def test_news_list_forbidden_for_unvalidated(client):
    user = User.objects.create_user("pending-news", password="pw-test-1234")
    Profile.objects.create(user=user, is_validated=False)
    client.force_login(user)
    assert client.get(reverse("gestion:news-list")).status_code == 403


@pytest.mark.django_db
def test_news_create_sanitizes_description(validated_client):
    response = validated_client.post(
        reverse("gestion:news-create"),
        {
            "title": "Appel à bénévoles",
            "slug": "",
            "category": "Appel",
            "description": "<p>Rejoignez-nous</p><script>alert(1)</script>",
            "cover": "",
        },
    )
    assert response.status_code == 302
    news = News.objects.get(title="Appel à bénévoles")
    assert "<script>" not in news.description
    assert "<p>Rejoignez-nous</p>" in news.description
    assert news.status == "draft"  # créée en brouillon
    assert news.slug == "appel-a-benevoles"  # slug auto


@pytest.mark.django_db
def test_news_publish_and_unpublish_views(validated_client):
    news = News.objects.create(title="x")
    validated_client.post(reverse("gestion:news-publish", args=[news.pk]))
    news.refresh_from_db()
    assert news.status == PUBLISHED and news.published_at is not None

    validated_client.post(reverse("gestion:news-unpublish", args=[news.pk]))
    news.refresh_from_db()
    assert news.status == "draft"


@pytest.mark.django_db
def test_news_list_filters(validated_client):
    News.objects.create(title="publiée", status=PUBLISHED)
    News.objects.create(title="brouillon")

    def titles(filter_value):
        response = validated_client.get(reverse("gestion:news-list"), {"filter": filter_value})
        return {n.title for n in response.context["news_list"]}

    assert titles("published") == {"publiée"}
    assert titles("drafts") == {"brouillon"}
    assert titles("all") == {"publiée", "brouillon"}


# --- Vues comptes (owner) ---


@pytest.fixture
def owner_client(client):
    user = User.objects.create_user("owner", password="pw-test-1234")
    Profile.objects.create(user=user, role=OWNER, is_validated=True)
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_accounts_forbidden_for_editor(validated_client):
    # validated_client est un éditeur validé, pas un owner.
    assert validated_client.get(reverse("gestion:accounts-list")).status_code == 403


@pytest.mark.django_db
def test_accounts_visible_for_owner(owner_client):
    assert owner_client.get(reverse("gestion:accounts-list")).status_code == 200


@pytest.mark.django_db
def test_invitation_create_generates_token(owner_client):
    response = owner_client.post(reverse("gestion:accounts-list"), {"email": "x@example.com"})
    assert response.status_code == 302
    inv = Invitation.objects.get()
    assert inv.token  # jeton généré par le modèle
    assert inv.created_by.username == "owner"


@pytest.mark.django_db
def test_invitation_regenerate_changes_token(owner_client):
    inv = Invitation.objects.create()
    old_token = inv.token
    owner_client.post(reverse("gestion:invitation-regenerate", args=[inv.pk]))
    inv.refresh_from_db()
    assert inv.token != old_token


@pytest.mark.django_db
def test_invitation_regenerate_skips_used(owner_client):
    # Régénérer une invitation déjà consommée n'émet pas un nouveau lien (mort) : no-op.
    inv = Invitation.objects.create(used_at=timezone.now())
    old_token = inv.token
    owner_client.post(reverse("gestion:invitation-regenerate", args=[inv.pk]))
    inv.refresh_from_db()
    assert inv.token == old_token


@pytest.mark.django_db
def test_profile_toggle_validation(owner_client):
    editor = User.objects.create_user("ed", password="pw-test-1234")
    profile = Profile.objects.create(user=editor, is_validated=True)
    owner_client.post(reverse("gestion:profile-toggle-validation", args=[profile.pk]))
    profile.refresh_from_db()
    assert profile.is_validated is False

    owner_client.post(reverse("gestion:profile-toggle-validation", args=[profile.pk]))
    profile.refresh_from_db()
    assert profile.is_validated is True


@pytest.mark.django_db
def test_owner_profile_validation_not_toggled(owner_client):
    # L'owner reste toujours validé (anti-lockout) : la bascule est sans effet.
    owner_profile = Profile.objects.get(role=OWNER)
    owner_client.post(reverse("gestion:profile-toggle-validation", args=[owner_profile.pk]))
    owner_profile.refresh_from_db()
    assert owner_profile.is_validated is True
