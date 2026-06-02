from django.db import migrations

# Reprise des contenus aujourd'hui codés en dur (mentions_legales.html) : après bascule,
# le rendu public ne change pas (placeholders légaux « — » conservés tels quels).
# NB : la section « Éditeur » passe de `<br>` à des `<p>` séparés car le sanitizer
# (apps/common/sanitize.py) n'autorise pas `<br>` → un seed avec `<br>` serait strippé
# à la première édition. Rendu visuel quasi identique en `.prose`.
MENTIONS = {
    "kicker": "Informations légales",
    "title": "Mentions légales & confidentialité",
    "editor_html": (
        "<p>Association 432 Hz — association loi 1901.</p>"
        "<p>Adresse : Annecy, Haute-Savoie.</p>"
        "<p>SIRET : —</p>"
        "<p>Directeur·rice de la publication : —</p>"
        "<p>Contact : <a href=\"mailto:contact@432hz.fr\">contact@432hz.fr</a></p>"
    ),
    "hosting_html": "<p>—</p>",
    "intellectual_property_html": (
        "<p>Les contenus de ce site (textes, visuels, logo) sont la propriété de "
        "l'association 432 Hz, sauf mention contraire. Toute reproduction sans "
        "autorisation est interdite.</p>"
    ),
    "privacy_html": (
        "<p>Ce site mesure son audience avec <strong>Plausible</strong>, une solution "
        "d'analyse respectueuse de la vie privée : aucun cookie n'est déposé et aucune "
        "donnée personnelle n'est collectée ni revendue.</p>"
        "<p>Les contenus tiers (formulaire d'adhésion HelloAsso, lecteurs audio…) ne sont "
        "chargés qu'après une action explicite de votre part (« click-to-load ») : aucun "
        "appel n'est fait à ces services tant que vous ne le demandez pas.</p>"
    ),
}


def seed(apps, schema_editor):
    apps.get_model("pages", "MentionsContent").objects.create(**MENTIONS)


def unseed(apps, schema_editor):
    apps.get_model("pages", "MentionsContent").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0008_mentionscontent"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
