from django.contrib.auth.forms import UserCreationForm


class InvitationAcceptForm(UserCreationForm):
    """Choix du nom d'utilisateur et du mot de passe à l'acceptation d'une invitation.

    Réutilise la validation de mot de passe de Django (AUTH_PASSWORD_VALIDATORS).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Django ≥ 5.1 ajoute un champ « usable_password » dont on n'a pas l'usage ici.
        self.fields.pop("usable_password", None)
