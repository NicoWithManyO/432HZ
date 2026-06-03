from django.db import migrations

# Reprise du bouton « Adhérer » aujourd'hui codé en dur dans le header (base.html) :
# après bascule vers les CTA pilotés en base, la barre de navigation reste identique.


def seed(apps, schema_editor):
    CallToAction = apps.get_model("pages", "CallToAction")
    CallToAction.objects.create(
        page="nav", label="Adhérer", url="/adherer/", variant="red", order=0
    )


def unseed(apps, schema_editor):
    apps.get_model("pages", "CallToAction").objects.filter(page="nav").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0011_alter_calltoaction_page"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
