from datetime import datetime, time, timedelta

import pytest
from django.utils import timezone

from apps.common.models import DRAFT, PUBLISHED
from apps.events.models import Event


@pytest.mark.django_db
def test_slug_is_derived_from_title():
    event = Event.objects.create(title="Concert au Pâquier", starts_at=timezone.now())
    assert event.slug == "concert-au-paquier"


@pytest.mark.django_db
def test_description_sanitized_on_save():
    # Barrière XSS au niveau modèle : vaut quel que soit le chemin d'écriture (ici, ORM direct).
    event = Event.objects.create(
        title="x",
        starts_at=timezone.now(),
        description="<p>ok</p><script>alert(1)</script>",
    )
    assert "<script>" not in event.description
    assert "<p>ok</p>" in event.description


@pytest.mark.django_db
def test_slug_stays_unique_for_duplicate_titles():
    first = Event.objects.create(title="Même titre", starts_at=timezone.now())
    second = Event.objects.create(title="Même titre", starts_at=timezone.now())
    assert first.slug != second.slug
    assert second.slug.startswith("meme-titre")


@pytest.mark.django_db
def test_published_at_set_once_on_first_publish():
    event = Event.objects.create(title="x", starts_at=timezone.now())
    assert event.published_at is None

    event.status = PUBLISHED
    event.save()
    first_date = event.published_at
    assert first_date is not None

    # Dépublier puis republier ne réécrit pas la date d'origine.
    event.status = DRAFT
    event.save()
    event.status = PUBLISHED
    event.save()
    assert event.published_at == first_date


@pytest.mark.django_db
def test_published_at_persisted_with_restricted_update_fields():
    """Publier via save(update_fields=[...]) doit quand même écrire published_at."""
    event = Event.objects.create(title="maj partielle", starts_at=timezone.now())
    event.status = PUBLISHED
    event.save(update_fields=["status"])

    event.refresh_from_db()
    assert event.published_at is not None


@pytest.mark.django_db
def test_published_manager_filters_status():
    Event.objects.create(title="brouillon", starts_at=timezone.now())
    live = Event.objects.create(title="publié", starts_at=timezone.now(), status=PUBLISHED)
    assert list(Event.objects.published()) == [live]


@pytest.mark.django_db
def test_is_past_uses_end_then_start():
    now = timezone.now()
    past = Event.objects.create(title="passé", starts_at=now - timedelta(days=2))
    upcoming = Event.objects.create(title="à venir", starts_at=now + timedelta(days=2))
    assert past.is_past
    assert not upcoming.is_past


@pytest.mark.django_db
def test_event_on_its_day_counts_as_upcoming():
    # Le jour J, un event reste « à venir » toute la journée, même si son heure de début
    # est déjà passée : on compare la date locale, pas l'instant.
    today_early = timezone.make_aware(datetime.combine(timezone.localdate(), time(0, 1)))
    event = Event.objects.create(title="aujourd'hui", starts_at=today_early)
    assert not event.is_past
    assert event in Event.objects.upcoming()
    assert event not in Event.objects.past()


@pytest.mark.django_db
def test_event_the_day_before_counts_as_past():
    yesterday_late = timezone.make_aware(
        datetime.combine(timezone.localdate() - timedelta(days=1), time(23, 0))
    )
    event = Event.objects.create(title="hier", starts_at=yesterday_late)
    assert event.is_past
    assert event in Event.objects.past()
    assert event not in Event.objects.upcoming()


@pytest.mark.django_db
def test_publish_sets_status_and_date_once():
    event = Event.objects.create(title="x", starts_at=timezone.now())
    event.publish()
    event.refresh_from_db()
    assert event.status == PUBLISHED
    first_date = event.published_at
    assert first_date is not None

    # Dépublier puis republier conserve la date d'origine.
    event.unpublish()
    event.refresh_from_db()
    assert event.status == DRAFT
    event.publish()
    event.refresh_from_db()
    assert event.published_at == first_date
