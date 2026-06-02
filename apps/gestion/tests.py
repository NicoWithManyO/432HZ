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
from apps.pages.models import (
    AssoContent,
    CallToAction,
    ContactContent,
    HomeContent,
    KeyFigure,
    MentionsContent,
    Mission,
    SocialLink,
    TickerItem,
)


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


# --- Contenus du site (hero accueil + bandeau) ---


@pytest.mark.django_db
def test_ticker_create_requires_login(client):
    response = client.post(reverse("gestion:ticker-create"), {"text": "X"})
    assert response.status_code == 302  # anonyme → login


@pytest.mark.django_db
def test_ticker_create_forbidden_for_unvalidated(client):
    user = User.objects.create_user("pending", password="pw-test-1234")
    Profile.objects.create(user=user, is_validated=False)
    client.force_login(user)
    assert client.post(reverse("gestion:ticker-create"), {"text": "X"}).status_code == 403


@pytest.mark.django_db
def test_ticker_create_appends_at_end(validated_client):
    TickerItem.objects.all().delete()
    TickerItem.objects.create(text="Premier", order=0)
    response = validated_client.post(
        reverse("gestion:ticker-create"), {"text": "Nouveau"}, follow=True
    )
    created = TickerItem.objects.get(text="Nouveau")
    assert created.order == 1
    assert "Phrase ajoutée" in response.content.decode()  # retour de succès (PRG)


@pytest.mark.django_db
def test_ticker_create_invalid_surfaces_error(validated_client):
    # Texte vide → rien créé, et l'échec remonte via un message (PRG).
    TickerItem.objects.all().delete()
    response = validated_client.post(
        reverse("gestion:ticker-create"), {"text": ""}, follow=True
    )
    assert TickerItem.objects.count() == 0
    assert "non ajoutée" in response.content.decode()


@pytest.mark.django_db
def test_ticker_delete(validated_client):
    item = TickerItem.objects.create(text="À supprimer", order=0)
    validated_client.post(reverse("gestion:ticker-delete", args=[item.pk]))
    assert not TickerItem.objects.filter(pk=item.pk).exists()


@pytest.mark.django_db
def test_ticker_toggle_highlight(validated_client):
    item = TickerItem.objects.create(text="X", order=0, highlighted=False)
    validated_client.post(reverse("gestion:ticker-toggle-highlight", args=[item.pk]))
    item.refresh_from_db()
    assert item.highlighted is True


@pytest.mark.django_db
def test_ticker_move_swaps_order_with_neighbor(validated_client):
    TickerItem.objects.all().delete()
    first = TickerItem.objects.create(text="A", order=0)
    second = TickerItem.objects.create(text="B", order=1)
    validated_client.post(reverse("gestion:ticker-move", args=[second.pk]) + "?dir=up")
    first.refresh_from_db()
    second.refresh_from_db()
    assert second.order == 0
    assert first.order == 1


@pytest.mark.django_db
def test_home_content_update(validated_client):
    home = HomeContent.load()
    response = validated_client.post(
        reverse("gestion:home-content-update"),
        {
            "subtitle": "Nouveau sous-titre",
            "punchline": "Une [r]punchline[/r].",
            "intro": "Intro modifiée.",
        },
        follow=True,
    )
    home.refresh_from_db()
    assert home.subtitle == "Nouveau sous-titre"
    assert home.punchline == "Une [r]punchline[/r]."
    # Fragment sans apostrophe (Django échappe ' en &#x27;) et propre au message de succès.
    assert "accueil enregistré" in response.content.decode()  # retour de succès (PRG)


@pytest.mark.django_db
def test_home_display_update(validated_client):
    home = HomeContent.load()
    response = validated_client.post(
        reverse("gestion:home-display-update"),
        {"events_count": 5, "news_count": 6},
        follow=True,
    )
    home.refresh_from_db()
    assert home.events_count == 5
    assert home.news_count == 6
    assert "Affichage de l&#x27;accueil enregistré" in response.content.decode()


@pytest.mark.django_db
def test_home_display_update_rejects_over_max(validated_client):
    home = HomeContent.load()
    before = home.events_count
    response = validated_client.post(
        reverse("gestion:home-display-update"),
        {"events_count": 20, "news_count": 4},
        follow=True,
    )
    home.refresh_from_db()
    # Borne haute (12) : la valeur hors limite n'est pas enregistrée.
    assert home.events_count == before
    assert "non enregistré" in response.content.decode()


