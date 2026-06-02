from datetime import timedelta
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from apps.common.models import DRAFT, PUBLISHED
from apps.events.models import Event
from apps.news.models import News
from apps.pages.models import CallToAction, HomeContent, SocialLink, TickerItem
from apps.pages.punchline import render_punchline


def test_no_multiline_django_comments():
    """Garde-fou : un commentaire `{# … #}` Django ne tient QUE sur une ligne. Étalé sur
    plusieurs lignes, il est rendu littéralement (et exécute les tags internes). Pour tout
    commentaire multi-ligne, utiliser `{% comment %}…{% endcomment %}`."""
    root = Path(settings.BASE_DIR)
    offenders = []
    for template in root.glob("**/*.html"):
        if any(part in {".venv", "node_modules", "staticfiles"} for part in template.parts):
            continue
        for lineno, line in enumerate(template.read_text(encoding="utf-8").splitlines(), 1):
            idx = line.find("{#")
            # `{#` ouvert sans `#}` fermant après lui sur la même ligne → commentaire multi-ligne.
            if idx != -1 and "#}" not in line[idx:]:
                offenders.append(f"{template.relative_to(root)}:{lineno}")
    assert not offenders, (
        "Commentaire {# #} multi-ligne détecté (utiliser {% comment %}) : " + ", ".join(offenders)
    )


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


# --- Redirection 301 sur changement de slug (P4.2) ---


@pytest.mark.django_db
def test_old_event_slug_redirects_permanently(client):
    event = Event.objects.create(title="Concert", starts_at=timezone.now(), status=PUBLISHED)
    old_slug = event.slug
    event.slug = "concert-renomme"
    event.save()

    response = client.get(reverse("event-detail", args=[old_slug]))
    assert response.status_code == 301
    assert response["Location"] == event.get_absolute_url()


@pytest.mark.django_db
def test_old_news_slug_redirects_permanently(client):
    news = News.objects.create(title="Communiqué", status=PUBLISHED)
    old_slug = news.slug
    news.slug = "communique-corrige"
    news.save()

    response = client.get(reverse("news-detail", args=[old_slug]))
    assert response.status_code == 301
    assert response["Location"] == news.get_absolute_url()


@pytest.mark.django_db
def test_unknown_slug_still_404(client):
    # Un slug jamais utilisé n'a pas d'historique → 404, pas de redirection.
    assert client.get(reverse("event-detail", args=["jamais-vu"])).status_code == 404


@pytest.mark.django_db
def test_old_slug_of_unpublished_target_404(client):
    # Cible repassée en brouillon : l'ancien slug ne redirige pas (cohérent avec l'URL courante).
    event = Event.objects.create(title="Concert", starts_at=timezone.now(), status=PUBLISHED)
    old_slug = event.slug
    event.slug = "concert-renomme"
    event.status = DRAFT
    event.save()
    assert client.get(reverse("event-detail", args=[old_slug])).status_code == 404


@pytest.mark.django_db
def test_old_slug_redirect_isolated_per_model(client):
    # L'ancien slug d'un event ne déclenche pas de redirection sur l'URL d'actu.
    event = Event.objects.create(title="Concert", starts_at=timezone.now(), status=PUBLISHED)
    old_slug = event.slug
    event.slug = "concert-renomme"
    event.save()
    assert client.get(reverse("news-detail", args=[old_slug])).status_code == 404


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


# --- Accueil enrichi (P3.3) : feature « à la une », grilles, états vides ---


@pytest.mark.django_db
def test_home_featured_defaults_to_nearest_upcoming(client):
    near = timezone.now() + timedelta(days=2)
    far = timezone.now() + timedelta(days=20)
    nearest = Event.objects.create(title="Le plus proche", starts_at=near, status=PUBLISHED)
    Event.objects.create(title="Le plus lointain", starts_at=far, status=PUBLISHED)
    # Aucun event coché « à la une » → la vedette est le prochain event.
    context = client.get(reverse("home")).context
    assert context["featured_event"] == nearest
    # La vedette n'est pas dupliquée dans la grille des suivants.
    assert nearest not in context["upcoming_events"]


@pytest.mark.django_db
def test_home_featured_prefers_flagged_event(client):
    near = timezone.now() + timedelta(days=2)
    far = timezone.now() + timedelta(days=20)
    Event.objects.create(title="Le plus proche", starts_at=near, status=PUBLISHED)
    flagged = Event.objects.create(
        title="La une choisie", starts_at=far, status=PUBLISHED, is_featured=True
    )
    # Un event coché « à la une » prime sur le plus proche.
    assert client.get(reverse("home")).context["featured_event"] == flagged


