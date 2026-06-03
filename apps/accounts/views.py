from django.contrib.auth import login
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django_ratelimit.decorators import ratelimit

from .forms import InvitationAcceptForm
from .models import EDITOR, Invitation, Profile

# Backend explicite : l'utilisateur fraîchement créé n'a pas d'attribut `backend`.
_AUTH_BACKEND = "django.contrib.auth.backends.ModelBackend"


# Throttle par IP : freine le martèlement de tokens d'invitation (création de compte).
@ratelimit(key="ip", rate="10/h", method="POST", block=True)
def accept_invitation(request, token):
    """Acceptation d'une invitation : crée un éditeur validé et le connecte."""
    invitation = Invitation.objects.filter(token=token).first()
    if invitation is None or not invitation.is_valid:
        return render(request, "gestion/invitation_invalid.html", status=410)

    if request.method == "POST":
        form = InvitationAcceptForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                # Consommation atomique : seule la 1re requête à passer used_at de
                # NULL → now() gagne, ce qui garantit l'usage unique même en cas de
                # double soumission concurrente (select_for_update indispo sur SQLite).
                consumed = Invitation.objects.filter(
                    pk=invitation.pk, used_at__isnull=True
                ).update(used_at=timezone.now())
                if not consumed:
                    return render(request, "gestion/invitation_invalid.html", status=410)
                user = form.save()
                Profile.objects.create(user=user, role=EDITOR, is_validated=True)
            login(request, user, backend=_AUTH_BACKEND)
            return redirect("gestion:dashboard")
    else:
        form = InvitationAcceptForm()

    return render(
        request,
        "gestion/invitation_accept.html",
        {"form": form, "invitation": invitation},
    )
