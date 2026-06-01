from django.db import migrations

# Reprise à l'identique des contenus aujourd'hui codés en dur (base.html / home.html) :
# après bascule, le rendu public ne change pas.
TICKER_PHRASES = [
    "Spectacle vivant",
    "Concerts",
    "Performances",
    "Fêtes de quartier",
    "Annecy",
]

HOME = {
    "subtitle": "Association culturelle · Annecy",
    "punchline": "On fait vibrer le [r]spectacle vivant[/r].",
    "intro": (
        "Concerts, performances et fêtes de quartier à Annecy. "
        "Squelette de fondation — le site complet arrive au fil de la roadmap."
    ),
}


def seed(apps, schema_editor):
    TickerItem = apps.get_model("pages", "TickerItem")
    HomeContent = apps.get_model("pages", "HomeContent")
    for order, text in enumerate(TICKER_PHRASES):
        TickerItem.objects.create(text=text, order=order)
    HomeContent.objects.create(**HOME)


def unseed(apps, schema_editor):
    apps.get_model("pages", "TickerItem").objects.all().delete()
    apps.get_model("pages", "HomeContent").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
