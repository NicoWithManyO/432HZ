"""Contrôles d'accès à la gestion : profil validé (owner/editor) et owner seul."""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


def is_validated(user):
    # Django (ModelBackend.get_user) anonymise déjà tout compte is_active=False au
    # chargement de session : un utilisateur inactif n'arrive jamais authentifié ici.
    return (
        user.is_authenticated
        and hasattr(user, "profile")
        and user.profile.is_validated
    )


def is_owner(user):
    return is_validated(user) and user.profile.is_owner


class ValidatedRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Réserve une vue aux profils validés (anonyme → login, connecté non autorisé → 403)."""

    login_url = "gestion:login"

    def test_func(self):
        return is_validated(self.request.user)


class OwnerRequiredMixin(ValidatedRequiredMixin):
    """Réserve une vue aux owners (gestion des comptes/invitations)."""

    def test_func(self):
        return is_owner(self.request.user)
