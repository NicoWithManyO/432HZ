import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError


@pytest.mark.django_db
def test_bootstrap_owner_creates_superuser():
    call_command(
        "bootstrap_owner",
        username="nico",
        email="nico@example.com",
        password="s3cret-pass!",
    )

    user = get_user_model().objects.get(username="nico")
    assert user.is_superuser
    assert user.is_staff
    assert user.check_password("s3cret-pass!")


@pytest.mark.django_db
def test_bootstrap_owner_refuses_existing_username():
    get_user_model().objects.create_user(username="nico", password="x")

    with pytest.raises(CommandError):
        call_command("bootstrap_owner", username="nico", password="other")


@pytest.mark.django_db
def test_bootstrap_owner_rejects_weak_password():
    """create_superuser ne valide pas le mot de passe : la commande doit s'en charger."""
    with pytest.raises(CommandError):
        call_command("bootstrap_owner", username="nico", password="123")

    assert not get_user_model().objects.filter(username="nico").exists()
