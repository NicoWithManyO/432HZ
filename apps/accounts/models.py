"""Profils, invitations par token et verrou d'édition (cf cahier §5, §9).

L'auth s'appuie sur le User Django standard ; `Profile` (1-1) porte le rôle et la
validation. Pas d'inscription ouverte : les éditeurs sont créés via `Invitation`.
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import UUIDModel

OWNER = "owner"
EDITOR = "editor"
ROLE_CHOICES = [
    (OWNER, "Propriétaire"),
    (EDITOR, "Éditeur"),
]

INVITATION_TTL = timedelta(days=7)
EDIT_LOCK_TTL = timedelta(minutes=2)


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=EDITOR)
    is_validated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} ({self.role})"

    @property
    def is_owner(self):
        return self.role == OWNER


def _default_token():
    return secrets.token_urlsafe(32)


def _default_expiry():
    return timezone.now() + INVITATION_TTL


class Invitation(UUIDModel):
    """Jeton à usage unique créé par un owner ; consommé à l'acceptation."""

    token = models.CharField(max_length=64, unique=True, default=_default_token, editable=False)
    email = models.EmailField(blank=True, help_text="Indicatif (transmis hors-ligne en v1).")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="invitations_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=_default_expiry)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invitation {self.token[:8]}…"

    @property
    def is_used(self):
        return self.used_at is not None

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired

    def regenerate(self):
        """Réémet un jeton neuf et repousse l'expiration. Ne touche jamais à
        `used_at` : une invitation à usage unique consommée le reste (sinon le lien
        rouvrirait la création d'un nouveau compte)."""
        self.token = _default_token()
        self.expires_at = _default_expiry()
        self.save(update_fields=["token", "expires_at"])


class EditLock(UUIDModel):
    """Verrou d'édition pessimiste (confort) : actif tant que le heartbeat est récent."""

    object_type = models.CharField(max_length=10, choices=[("event", "Event"), ("news", "News")])
    object_id = models.UUIDField()
    holder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="edit_locks",
    )
    acquired_at = models.DateTimeField(auto_now_add=True)
    heartbeat_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["object_type", "object_id"], name="unique_lock_per_object"
            ),
        ]

    def __str__(self):
        return f"{self.object_type}:{self.object_id} → {self.holder}"

    @property
    def is_active(self):
        return timezone.now() - self.heartbeat_at < EDIT_LOCK_TTL
