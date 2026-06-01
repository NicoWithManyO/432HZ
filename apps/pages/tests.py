from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.common.models import PUBLISHED
from apps.events.models import Event
from apps.news.models import News
from apps.pages.models import HomeContent, TickerItem
from apps.pages.punchline import render_punchline


def test_render_punchline_escapes_plain_text():
    # Tout est échappé : aucune balise injectée ne survit.
    out = render_punchline("Tom & <b>Jerry</b>")
    assert "<b>" not in out
    assert "&amp;" in out
    assert "&lt;b&gt;" in out


def test_render_punchline_wraps_marker_in_red_span():
    out = render_punchline("On fait vibrer le [r]spectacle vivant[/r].")
    assert '<span class="text-red italic">spectacle vivant</span>' in out
    assert "[r]" not in out


def test_render_punchline_neutralizes_script_inside_marker():
    # Le contenu du marqueur est échappé AVANT le remplacement → pas d'XSS.
    out = render_punchline("[r]<script>alert(1)</script>[/r]")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_render_punchline_leaves_unclosed_marker_literal():
    out = render_punchline("texte [r]sans fin")
    assert "<span" not in out
    assert "[r]sans fin" in out


@pytest.mark.django_db
def test_home_content_load_returns_singleton():
    # La migration de seed crée la ligne unique.
    home = HomeContent.load()
    assert home is not None
    assert home.subtitle


@pytest.mark.django_db
def test_home_content_save_enforces_singleton():
    # Une 2e création ne crée pas de ligne : elle écrase l'existante.
    HomeContent.objects.all().delete()
    first = HomeContent.objects.create(subtitle="A", punchline="p", intro="i")
    HomeContent.objects.create(subtitle="B", punchline="p", intro="i")
    assert HomeContent.objects.count() == 1
    assert HomeContent.load().pk == first.pk
    assert HomeContent.load().subtitle == "B"


@pytest.mark.django_db
def test_ticker_bar_renders_items_with_highlight(client):
    TickerItem.objects.all().delete()
    TickerItem.objects.create(text="Phrase rouge", highlighted=True, order=0)
    TickerItem.objects.create(text="Phrase neutre", highlighted=False, order=1)
    html = client.get(reverse("home")).content.decode()
    assert "Phrase rouge" in html
    assert "Phrase neutre" in html
    # La phrase mise en avant porte la classe rouge, l'autre la classe papier.
    assert '<span class="text-red">Phrase rouge</span>' in html
    assert '<span class="text-paper">Phrase neutre</span>' in html


@pytest.mark.django_db
def test_ticker_bar_hidden_when_empty(client):
    TickerItem.objects.all().delete()
    html = client.get(reverse("home")).content.decode()
    assert "data-ticker" not in html


# --- Agenda & actus publics (P3.1) : le public ne voit QUE le publié ---


@pytest.mark.django_db
def test_agenda_list_shows_published_upcoming_hides_draft(client):
    soon = timezone.now() + timedelta(days=10)
    Event.objects.create(title="Concert public", starts_at=soon, status=PUBLISHED)
    Event.objects.create(title="Concert brouillon", starts_at=soon)  # draft par défaut
    html = client.get(reverse("agenda")).content.decode()
    assert "Concert public" in html
    assert "Concert brouillon" not in html


@pytest.mark.django_db
def test_agenda_list_when_filter_separates_upcoming_and_past(client):
    past = timezone.now() - timedelta(days=10)
    future = timezone.now() + timedelta(days=10)
    Event.objects.create(title="Event passé", starts_at=past, status=PUBLISHED)
    Event.objects.create(title="Event futur", starts_at=future, status=PUBLISHED)

    # Défaut : à venir.
    default_html = client.get(reverse("agenda")).content.decode()
    assert "Event futur" in default_html
    assert "Event passé" not in default_html

    # ?when=past : passés uniquement.
    past_html = client.get(reverse("agenda"), {"when": "past"}).content.decode()
    assert "Event passé" in past_html
    assert "Event futur" not in past_html


@pytest.mark.django_db
def test_agenda_in_progress_event_counts_as_upcoming(client):
    now = timezone.now()
    # Event en cours (commencé hier, finit demain) : « à venir » au sens is_past (ends_at).
    Event.objects.create(
        title="Festival en cours",
        starts_at=now - timedelta(days=1),
        ends_at=now + timedelta(days=1),
        status=PUBLISHED,
    )
    assert "Festival en cours" in client.get(reverse("agenda")).content.decode()
    past = client.get(reverse("agenda"), {"when": "past"}).content.decode()
    assert "Festival en cours" not in past


@pytest.mark.django_db
def test_event_detail_published_ok_draft_and_unknown_404(client):
    published = Event.objects.create(
        title="Soirée live", starts_at=timezone.now(), status=PUBLISHED
    )
    draft = Event.objects.create(title="Soirée secrète", starts_at=timezone.now())

    assert client.get(reverse("event-detail", args=[published.slug])).status_code == 200
    assert client.get(reverse("event-detail", args=[draft.slug])).status_code == 404
    assert client.get(reverse("event-detail", args=["slug-inexistant"])).status_code == 404


@pytest.mark.django_db
def test_actus_list_shows_published_hides_draft(client):
    News.objects.create(title="Actu publiée", status=PUBLISHED)
    News.objects.create(title="Actu brouillon")
    html = client.get(reverse("actus")).content.decode()
    assert "Actu publiée" in html
    assert "Actu brouillon" not in html


@pytest.mark.django_db
def test_news_detail_published_ok_draft_404(client):
    published = News.objects.create(title="Communiqué", status=PUBLISHED)
    draft = News.objects.create(title="Note interne")
    assert client.get(reverse("news-detail", args=[published.slug])).status_code == 200
    assert client.get(reverse("news-detail", args=[draft.slug])).status_code == 404


def test_plain_excerpt_strips_tags_and_decodes_entities():
    from apps.pages.templatetags.pages import plain_excerpt

    # Balises retirées + entités décodées (sinon « &amp; » double-échappé à l'affichage).
    out = plain_excerpt("<p>Théâtre de rue &amp; déambulation</p>")
    assert out == "Théâtre de rue & déambulation"


@pytest.mark.django_db
def test_get_absolute_url(client):
    event = Event.objects.create(title="Bal", starts_at=timezone.now(), status=PUBLISHED)
    news = News.objects.create(title="Brève", status=PUBLISHED)
    assert event.get_absolute_url() == reverse("event-detail", args=[event.slug])
    assert news.get_absolute_url() == reverse("news-detail", args=[news.slug])


# --- Pages fixes (P3.2) : câblage routes + gabarit 404 ---


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("route", "marker"),
    [
        ("asso", "432 Hz"),
        ("adherer", "Adhérer"),
        ("contact", "Contact"),
        ("mentions", "Mentions légales"),
    ],
)
def test_fixed_pages_return_200_with_heading(client, route, marker):
    response = client.get(reverse(route))
    assert response.status_code == 200
    assert marker in response.content.decode()


@pytest.mark.django_db
def test_unknown_url_renders_404_template(client):
    # Django sert templates/404.html dès que DEBUG=False (forcé en test).
    response = client.get("/cette-page-nexiste-pas/")
    assert response.status_code == 404
    assert "Hors fréquence" in response.content.decode()
