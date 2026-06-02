from django.db import migrations

# Reprise à l'identique des contenus aujourd'hui codés en dur (asso.html, hero de home.html) :
# après bascule, le rendu public ne change pas.
ASSO = {
    "kicker": "L'association",
    "title": "432 Hz",
    "manifesto": (
        "<p>432 Hz est une association culturelle annécienne née en 2021. On fait vibrer "
        "le spectacle vivant : concerts, performances, fêtes de quartier — des rendez-vous "
        "accessibles, fabriqués avec et pour les gens d'ici.</p>"
        "<p>Notre conviction : la culture se vit ensemble, dans la rue comme sur scène. On "
        "rassemble artistes, bénévoles et habitant·es autour d'une programmation exigeante "
        "et joyeuse.</p>"
    ),
    "missions_kicker": "Nos missions",
    "missions_title": "Ce qu'on défend",
}

KEY_FIGURES = [
    "81 adhérent·e·s",
    "22 bénévoles",
    "Depuis 2021",
]

MISSIONS = [
    (
        "Le spectacle vivant",
        "Promouvoir et diffuser le spectacle vivant sous toutes ses formes : musique, "
        "performance, arts de la rue.",
    ),
    (
        "Les manifestations",
        "Organiser concerts, fêtes de quartier et événements culturels qui font vivre "
        "l'espace public.",
    ),
    (
        "L'éducatif & le préventif",
        "Mener des actions éducatives et de prévention autour de la pratique culturelle "
        "et de la fête responsable.",
    ),
]

# (page, label, url, variant) — ordre = position dans la liste.
CTAS = [
    ("home", "Rejoindre l'asso", "/adherer/", "red"),
    ("home", "Voir l'agenda →", "/agenda/", "ghost"),
    ("asso", "Rejoindre l'asso", "/adherer/", "red"),
]


def seed(apps, schema_editor):
    AssoContent = apps.get_model("pages", "AssoContent")
    KeyFigure = apps.get_model("pages", "KeyFigure")
    Mission = apps.get_model("pages", "Mission")
    CallToAction = apps.get_model("pages", "CallToAction")
    AssoContent.objects.create(**ASSO)
    for order, text in enumerate(KEY_FIGURES):
        KeyFigure.objects.create(text=text, order=order)
    for order, (title, description) in enumerate(MISSIONS):
        Mission.objects.create(title=title, description=description, order=order)
    # L'ordre repart à 0 par page (champ `order` scopé par `page`).
    counters = {}
    for page, label, url, variant in CTAS:
        order = counters.get(page, 0)
        CallToAction.objects.create(
            page=page, label=label, url=url, variant=variant, order=order
        )
        counters[page] = order + 1


def unseed(apps, schema_editor):
    apps.get_model("pages", "AssoContent").objects.all().delete()
    apps.get_model("pages", "KeyFigure").objects.all().delete()
    apps.get_model("pages", "Mission").objects.all().delete()
    apps.get_model("pages", "CallToAction").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0003_assocontent_calltoaction_keyfigure_mission"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
