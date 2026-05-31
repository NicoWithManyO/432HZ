import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_home_renders(client):
    """L'accueil répond 200 et étend le layout de base."""
    response = client.get(reverse("home"))
    assert response.status_code == 200
    assert b"432 Hz" in response.content
    assert b'class="waveform' in response.content
