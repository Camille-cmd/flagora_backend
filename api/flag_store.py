from django.core.cache import cache
from django.db.models import QuerySet

from core.models import Country


class FlagStore:
    def __init__(self):
        self._cache_flags()

    @staticmethod
    def get_path(country_iso2: int) -> str | None:
        return cache.get(country_iso2)

    def reload_flag(self, country_iso2: int) -> None:
        self._cache_flag(country_iso2)

    def reload_all_flags(self) -> None:
        self._cache_flags()

    def _cache_flag(self, country_iso2: int) -> None:
        country = Country.objects.get(iso2_code=country_iso2)
        self._cache_flags([country])

    @staticmethod
    def _cache_flags(countries: QuerySet[Country] = None) -> None:
        if countries is None:
            countries = Country.objects.all()

        for country in countries:
            flag = country.flag
            if flag:
                with open(flag.path, "r") as f:
                    cache.set(country.iso2_code, f.read(), timeout=None)


flag_store = FlagStore()