@pytest.mark.django_db
def test_dashboard_renders_tabs_and_accordions(validated_client):
    # Onglets : un par page éditable, chacun relié à son panneau (aria-controls).
    html = validated_client.get(reverse("gestion:dashboard")).content.decode()
    for slug in ("accueil", "asso", "contact", "mentions"):
        assert f'aria-controls="panel-{slug}"' in html
        assert f'id="panel-{slug}"' in html
    # Accordéons repliables : 4 sur l'accueil (Hero + Bandeau + Boutons + Affichage) + 4 sur
    # L'asso (Textes + Missions + Chiffres-clés + Boutons) + 2 sur Contact (Textes &
    # coordonnées + Réseaux) + 1 sur Mentions légales (Textes).
    assert html.count('class="gestion-accordion"') == 11
    assert reverse("gestion:home-display-update") in html


# --- Contenu page L'asso : singleton + sanitize + édition ---


@pytest.mark.django_db
def test_asso_content_is_singleton():
    # Le seed pose déjà l'unique ligne ; toute sauvegarde « neuve » la met à jour.
    assert AssoContent.objects.count() == 1
    AssoContent(
        kicker="K", title="T", manifesto="<p>x</p>",
        missions_kicker="MK", missions_title="MT",
    ).save()
    assert AssoContent.objects.count() == 1


@pytest.mark.django_db
def test_asso_content_sanitizes_manifesto_on_save():
    asso = AssoContent.load()
    asso.manifesto = "<p>ok</p><script>alert(1)</script>"
    asso.save()
    asso.refresh_from_db()
    assert "<script>" not in asso.manifesto
    assert "alert(1)" not in asso.manifesto
    assert "<p>ok</p>" in asso.manifesto


@pytest.mark.django_db
def test_sanitized_html_model_tolerates_none_field():
    # Mixin partagé : un champ riche à None ne doit pas faire planter le save (→ "").
    asso = AssoContent.load()
    asso.manifesto = None
    asso.save()
    asso.refresh_from_db()
    assert asso.manifesto == ""


@pytest.mark.django_db
def test_asso_content_update(validated_client):
    response = validated_client.post(
        reverse("gestion:asso-content-update"),
        {
            "kicker": "Le collectif",
            "title": "432 Hz",
            "manifesto": "<p>Nouveau manifeste.</p>",
            "missions_kicker": "Nos missions",
            "missions_title": "Ce qu'on défend",
        },
        follow=True,
    )
    asso = AssoContent.load()
    assert asso.kicker == "Le collectif"
    assert asso.missions_title == "Ce qu'on défend"
    # Fragment sans apostrophe (Django échappe ' en &#x27;), propre au message de succès.
    assert "page L" in response.content.decode() and "enregistrés" in response.content.decode()


@pytest.mark.django_db
def test_asso_content_update_invalid_surfaces_error(validated_client):
    response = validated_client.post(
        reverse("gestion:asso-content-update"),
        {"kicker": "", "title": "", "manifesto": "", "missions_kicker": "",
         "missions_title": ""},
        follow=True,
    )
    assert "non enregistrés" in response.content.decode()


# --- Contenu page Contact : singleton + sanitize + édition ---


@pytest.mark.django_db
def test_contact_content_is_singleton():
    # Le seed pose déjà l'unique ligne ; toute sauvegarde « neuve » la met à jour.
    assert ContactContent.objects.count() == 1
    ContactContent(
        kicker="K", title="T", intro="<p>x</p>", coordinates_title="C",
        email="a@b.fr", address="A", networks_title="N",
    ).save()
    assert ContactContent.objects.count() == 1


@pytest.mark.django_db
def test_contact_content_sanitizes_intro_on_save():
    contact = ContactContent.load()
    contact.intro = "<p>ok</p><script>alert(1)</script>"
    contact.save()
    contact.refresh_from_db()
    assert "<script>" not in contact.intro
    assert "alert(1)" not in contact.intro
    assert "<p>ok</p>" in contact.intro


@pytest.mark.django_db
def test_contact_content_update(validated_client):
    response = validated_client.post(
        reverse("gestion:contact-content-update"),
        {
            "kicker": "Écris-nous",
            "title": "Contact",
            "intro": "<p>Nouvelle intro.</p>",
            "coordinates_title": "Coordonnées",
            "email": "hello@432hz.fr",
            "address": "Annecy",
            "networks_title": "Réseaux",
        },
        follow=True,
    )
    contact = ContactContent.load()
    assert contact.kicker == "Écris-nous"
    assert contact.email == "hello@432hz.fr"
    assert "page Contact" in response.content.decode()
    assert "enregistrés" in response.content.decode()


