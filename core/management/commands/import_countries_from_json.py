import json
import logging
from collections import defaultdict
from pathlib import Path

import requests
from django.core.files.base import ContentFile
from django.core.management import BaseCommand
from django.utils import timezone

from core.models import Country, City

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            "-f", "-file_name",
            type=str,
            help="The path to the JSON file containing the countries data. "
                 "The file MUST be in the 'data' directory. If not provided, the data will be fetched from the API."
        )

    def handle(self, *args, **options):
        json_file_name = options.get("file_name")

        file_path = Path(__file__).resolve().parent / "data" / json_file_name
        with open(file_path, "r", encoding="utf-8") as json_file:
            countries = json.load(json_file)

        self.import_countries_from_json(countries)

        logger.info("Import complete.")

    def import_countries_from_json(self, countries: list[dict]) -> None:
        """
        Import countries from a backup JSON file located in the 'data' directory.
        """
        for country in countries:
            name_en = country["name_en"]
            name_fr = country["name_fr"]
            name_native = country["name_native"]
            flag_url = country["flag"]
            continent = country["continent"]
            iso2 = country["iso2"]
            iso3 = country["iso3"]
            wikidata_id = country["wikidata_id"]
            cities_data = country["cities"]

            country_obj, _ = Country.objects.update_or_create(
                iso2_code=iso2,
                defaults={
                    "name_en": name_en,
                    "name_fr": name_fr,
                    "name_native": name_native,
                    "continent": continent,
                    "iso3_code": iso3,
                    "flag": flag_url,
                    "wikidata_id": wikidata_id,
                }
            )

            cities_to_add_to_country = set()
            for city_data in cities_data:
                city, _ = City.objects.update_or_create(
                    name_en=city_data["name_en"],
                    defaults={
                        "name_fr": city_data["name_fr"],
                        "is_capital": city_data["is_capital"]
                    }
                )

                cities_to_add_to_country.add(city)

            country_obj.cities.add(*cities_to_add_to_country)
