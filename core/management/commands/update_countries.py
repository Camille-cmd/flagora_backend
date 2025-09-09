import logging

from django.core.management import BaseCommand

from core.management.commands.generate_countries_json_backup import (
    Command as CountriesBackupCommand,
)
from core.models import Country
from core.services.country_services import country_update

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--country_iso2code", "-c", type=str, help="The iso2 code of the country to import.")

    def handle(self, *args, **options):
        country_iso2_code = options.get("country_iso2code")

        countries_filters = {}
        if country_iso2_code:
            countries_filters["iso2code"] = country_iso2_code

        # Backup data before importing and updating
        CountriesBackupCommand.generate_backup_json()

        for country in Country.objects.filter(**countries_filters):
            try:
                country_update(country)
            except ValueError as e:
                logger.error(self.style.ERROR(f"Update error : {country.name_en} - {country.iso2_code} - {str(e)}"))

        logger.info(self.style.SUCCESS("All countries updated."))
