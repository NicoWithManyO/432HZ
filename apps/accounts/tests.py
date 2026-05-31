import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone
from django.utils.crypto import get_random_string

from apps.accounts.models import OWNER, EditLock, Invitation, Profile

# Mot de passe de test généré à l'exécution (aucun littéral type secret dans le dépôt).
PASSWORD = get_random_string(12)


@pytest.mark.django_db
def test_bootstrap_owner_creates_superuser():
    call_command(
        "bootstrap_owner",
        username="nico",
        email="nico@example.com",
        password=PASSWORD,
    )

    user = get_user_model().objects.get(username="nico")
    assert user.is_superuser
    assert user.is_staff
    assert user.check_password(PASSWORD)
    assert user.profile.role == OWNER
    assert user.profile.is_validated


@pytest.mark.django_db
def test_bootstrap_owner_refuses_existing_username():
    get_user_model().objects.create_user(username="nico", password=PASSWORD)

    with pytest.raises(CommandError):
        call_command("bootstrap_owner", username="nico", password=PASSWORD)


@pytest.mark.django_db
def test_bootstrap_owner_rejects_weak_password():
    """create_superuser ne valide pas le mot de passe : la commande doit s'en charger."""
    with pytest.raises(CommandError):
        call_command("bootstrap_owner", username="nico", password="123")

    assert not get_user_model().objects.filter(username="nico").exists()


@pytest.mark.django_db
def test_profile_is_owner():
    user = get_user_model().objects.create_user(username="o", password=PASSWORD)
    profile = Profile.objects.create(user=user, role=OWNER, is_validated=True)
    assert profile.is_owner


@pytest.mark.django_db
def test_invitation_token_is_generated_and_unique():
    a = Invitation.objects.create()
    b = Invitation.objects.create()
    assert a.token and b.token
    assert a.token != b.token


@pytest.mark.django_db
def test_invitation_validity_states():
    fresh = Invitation.objects.create()
    assert fresh.is_valid

    used = Invitation.objects.create(used_at=timezone.now())
    assert not used.is_valid

    expired = Invitation.objects.create(expires_at=timezone.now() - timedelta(days=1))
    assert expired.is_expired
    assert not expired.is_valid


@pytest.mark.django_db
def test_invitation_regenerate_renews_token_and_expiry():
    # Invitation expirée mais jamais consommée : régénérer la rend de nouveau valable.
    inv = Invitation.objects.create(expires_at=timezone.now() - timedelta(days=1))
    old_token = inv.token
    inv.regenerate()
    inv.refresh_from_db()
    assert inv.token != old_token
    assert inv.is_valid


@pytest.mark.django_db
def test_invitation_regenerate_does_not_resurrect_used():
    # Garde-fou sécurité : une invitation à usage unique consommée le reste.
    inv = Invitation.objects.create(used_at=timezone.now())
    inv.regenerate()
    inv.refresh_from_db()
    assert inv.is_used
    assert not inv.is_valid


@pytest.mark.django_db
def test_edit_lock_is_active_while_heartbeat_recent():
    user = get_user_model().objects.create_user(username="h", password=PASSWORD)
    lock = EditLock.objects.create(object_type="event", object_id=uuid.uuid4(), holder=user)
    assert lock.is_active

    # Heartbeat ancien (> 2 min) → verrou considéré relâché.
    lock.heartbeat_at = timezone.now() - timedelta(minutes=5)
    assert not lock.is_active
