from django.http import HttpResponse

# Chemins interdits aux robots (back-office).
DISALLOWED = ["/gestion/", "/django-admin/"]


def robots_txt(request):
    """robots.txt servi dynamiquement : la ligne Sitemap pointe sur le host courant."""
    lines = ["User-agent: *"]
    lines += [f"Disallow: {path}" for path in DISALLOWED]
    lines += ["", f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}"]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")