@pytest.mark.django_db
def test_home_hides_draft_and_past_from_upcoming(client):
    soon = timezone.now() + timedelta(days=5)
    past = timezone.now() - timedelta(days=5)
    Event.objects.create(title="À venir publié", starts_at=soon, status=PUBLISHED)
    Event.objects.create(title="À venir brouillon", starts_at=soon)
    Event.objects.create(title="Déjà passé", starts_at=past, status=PUBLISHED)

    html = client.get(reverse("home")).content.decode()
    assert "À venir publié" in html
    assert "À venir brouillon" not in html
    # Ni le brouillon ni le passé n'apparaissent dans « à l'affiche ».
    context = client.get(reverse("home")).context
    assert all(e.title != "Déjà passé" for e in context["upcoming_events"])
    assert context["featured_event"].title == "À venir publié"
    assert "Déjà passé" not in html


@pytest.mark.django_db
def test_home_lists_recent_published_news(client):
    News.objects.create(title="Actu en home", status=PUBLISHED)
    News.objects.create(title="Actu cachée")
    html = client.get(reverse("home")).content.decode()
    assert "Actu en home" in html
    assert "Actu cachée" not in html


@pytest.mark.django_db
def test_home_empty_states_render_without_content(client):
    Event.objects.all().delete()
    News.objects.all().delete()
    response = client.get(reverse("home"))
    assert response.status_code == 200
    html = response.content.decode()
    assert response.context["featured_event"] is None
    # Les sections restent visibles avec un message d'état vide à la charte.
    assert "Rien à l'affiche pour l'instant" in html
    assert "Aucune actu pour le moment" in html


@pytest.mark.django_db
def test_home_renders_section_headings(client):
    html = client.get(reverse("home")).content.decode()
    for heading in ("À l'affiche", "Actus"):
        assert heading in html


@pytest.mark.django_db
def test_home_hero_renders_configured_buttons(client):
    # Le hero reprend les 2 boutons du seed, avec leur style (rouge / ghost) et destination.
    html = client.get(reverse("home")).content.decode()
    assert '<a href="/adherer/" class="btn btn--red">Rejoindre l&#x27;asso</a>' in html
    assert '<a href="/agenda/" class="btn btn--ghost">Voir l&#x27;agenda →</a>' in html


@pytest.mark.django_db
def test_home_hero_buttons_are_free(client):
    # Boutons libres : on peut tout supprimer (hero sans bouton, sans casser la page).
    CallToAction.objects.filter(page=CallToAction.HOME).delete()
    response = client.get(reverse("home"))
    assert response.status_code == 200
    assert "Voir l&#x27;agenda" not in response.content.decode()


# --- Accueil : nombre d'events/actus affichés configurable (HomeContent) ---


@pytest.mark.django_db
def test_home_content_has_default_counts():
    # Le seed pose la ligne ; les nouveaux champs prennent les défauts du modèle (3 / 4).
    home = HomeContent.load()
    assert home.events_count == 3
    assert home.news_count == 4


@pytest.mark.django_db
def test_home_respects_configured_events_count(client):
    now = timezone.now()
    for i in range(5):
        Event.objects.create(
            title=f"Event {i}", starts_at=now + timedelta(days=i + 1), status=PUBLISHED
        )
    home = HomeContent.load()
    home.events_count = 2
    home.save()
    # Vedette à part : la grille des suivants est limitée au nombre configuré.
    context = client.get(reverse("home")).context
    assert len(context["upcoming_events"]) == 2


@pytest.mark.django_db
def test_home_respects_configured_news_count(client):
    for i in range(5):
        News.objects.create(title=f"Actu {i}", status=PUBLISHED)
    home = HomeContent.load()
    home.news_count = 2
    home.save()
    assert len(client.get(reverse("home")).context["recent_news"]) == 2


@pytest.mark.django_db
def test_home_zero_events_count_keeps_featured(client):
    now = timezone.now()
    featured = Event.objects.create(
        title="La une", starts_at=now + timedelta(days=1), status=PUBLISHED
    )
    Event.objects.create(title="Suivant", starts_at=now + timedelta(days=2), status=PUBLISHED)
    home = HomeContent.load()
    home.events_count = 0
    home.save()
    context = client.get(reverse("home")).context
    # La vedette reste indépendante du compteur ; seule la grille des suivants disparaît.
    assert context["featured_event"] == featured
    assert context["upcoming_events"] == []


@pytest.mark.django_db
def test_home_zero_news_count_hides_actus_section(client):
    News.objects.create(title="Actu masquée", status=PUBLISHED)
    home = HomeContent.load()
    home.news_count = 0
    home.save()
    html = client.get(reverse("home")).content.decode()
    # Compteur à 0 ⇒ toute la section Actus disparaît (ni titre, ni état vide).
    assert 'id="actus"' not in html
    assert "Actu masquée" not in html
    assert "Aucune actu pour le moment" not in html


@pytest.mark.django_db
def test_asso_page_renders_seeded_content(client):
    # Après bascule template→base : le rendu reprend mot pour mot les textes d'origine.
    html = client.get(reverse("asso")).content.decode()
    assert "L&#x27;association" in html  # kicker (apostrophe échappée)
    assert "432 Hz est une association culturelle annécienne née en 2021" in html
    assert "Ce qu&#x27;on défend" in html
    # Les 3 chiffres-clés et les 3 missions numérotées.
    assert "81 adhérent·e·s" in html
    assert "Depuis 2021" in html
    assert "Le spectacle vivant" in html
    assert "Les manifestations" in html
    assert ">01<" in html and ">02<" in html and ">03<" in html
    # CTA toujours présent, pointant vers la destination configurée (Adhérer par défaut).
    assert "Rejoindre l&#x27;asso" in html
    assert 'href="/adherer/"' in html


