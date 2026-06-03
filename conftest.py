"""Fixtures partagées par toute la suite de tests.

django-ratelimit est actif en dev/prod, mais son compteur vit dans le cache (mémoire de
process) et persisterait donc entre tests, provoquant de faux 403. On le désactive par défaut
ici ; les tests qui ciblent le throttling le réactivent (`settings.RATELIMIT_ENABLE = True`)
et vident le cache eux-mêmes. django-axes, lui, stocke en base : il est isolé naturellement
par le rollback de `@pytest.mark.django_db`.
"""

import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _isolate_ratelimit(settings):
    settings.RATELIMIT_ENABLE = False
    cache.clear()
