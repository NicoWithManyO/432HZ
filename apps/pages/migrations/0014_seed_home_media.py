from django.db import migrations


def seed(apps, schema_editor):
    # Crée l'unique ligne du singleton en mode désactivé : l'accueil reste inchangé tant
    # que l'asso n'a rien configuré, et le form du dashboard a toujours une instance.
    HomeMedia = apps.get_model("pages", "HomeMedia")
    if not HomeMedia.objects.exists():
        HomeMedia.objects.create(mode="off")


def unseed(apps, schema_editor):
    apps.get_model("pages", "HomeMedia").objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("pages", "0013_homemedia_homemediaimage_homemedia_images_and_more"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
