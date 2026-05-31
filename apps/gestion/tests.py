from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Profile
from apps.common.models import PUBLISHED
from apps.events.models import Event
from apps.gestion.sanitize import clean_html


def test_clean_html_keeps_allowed_tags():
    html = "<p>Un <strong>concert</strong> et <a href='/x' title='x'>un lien</a>.</p>"
    cleaned = clean_html(html)
    assert "<strong>" in cleaned
    assert "<a " in cleaned and 'href="/x"' in cleaned


def test_clean_html_strips_disallowed_tags():
    cleaned = clean_html("<script>alert(1)</script><p>ok</p>")
    assert "<script>" not in cleaned
    assert "alert(1)" not in cleaned
    assert "<p>ok</p>" in cleaned


def test_clean_html_strips_disallowed_attributes():
    cleaned = clean_html('<p onclick="evil()" class="x">texte</p>')
    assert "onclick" not in cleaned
    assert "class" not in cleaned
    assert "texte" in cleaned


def test_clean_html_strips_image_tag():
    # img n'est pas dans l'allowlist (les médias passent par la galerie).
    cleaned = clean_html('<img src="x.jpg"><p>txt</p>')
    assert "<img" not in cleaned


# --- Vues events ---


@pytest.fixture
def validated_client(client):
    user = User.objects.create_user("editor", password="pw-test-1234")
    Profile.objects.create(user=user, is_validated=True)
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_event_list_requires_login(client):
    response = client.get(reverse("gestion:event-list"))
    assert response.status_code == 302  # anonyme → login


@pytest.mark.django_db
def test_event_list_forbidden_for_unvalidated(client):
    user = User.objects.create_user("pending", password="pw-test-1234")
    Profile.objects.create(user=user, is_validated=False)
    client.force_login(user)
    assert client.get(reverse("gestion:event-list")).status_code == 403


@pytest.mark.django_db
def test_event_create_sanitizes_description(validated_client):
    response = validated_client.post(
        reverse("gestion:event-create"),
        {
            "title": "Concert test",
            "slug": "",
            "kind": "",
            "starts_at": "2026-09-01T20:30",
            "ends_at": "",
            "location": "Le Brise-Glace",
            "price": "",
            "description": "<p>Top</p><script>alert(1)</script>",
            "cover": "",
        },
    )
    assert response.status_code == 302
    event = Event.objects.get(title="Concert test")
    assert "<script>" not in event.description
    assert "<p>Top</p>" in event.description
    assert event.status == "draft"  # créé en brouillon
    assert event.slug == "concert-test"  # slug auto


@pytest.mark.django_db
def test_event_publish_and_unpublish_views(validated_client):
    event = Event.objects.create(title="x", starts_at=timezone.now())
    validated_client.post(reverse("gestion:event-publish", args=[event.pk]))
    event.refresh_from_db()
    assert event.status == PUBLISHED and event.published_at is not None

    validated_client.post(reverse("gestion:event-unpublish", args=[event.pk]))
    event.refresh_from_db()
    assert event.status == "draft"


@pytest.mark.django_db
def test_event_list_filters(validated_client):
    now = timezone.now()
    Event.objects.create(title="à venir", starts_at=now + timedelta(days=3), status=PUBLISHED)
    Event.objects.create(title="passé", starts_at=now - timedelta(days=3), status=PUBLISHED)
    Event.objects.create(title="brouillon", starts_at=now + timedelta(days=1))

    def titles(filter_value):
        response = validated_client.get(reverse("gestion:event-list"), {"filter": filter_value})
        return {e.title for e in response.context["events"]}

    assert titles("upcoming") == {"à venir", "brouillon"}
    assert titles("past") == {"passé"}
    assert titles("drafts") == {"brouillon"}
    assert titles("all") == {"à venir", "passé", "brouillon"}