@pytest.mark.django_db
def test_contact_content_update_invalid_surfaces_error(validated_client):
    response = validated_client.post(
        reverse("gestion:contact-content-update"),
        {"kicker": "", "title": "", "intro": "", "coordinates_title": "",
         "email": "pas-un-email", "address": "", "networks_title": ""},
        follow=True,
    )
    assert "non enregistrés" in response.content.decode()


@pytest.mark.django_db
def test_social_link_create_appends_at_end(validated_client):
    SocialLink.objects.all().delete()
    SocialLink.objects.create(label="Insta", url="https://instagram.com/", order=0)
    validated_client.post(
        reverse("gestion:list-create", args=["social-link"]),
        {"social-link-new-label": "Bandcamp", "social-link-new-url": "https://bandcamp.com/"},
    )
    created = SocialLink.objects.get(label="Bandcamp")
    assert created.order == 1


# --- Contenu page Mentions légales : singleton + sanitize + édition ---


@pytest.mark.django_db
def test_mentions_content_is_singleton():
    # Le seed pose déjà l'unique ligne ; toute sauvegarde « neuve » la met à jour.
    assert MentionsContent.objects.count() == 1
    MentionsContent(
        kicker="K", title="T", editor_html="<p>e</p>", hosting_html="<p>h</p>",
        intellectual_property_html="<p>i</p>", privacy_html="<p>p</p>",
    ).save()
    assert MentionsContent.objects.count() == 1


@pytest.mark.django_db
def test_mentions_content_sanitizes_sections_on_save():
    mentions = MentionsContent.load()
    mentions.privacy_html = "<p>ok</p><script>alert(1)</script>"
    mentions.save()
    mentions.refresh_from_db()
    assert "<script>" not in mentions.privacy_html
    assert "alert(1)" not in mentions.privacy_html
    assert "<p>ok</p>" in mentions.privacy_html


@pytest.mark.django_db
def test_mentions_content_update(validated_client):
    response = validated_client.post(
        reverse("gestion:mentions-content-update"),
        {
            "kicker": "Légal",
            "title": "Mentions légales",
            "editor_html": "<p>Nouvel éditeur.</p>",
            "hosting_html": "<p>Nouvel hébergeur.</p>",
            "intellectual_property_html": "<p>PI.</p>",
            "privacy_html": "<p>Vie privée.</p>",
        },
        follow=True,
    )
    mentions = MentionsContent.load()
    assert mentions.kicker == "Légal"
    assert "Nouvel éditeur." in mentions.editor_html
    assert "page Mentions légales" in response.content.decode()
    assert "enregistrés" in response.content.decode()


@pytest.mark.django_db
def test_mentions_content_update_invalid_surfaces_error(validated_client):
    response = validated_client.post(
        reverse("gestion:mentions-content-update"),
        {"kicker": "", "title": "", "editor_html": "", "hosting_html": "",
         "intellectual_property_html": "", "privacy_html": ""},
        follow=True,
    )
    assert "non enregistrés" in response.content.decode()


# --- CRUD générique de listes ordonnées (missions, chiffres-clés) ---


# Les formulaires d'ajout/édition sont préfixés (plusieurs cohabitent sur le dashboard).
@pytest.mark.django_db
def test_ordered_list_create_appends_at_end(validated_client):
    Mission.objects.all().delete()
    Mission.objects.create(title="Première", description="d", order=0)
    validated_client.post(
        reverse("gestion:list-create", args=["mission"]),
        {"mission-new-title": "Nouvelle", "mission-new-description": "desc"},
    )
    created = Mission.objects.get(title="Nouvelle")
    assert created.order == 1


@pytest.mark.django_db
def test_ordered_list_create_invalid_surfaces_error(validated_client):
    count = Mission.objects.count()
    response = validated_client.post(
        reverse("gestion:list-create", args=["mission"]),
        {"mission-new-title": "", "mission-new-description": ""},
        follow=True,
    )
    assert Mission.objects.count() == count
    assert "non ajouté" in response.content.decode()


@pytest.mark.django_db
def test_ordered_list_update_edits_item(validated_client):
    mission = Mission.objects.create(title="Avant", description="d", order=0)
    response = validated_client.post(
        reverse("gestion:list-update", args=["mission", mission.pk]),
        {
            f"mission-{mission.pk}-title": "Après",
            f"mission-{mission.pk}-description": "modifiée",
        },
        follow=True,
    )
    mission.refresh_from_db()
    assert mission.title == "Après"
    assert mission.description == "modifiée"
    assert "modifié" in response.content.decode()


