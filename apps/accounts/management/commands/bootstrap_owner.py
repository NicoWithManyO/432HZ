"""Crée le compte propriétaire fondateur (premier accès à la gestion).

Pas d'inscription ouverte sur le site : le premier compte est amorcé ici, puis les
éditeurs sont créés par invitation (cf cahier §9). Ce compte est un superuser Django
doté d'un `Profile` de rôle `owner`, validé.

Usage :
    python manage.py bootstrap_owner --username nico --email nico@example.com
Le mot de passe est demandé de façon masquée s'il n'est pas fourni via --password.
"""

from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import OWNER, Profile


class Command(BaseCommand):
    help = "Crée le compte propriétaire fondateur (superuser)."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--email", default="")
        parser.add_argument(
            "--password",
            default=None,
            help="Mot de passe (sinon demandé de façon masquée).",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]

        if User.objects.filter(username=username).exists():
            raise CommandError(f"L'utilisateur « {username} » existe déjà.")

        password = options["password"]
        if not password:
            password = getpass("Mot de passe : ")
            if password != getpass("Confirmation : "):
                raise CommandError("Les mots de passe ne correspondent pas.")

        # create_superuser ne déclenche pas AUTH_PASSWORD_VALIDATORS : on valide à la main.
        try:
            validate_password(password)
        except ValidationError as error:
            raise CommandError("\n".join(error.messages)) from error

        # User + Profile en une seule transaction : pas de superuser orphelin (sans
        # Profile, il serait verrouillé hors de /gestion/ et impossible à relancer).
        with transaction.atomic():
            user = User.objects.create_superuser(
                username=username,
                email=options["email"],
                password=password,
            )
            Profile.objects.create(user=user, role=OWNER, is_validated=True)
        self.stdout.write(self.style.SUCCESS(f"Propriétaire « {username} » créé."))
