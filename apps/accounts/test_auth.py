import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import EDITOR, Invitation, Profile

User = get_user_model()
PWD = "Vibrant-432hz!"


@pytest.mark.django_db
def test_accept_invitation_creates_validated_editor(client):
    invitation = Invitation.objects.create()
    url = reverse("gestion:accept-invitation", args=[invitation.token])

    response = client.post(url, {"username": "newbie", "password1": PWD, "password2": PWD})

    assert response.status_code == 302
    user = User.objects.get(username="newbie")
    assert user.profile.role == EDITOR
    assert user.profile.is_validated
    invitation.refresh_from_db()
    assert invitation.is_used


@pytest.mark.django_db
def test_invalid_invitation_is_rejected_and_creates_nothing(client):
    invitation = Invitation.objects.create(used_at=timezone.now())
    url = reverse("gestion:accept-invitation", args=[invitation.token])

    assert client.get(url).status_code == 410
    client.post(url, {"username": "ghost", "password1": PWD, "password2": PWD})
    assert not User.objects.filter(username="ghost").exists()


@pytest.mark.django_db
def test_unknown_token_is_rejected(client):
    assert client.get(reverse("gestion:accept-invitation", args=["nope"])).status_code == 410


@pytest.mark.django_db
def test_valid_invitation_renders_form(client):
    invitation = Invitation.objects.create()
    response = client.get(reverse("gestion:accept-invitation", args=[invitation.token]))
    assert response.status_code == 200
    assert b"password1" in response.content


def test_login_page_renders(client):
    assert client.get(reverse("gestion:login")).status_code == 200


@pytest.mark.django_db
def test_dashboard_redirects_anonymous_to_login(client):
    response = client.get(reverse("gestion:dashboard"))
    assert response.status_code == 302
    assert reverse("gestion:login") in response.url


@pytest.mark.django_db
def test_validated_user_reaches_dashboard(client):
    user = User.objects.create_user(username="ed", password=PWD)
    Profile.objects.create(user=user, role=EDITOR, is_validated=True)
    client.force_login(user)
    assert client.get(reverse("gestion:dashboard")).status_code == 200


@pytest.mark.django_db
def test_unvalidated_user_is_forbidden(client):
    user = User.objects.create_user(username="pending", password=PWD)
    Profile.objects.create(user=user, role=EDITOR, is_validated=False)
    client.force_login(user)
    assert client.get(reverse("gestion:dashboard")).status_code == 403


@pytest.mark.django_db
def test_invitation_cannot_be_reused(client):
    invitation = Invitation.objects.create()
    url = reverse("gestion:accept-invitation", args=[invitation.token])
    client.post(url, {"username": "first", "password1": PWD, "password2": PWD})

    # Le token est désormais consommé : une seconde acceptation est refusée.
    assert client.get(url).status_code == 410
    client.post(url, {"username": "second", "password1": PWD, "password2": PWD})
    assert not User.objects.filter(username="second").exists()
