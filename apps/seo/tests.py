from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.common.models import PUBLISHED
from apps.events.models import Event
from apps.media.models import Image
from apps.media.tests import make_image_file
from apps.news.models import News

# --- sitemap.xml ---


@pytest.mark.django_db
def test_sitemap_returns_xml(client):
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert "xml" in response["Content-Type"]


@pytest.mark.django_db
def test_sitemap_lists_published_only(client):
    soon = timezone.now() + timedelta(days=5)
    pub_event = Event.objects.create(title="Event publié", starts_at=soon, status=PUBLISHED)
    Event.objects.create(title="Event brouillon", starts_at=soon)
    pub_news = News.objects.create(title="Actu publiée", status=PUBLISHED)
    News.objects.create(title="Actu brouillon")

    body = client.get("/sitemap.xml").content.decode()
    assert pub_event.get_absolute_url() in body
    assert pub_news.get_absolute_url() in body
    assert "event-brouillon" not in body
    assert "actu-brouillon" not in body


@pytest.mark.django_db
def test_sitemap_includes_static_pages(client):
    body = client.get("/sitemap.xml").content.decode()
    for name in ("home", "agenda", "actus", "asso", "adherer", "contact", "mentions"):
        assert reverse(name) in body


@pytest.mark.django_db
def test_sitemap_urls_are_absolute(client):
    # Le domaine vient du host de la requête (RequestSite), pas d'une config.
    body = client.get("/sitemap.xml").content.decode()
    assert "<loc>http://testserver/" in body


@pytest.mark.django_db
def test_sitemap_no_n_plus_one(client, django_assert_max_num_queries):
    soon = timezone.now() + timedelta(days=5)
    for i in range(5):
        Event.objects.create(title=f"Event {i}", starts_at=soon, status=PUBLISHED)
        News.objects.create(title=f"Actu {i}", status=PUBLISHED)
    # 2 sitemaps dynamiques × (count + page) = 4 requêtes ; constant quel que soit le nombre.
    with django_assert_max_num_queries(6):
        client.get("/sitemap.xml")


# --- robots.txt ---


def test_robots_is_plain_text(client):
    response = client.get("/robots.txt")
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/plain")


def test_robots_disallows_backoffice(client):
    body = client.get("/robots.txt").content.decode()
    assert "Disallow: /gestion/" in body
    assert "Disallow: /django-admin/" in body


def test_robots_points_to_sitemap(client):
    body = client.get("/robots.txt").content.decode()
    assert "Sitemap: http://testserver/sitemap.xml" in body


# --- JSON-LD ---


@pytest.mark.django_db
def test_event_detail_has_event_jsonld(client):
    event = Event.objects.create(
        title="Concert au lac",
        starts_at=timezone.now() + timedelta(days=3),
        location="Pâquier, Annecy",
        status=PUBLISHED,
    )
    body = client.get(event.get_absolute_url()).content.decode()
    assert 'type="application/ld+json"' in body
    assert '"@type": "Event"' in body
    assert '"Concert au lac"' in body
    # Date au format ISO (présence du séparateur T).
    assert '"startDate": "' in body and "T" in body


@pytest.mark.django_db
def test_event_jsonld_escapes_dangerous_title(client):
    # Le filtre ld_json neutralise toute injection : `<` devient <, pas de balise vivante.
    event = Event.objects.create(
        title="</script><script>alert(1)</script> & co",
        starts_at=timezone.now() + timedelta(days=3),
        status=PUBLISHED,
    )
    body = client.get(event.get_absolute_url()).content.decode()
    assert "<script>alert(1)</script>" not in body
    assert "\\u003C" in body  # le `<` du titre a été échappé


@pytest.mark.django_db
def test_organization_jsonld_on_home(client):
    body = client.get(reverse("home")).content.decode()
    assert 'id="org-jsonld"' in body
    assert '"@type": "Organization"' in body
    assert '"432 Hz"' in body


# --- Open Graph / canonical ---


@pytest.mark.django_db
def test_event_detail_og_image_absolute_from_cover(client, settings, tmp_path):
    # MEDIA_ROOT en tmp : la vignette `og` est générée hors du dépôt.
    settings.MEDIA_ROOT = str(tmp_path)
    cover = Image.objects.create(alt="Affiche", file=make_image_file())
    event = Event.objects.create(
        title="Soirée live",
        starts_at=timezone.now() + timedelta(days=3),
        cover=cover,
        status=PUBLISHED,
    )
    body = client.get(event.get_absolute_url()).content.decode()
    assert '<meta property="og:image" content="http://testserver/media/' in body


@pytest.mark.django_db
def test_event_detail_og_type_article_and_published_time(client):
    event = Event.objects.create(
        title="Spectacle", starts_at=timezone.now() + timedelta(days=3), status=PUBLISHED
    )
    body = client.get(event.get_absolute_url()).content.decode()
    assert '<meta property="og:type" content="article">' in body
    assert '<meta property="article:published_time" content="' in body


@pytest.mark.django_db
def test_detail_meta_description_reuses_excerpt(client):
    # La meta description du détail et og:description partagent la même source (DRY).
    event = Event.objects.create(
        title="Bal",
        starts_at=timezone.now() + timedelta(days=3),
        description="<p>Une grande fête populaire au bord du lac.</p>",
        status=PUBLISHED,
    )
    body = client.get(event.get_absolute_url()).content.decode()
    assert 'name="description" content="Une grande fête populaire au bord du lac."' in body


@pytest.mark.django_db
def test_detail_blank_html_description_falls_back(client):
    # Description HTML sans texte rendu (ex. <p></p>) → pas de description vide :
    # on retombe sur la description par défaut du site.
    event = Event.objects.create(
        title="Sans texte",
        starts_at=timezone.now() + timedelta(days=3),
        description="<p></p>",
        status=PUBLISHED,
    )
    body = client.get(event.get_absolute_url()).content.decode()
    assert '<meta property="og:description" content="">' not in body
    assert '<meta name="description" content="">' not in body
    assert "association culturelle à Annecy" in body


@pytest.mark.django_db
def test_canonical_strips_query_string(client):
    response = client.get(reverse("asso"), {"foo": "bar"})
    body = response.content.decode()
    assert '<link rel="canonical" href="http://testserver/asso/">' in body
    assert "foo=bar" not in body.split("</head>")[0]


@pytest.mark.django_db
def test_static_page_defaults_to_website_og(client):
    body = client.get(reverse("asso")).content.decode()
    assert '<meta property="og:type" content="website">' in body
    assert 'logo-432hz' in body


@pytest.mark.django_db
def test_home_overrides_title_and_description(client):
    body = client.get(reverse("home")).content.decode()
    assert "Spectacle vivant &amp; culture à Annecy" in body
    assert 'name="description" content="432 Hz, association culturelle annécienne' in body


# --- 404 ---


@pytest.mark.django_db
def test_404_is_noindex(client):
    body = client.get("/page-inexistante/").content.decode()
    assert '<meta name="robots" content="noindex">' in body
