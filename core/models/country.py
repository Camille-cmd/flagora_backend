import requests
from django.core.files.base import ContentFile
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models.city import City

# Mapping of continent codes to full names
CONTINENT_MAPPING = {
    "AF": "Africa",
    "AS": "Asia",
    "EU": "Europe",
    "NA": "North America",
    "SA": "South America",
    "OC": "Oceania",
    "AN": "Antarctica",
}


def flag_upload_path(instance, filename):
    """
    Generate the upload path for the flag of a country.
    :param instance: Country instance.
    :param filename: Original filename of the uploaded file.
    :return: Path for the file 'flags/<iso2_code>/<filename>'.
    """
    return f"flags/{instance.iso2_code}/{filename}"


class Country(models.Model):
    name_en = models.CharField(max_length=100, verbose_name=_("English name"))
    name_fr = models.CharField(max_length=100, verbose_name=_("French name"))
    name_native = models.CharField(max_length=100, verbose_name=_("Native name"))
    iso2_code = models.CharField(max_length=2, unique=True, verbose_name=_("iso2 code"))
    iso3_code = models.CharField(max_length=3, unique=True, verbose_name=_("iso3 code"))
    flag = models.ImageField(upload_to=flag_upload_path, null=True, blank=True, verbose_name=_("Flag"))
    cities = models.ManyToManyField(City, related_name="countries", verbose_name=_("Cities"))
    continent = models.CharField(max_length=100, choices=CONTINENT_MAPPING.items(), verbose_name=_("Continent"))

    wikidata_id = models.CharField(max_length=100, null=True, verbose_name=_("Wikidata ID"))

    class Meta:
        ordering = ("name_en",)
        verbose_name = _("country")
        verbose_name_plural = _("countries")

    def __str__(self):
        return self.name_en

    def save_flag(self, flag_url: str, delete_current: bool = True) -> bool:
        """
        Save the flag of a country to a file and delete the old one if it exists.
        """
        # Delete the old flag file if it exists
        if delete_current and self.flag and self.flag.path:
            self.flag.delete(save=False)

        headers = {"User-Agent": "FlagoraBot/0.0"}
        response = requests.get(flag_url, headers=headers, timeout=10)
        if response.status_code == 200:
            file_name = "flag.svg"
            self.flag.save(file_name, ContentFile(response.content), save=True)
            from api.flag_store import flag_store

            flag_store.reload_flag(self.iso2_code)
            return True

        return False

    @property
    def capitals(self) -> models.QuerySet["City"]:
        return self.cities.filter(is_capital=True)

    def get_capitals_names(self, name_field) -> list["City"]:
        return list(self.capitals.values_list(name_field, flat=True))
