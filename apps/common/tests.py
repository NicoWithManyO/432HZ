import pytest
from django.utils import timezone

from apps.common.models import SlugHistory
from apps.events.models import Event


@pytest.mark.django_db
def test_no_history_on_creation():
    # Une création ne génère aucun historique (slug neuf, pas d'ancien).
    Event.objects.create(title="Concert", starts_at=timezone.now())
    assert SlugHistory.objects.count() == 0


@pytest.mark.django_db
def test_resave_without_slug_change_records_nothing():
    # Modifier le titre sans toucher au slug ne crée pas d'entrée.
    event = Event.objects.create(title="Concert", starts_at=timezone.now())
    event.title = "Concert modifié"
    event.save()
    assert SlugHistory.objects.count() == 0


@pytest.mark.django_db
def test_manual_slug_change_is_recorded():
    event = Event.objects.create(title="Concert", starts_at=timezone.now())
    old = event.slug
    event.slug = "nouveau-slug"
    event.save()
    entry = SlugHistory.objects.get(old_slug=old)
    assert entry.content_object == event


@pytest.mark.django_db
def test_blanked_slug_regenerated_is_recorded():
    # Champ slug vidé + titre changé → slug régénéré, l'ancien est historisé.
    event = Event.objects.create(title="Concert", starts_at=timezone.now())
    old = event.slug
    event.title = "Tout autre titre"
    event.slug = ""
    event.save()
    assert event.slug == "tout-autre-titre"
    assert SlugHistory.objects.filter(old_slug=old).exists()


@pytest.mark.django_db
def test_reverting_to_old_slug_purges_its_entry():
    # Revenir à un slug déjà historisé le rend de nouveau « vivant » → entrée purgée.
    event = Event.objects.create(title="Concert", starts_at=timezone.now())
    original = event.slug
    event.slug = "intermediaire"
    event.save()
    event.slug = original
    event.save()
    assert not SlugHistory.objects.filter(old_slug=original).exists()
    assert SlugHistory.objects.filter(old_slug="intermediaire").exists()
