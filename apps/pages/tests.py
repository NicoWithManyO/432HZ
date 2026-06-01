import pytest
from django.urls import reverse

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
