"""Rendu de la punchline du hero : balise légère `[r]…[/r]` pour rougir des mots.

Pas de Tiptap ici : la punchline est un gros titre, on veut juste mettre en avant
quelques mots. On échappe TOUT le texte d'abord (XSS), puis on transforme les
marqueurs en `<span>`. Sûr car `escape()` ne touche que `& < > " '` : les `[ ] /`
des marqueurs survivent intacts, le remplacement reste donc fiable."""

import re

from django.utils.html import escape
from django.utils.safestring import mark_safe

_HIGHLIGHT = re.compile(r"\[r\](.*?)\[/r\]")


def render_punchline(text):
    escaped = escape(text)
    html = _HIGHLIGHT.sub(r'<span class="text-red italic">\1</span>', escaped)
    return mark_safe(html)
