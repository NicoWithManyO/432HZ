from django.db import migrations

# Reprise à l'identique des contenus aujourd'hui codés en dur (contact.html) :
# après bascule, le rendu public ne change pas.
CONTACT = {
    "kicker": "Nous écrire",
    "title": "Contact",
    "intro": (
        "<p>Une question, une proposition de collaboration, l'envie de filer un coup de "
        "main ? Écris-nous, on répond à toutes et tous.</p>"
    ),
    "coordinates_title": "Coordonnées",
    "email": "contact@432hz.fr",
    "address": "Annecy, Haute-Savoie",
    "networks_title": "Réseaux",
}

# (label, url) — ordre = position dans la liste.
SOCIAL_LINKS = [
    ("Instagram", "https://www.instagram.com/"),
    ("Facebook", "https://www.facebook.com/"),
    ("SoundCloud", "https://soundcloud.com/"),
]


def seed(apps, schema_editor):
    ContactContent = apps.get_model("pages", "ContactContent")
    SocialLink = apps.get_model("pages", "SocialLink")
    ContactContent.objects.create(**CONTACT)
    for order, (label, url) in enumerate(SOCIAL_LINKS):
        SocialLink.objects.create(label=label, url=url, order=order)


def unseed(apps, schema_editor):
    apps.get_model("pages", "ContactContent").objects.all().delete()
    apps.get_model("pages", "SocialLink").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0005_contactcontent_sociallink"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
