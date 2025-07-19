import json
import logging
from pathlib import Path

from django.core.management import BaseCommand
from django.utils import timezone

from core.models import Country

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    @staticmethod
    def generate_backup_json():
        """
        Generate a JSON file with the data of all countries in the database for backup purposes.

        The JSON file will be saved in the 'data' directory.
        """
        countries_in_db = Country.objects.all()

        # Do not backup an empty database.
        if not countries_in_db:
            return

        countries_list = []
        for country in countries_in_db:
            cities_data = []
            for city in country.cities.all():
                cities_data.append(
                    {
                        "name_en": city.name_en,
                        "name_fr": city.name_fr,
                        "is_capital": city.is_capital,
                    }
                )

            country_dict = {
                "name_en": country.name_en,
                "name_fr": country.name_fr,
                "name_native": country.name_native,
                "iso2": country.iso2_code,
                "iso3": country.iso3_code,
                "flag": country.flag.name if country.flag else "",
                "continent": country.continent,
                "wikidata_id": country.wikidata_id,
                "cities": cities_data,
            }
            countries_list.append(country_dict)

        now = timezone.now()
        working_dir = Path(__file__).resolve()
        # Create directories if they do not exist
        Path(working_dir.parent, "data").mkdir(exist_ok=True)
        output_file = Path(working_dir.parent, "data", f"countries_data_saved_{now}.json")
        with open(output_file, "w", encoding="utf-8") as json_file:
            json.dump(countries_list, json_file, ensure_ascii=False, indent=4)

        logger.info(f"File {output_file} generated successfully!")

    def handle(self, *args, **options):
        self.generate_backup_json()