@pytest.mark.django_db
def test_ordered_list_delete(validated_client):
    item = KeyFigure.objects.create(text="À supprimer", order=99)
    validated_client.post(reverse("gestion:list-delete", args=["key-figure", item.pk]))
    assert not KeyFigure.objects.filter(pk=item.pk).exists()


@pytest.mark.django_db
def test_ordered_list_move_swaps_order_with_neighbor(validated_client):
    Mission.objects.all().delete()
    first = Mission.objects.create(title="A", description="d", order=0)
    second = Mission.objects.create(title="B", description="d", order=1)
    validated_client.post(reverse("gestion:list-move", args=["mission", second.pk]) + "?dir=up")
    first.refresh_from_db()
    second.refresh_from_db()
    assert second.order == 0
    assert first.order == 1


@pytest.mark.django_db
def test_cta_create_is_scoped_to_its_page(validated_client):
    # Le compteur d'ordre repart de 0 par page : ajouter côté asso ne dépend pas du hero.
    CallToAction.objects.all().delete()
    CallToAction.objects.create(page=CallToAction.HOME, label="H1", url="/", order=0)
    CallToAction.objects.create(page=CallToAction.HOME, label="H2", url="/", order=1)
    validated_client.post(
        reverse("gestion:list-create", args=["asso-cta"]),
        {"asso-cta-new-label": "Don", "asso-cta-new-url": "/don/",
         "asso-cta-new-variant": "ghost"},
    )
    created = CallToAction.objects.get(label="Don")
    assert created.page == CallToAction.ASSO  # scope posé par la vue, pas saisi
    assert created.variant == "ghost"
    assert created.order == 0  # 1er bouton de la page asso, indépendant du hero


@pytest.mark.django_db
def test_cta_url_rejects_dangerous_scheme(validated_client):
    # Le lien est rendu dans un href : un schéma javascript: doit être refusé (XSS).
    count = CallToAction.objects.count()
    response = validated_client.post(
        reverse("gestion:list-create", args=["home-cta"]),
        {"home-cta-new-label": "X", "home-cta-new-url": "javascript:alert(1)",
         "home-cta-new-variant": "red"},
        follow=True,
    )
    assert CallToAction.objects.count() == count  # rien créé
    assert "non ajouté" in response.content.decode()


@pytest.mark.django_db
def test_cta_move_stays_within_its_page(validated_client):
    # Réordonner un bouton asso ne doit pas échanger avec un bouton de l'accueil.
    CallToAction.objects.all().delete()
    home = CallToAction.objects.create(page=CallToAction.HOME, label="H", url="/", order=0)
    a0 = CallToAction.objects.create(page=CallToAction.ASSO, label="A0", url="/", order=0)
    a1 = CallToAction.objects.create(page=CallToAction.ASSO, label="A1", url="/", order=1)
    validated_client.post(reverse("gestion:list-move", args=["asso-cta", a1.pk]) + "?dir=up")
    home.refresh_from_db()
    a0.refresh_from_db()
    a1.refresh_from_db()
    assert a1.order == 0 and a0.order == 1  # échangés entre eux
    assert home.order == 0  # le hero n'a pas bougé


@pytest.mark.django_db
def test_cta_move_cross_scope_is_404(validated_client):
    # Un pk de l'accueil via la clé asso-cta → 404 (pas de swap croisé entre pages).
    home = CallToAction.objects.create(page=CallToAction.HOME, label="H", url="/", order=0)
    response = validated_client.post(
        reverse("gestion:list-move", args=["asso-cta", home.pk]) + "?dir=down"
    )
    assert response.status_code == 404


@pytest.mark.django_db
def test_cta_delete_cross_scope_is_404(validated_client):
    asso = CallToAction.objects.create(page=CallToAction.ASSO, label="A", url="/", order=0)
    response = validated_client.post(reverse("gestion:list-delete", args=["home-cta", asso.pk]))
    assert response.status_code == 404
    assert CallToAction.objects.filter(pk=asso.pk).exists()  # non supprimé


@pytest.mark.django_db
def test_ordered_list_unknown_key_is_404(validated_client):
    response = validated_client.post(reverse("gestion:list-create", args=["inconnu"]), {})
    assert response.status_code == 404


@pytest.mark.django_db
def test_ordered_list_create_requires_login(client):
    response = client.post(reverse("gestion:list-create", args=["mission"]), {"title": "X"})
    assert response.status_code == 302  # anonyme → login