@pytest.mark.django_db
def test_contact_page_renders_seeded_content(client):
    # Après bascule template→base : le rendu reprend mot pour mot les textes d'origine.
    response = client.get(reverse("contact"))
    html = response.content.decode()
    assert "Nous écrire" in html  # kicker
    assert "Une question, une proposition de collaboration" in html
    assert 'href="mailto:contact@432hz.fr"' in html
    assert "Annecy, Haute-Savoie" in html
    # Les 3 réseaux seedés (cochés « afficher sur la page » par défaut).
    labels = [link.label for link in response.context["social_links"]]
    assert labels == ["Instagram", "Facebook", "SoundCloud"]


@pytest.mark.django_db
def test_contact_social_links_are_free(client):
    # Liste libre : on peut tout supprimer (bloc réseaux vide sans casser la page).
    SocialLink.objects.all().delete()
    response = client.get(reverse("contact"))
    assert response.status_code == 200
    assert list(response.context["social_links"]) == []


@pytest.mark.django_db
def test_social_link_page_and_footer_toggles_are_independent(client):
    # Chaque réseau s'affiche indépendamment sur la page Contact et/ou dans le footer.
    SocialLink.objects.all().delete()
    SocialLink.objects.create(label="PageOnly", url="https://p.test/", show_in_footer=False)
    SocialLink.objects.create(label="FooterOnly", url="https://f.test/", show_on_page=False)
    SocialLink.objects.create(label="Both", url="https://b.test/")

    # Page Contact : seuls show_on_page=True (PageOnly + Both).
    page_labels = [link.label for link in client.get(reverse("contact")).context["social_links"]]
    assert page_labels == ["PageOnly", "Both"]

    # Footer (site-wide via context processor) : seuls show_in_footer=True (FooterOnly + Both).
    footer_html = client.get(reverse("home")).content.decode()
    assert "https://f.test/" in footer_html
    assert "https://b.test/" in footer_html
    assert "https://p.test/" not in footer_html


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.instagram.com/432hz", "instagram"),
        ("https://instagram.com/432hz", "instagram"),
        ("https://facebook.com/432hz", "facebook"),
        ("https://soundcloud.com/432hz", "soundcloud"),
        ("https://www.youtube.com/@432hz", "youtube"),
        ("https://youtu.be/abc", "youtube"),
        ("https://twitter.com/432hz", "x"),
        ("https://x.com/432hz", "x"),
        ("https://www.tiktok.com/@432hz", "tiktok"),
        ("https://432hz.bandcamp.com/", "bandcamp"),  # sous-domaine
        ("https://open.spotify.com/artist/abc", "spotify"),  # sous-domaine
        ("https://www.linkedin.com/company/432hz", "linkedin"),
        ("https://example.com/whatever", "link"),  # inconnu → repli
        ("", "link"),  # url vide → repli
    ],
)
def test_social_link_icon_slug_from_domain(url, expected):
    # L'icône est déduite du domaine de l'URL (sous-domaines inclus), repli « link ».
    assert SocialLink(label="x", url=url).icon == expected


@pytest.mark.django_db
def test_social_links_render_icon_sprite_reference(client):
    # L'icône locale est rendue via <use href="#i-<slug>"> sur la page Contact et dans le footer.
    SocialLink.objects.all().delete()
    SocialLink.objects.create(label="Insta", url="https://instagram.com/432hz")
    SocialLink.objects.create(label="Perso", url="https://example.com/")  # inconnu → repli

    contact_html = client.get(reverse("contact")).content.decode()
    assert 'href="#i-instagram"' in contact_html
    assert 'href="#i-link"' in contact_html  # repli domaine inconnu
    assert 'id="i-instagram"' in contact_html  # sprite inclus une fois via base.html

    footer_html = client.get(reverse("home")).content.decode()
    assert 'href="#i-instagram"' in footer_html


@pytest.mark.django_db
def test_mentions_page_renders_seeded_content(client):
    # Après bascule template→base : le rendu reprend les textes d'origine + les titres
    # de section figés au template.
    response = client.get(reverse("mentions"))
    html = response.content.decode()
    assert "Informations légales" in html  # kicker
    # Titres de section (figés au template, pas en base).
    for section in (
        "Éditeur du site", "Hébergement", "Propriété intellectuelle", "Confidentialité",
    ):
        assert section in html
    # Contenu éditable seedé verbatim.
    assert "association loi 1901" in html
    assert 'href="mailto:contact@432hz.fr"' in html
    assert "<strong>Plausible</strong>" in html
    assert "click-to-load" in html
