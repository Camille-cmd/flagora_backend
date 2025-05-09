from django.core.files.base import ContentFile
from django.db import models
import requests

from core.models.City import City

def flag_upload_path(instance, filename):
    """
    Generate the upload path for the flag of a country.
    :param instance: Country instance.
    :param filename: Original filename of the uploaded file.
    :return: Path for the file 'flags/<iso2_code>/<filename>'.
    """
    return f"flags/{instance.iso2_code}/{filename}"


class Country(models.Model):
    name_en = models.CharField(max_length=100)
    name_fr = models.CharField(max_length=100)
    name_native = models.CharField(max_length=100)
    iso2_code = models.CharField(max_length=2, unique=True)
    iso3_code = models.CharField(max_length=3, unique=True)
    flag = models.ImageField(upload_to=flag_upload_path, null=True)
    cities = models.ManyToManyField(City)
    continent = models.CharField(max_length=100)

    wikidata_id = models.CharField(max_length=100, null=True)

    class Meta:
        ordering = ('name_en',)
        verbose_name_plural = 'countries'

    def __str__(self):
        return self.name_en

    def save_flag(self, flag_url: str) -> None:
        """
        Save the flag of a country to a file and delete the old one if it exists.
        """
        # Delete the old flag file if it exists
        if self.flag and self.flag.path:
            self.flag.delete(save=False)

        response = requests.get(flag_url)
        if response.status_code == 200:
            file_name = "flag.svg"
            self.flag.save(file_name, ContentFile(response.content), save=True)
