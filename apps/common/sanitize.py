"""Nettoyage du HTML léger saisi dans les descriptions (events, actus).

Barrière de sécurité côté serveur : seul un sous-ensemble de balises est conservé,
le reste est strippé. Posée au niveau du modèle (save), elle s'applique quel que soit
le chemin d'écriture. Reste en place même quand l'éditeur riche (Tiptap) arrive."""

import nh3

# Balises autorisées dans les descriptions (cf cahier : HTML léger).
ALLOWED_TAGS = {
    "p", "strong", "em", "u", "s", "a",
    "ul", "ol", "li", "h2", "h3", "blockquote", "code",
}

# Seuls les liens portent des attributs (nh3 force rel=noopener par défaut).
ALLOWED_ATTRIBUTES = {"a": {"href", "title"}}


def clean_html(value):
    """Renvoie `value` débarrassé de toute balise/attribut hors allowlist."""
    return nh3.clean(value, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
