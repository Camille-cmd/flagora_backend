import logging
from collections import defaultdict

import requests
from asgiref.timeout import timeout
from django.core.management import BaseCommand

from core.management.commands.generate_countries_json_backup import (
    Command as CountriesBackupCommand,
)
from core.models import City, Country
from core.models.country import CONTINENT_MAPPING
from core.services.utils import get_sparql_headers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API endpoints
countries_url = (
    "https://data.enseignementsup-recherche.gouv.fr/api/explore/v2.1/catalog/datasets/curiexplore-pays/records"
)
continents_url = "https://country.io/continent.json"


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--country_name", type=str, help="The name of the country to import.")

    @staticmethod
    def fetch_countries(country_name: str = None) -> list:
        """
        Get the complete list of countries from the curiexplore-pays API.

        :param country_name: The name of the country to filter by.
        :return: List of countries.
        """
        limit = 100
        offset = 0

        countries = []
        has_more = True
        while has_more:
            request_addition = ""
            if country_name:
                request_addition = f"&where=name_en='{country_name}'"
            response = requests.get(f"{countries_url}?limit={limit}&offset={offset}{request_addition}", timeout=10)
            results = response.json()["results"]

            if len(results) == 0:
                break

            countries += results

            has_more = len(results) == limit
            offset += limit

        return countries

    @staticmethod
    def get_countries_capitals_from_wikidata(
        country_wikidata_ids: list,
    ) -> dict[int, list[dict[str, str]]]:
        """
        Get the capital cities of countries from Wikidata.
        A city can have multiple capital cities (e.g., South Africa). Therefore, we return a list of capital cities.
        :param country_wikidata_ids: Wikidata ID of the country.
        :return: Dictionary of capital cities for each country {wikidata_id: list(capital_city_data)}.
        """
        # Endpoint SPARQL
        sparql_url = "https://query.wikidata.org/sparql"
        # SPARQL Query
        # The wikidata ids need to have the wd (entity) prefix for the query to work.
        values_clause = " ".join(f"wd:{wikidata_id}" for wikidata_id in country_wikidata_ids)
        query = f"""
        SELECT ?country ?countryLabel ?capitalLabel_en ?capitalLabel_fr WHERE {{
          VALUES ?country {{ {values_clause} }}              # List of countries
          ?country wdt:P36 ?capital.                      # Capital of each country

          OPTIONAL {{
            ?capital rdfs:label ?capitalLabel_en.
            FILTER (lang(?capitalLabel_en) = "en")
          }}
          OPTIONAL {{
            ?capital rdfs:label ?capitalLabel_fr.
            FILTER (lang(?capitalLabel_fr) = "fr")
          }}

          SERVICE wikibase:label {{                        # Get the label of the country
            bd:serviceParam wikibase:language "en".
          }}
        }}
        """

        # GET request to SPARQL API
        response = requests.get(
            sparql_url, params={"query": query, "format": "json"}, timeout=30, headers=get_sparql_headers()
        )
        response.raise_for_status()

        results = response.json().get("results", {}).get("bindings", [])
        if not results:
            logger.warning("No results found for the given Wikidata ID.")
            return {}  # No results found

        # Extract the capital city data for each country
        capital_data = defaultdict(list)
        for result in results:
            country_wikidata_id = result["country"]["value"].split("/")[-1]
            capital_en = result.get("capitalLabel_en", {}).get("value")
            capital_fr = result.get("capitalLabel_fr", {}).get("value")

            # Don't create a capital city if we do not have full information.
            if not capital_en or not capital_fr:
                continue

            capital_data[country_wikidata_id].append(
                {
                    "name_en": capital_en,
                    "name_fr": capital_fr,
                }
            )

        return capital_data

    def handle(self, *args, **options):
        country_name = options.get("country_name")

        # Backup data before importing and updating
        CountriesBackupCommand.generate_backup_json()

        # Import countries updating what is in db
        self.import_countries(country_name)

        logger.info("Import complete.")

    def import_countries(self, country_name: str = None) -> None:
        """
        Import countries from curiexplore-pays API.
        For continents, we use the continent code from the country.io API
        For the countries' capitals, we use the Wikidata API.

        :param country_name: The name of a single country to import.
        """
        countries = self.fetch_countries(country_name)
        continents_data = requests.get(continents_url, timeout=10).json()
        countries_wikidata_ids = [country["wikidata"] for country in countries if country.get("wikidata")]
        capitals_data = self.get_countries_capitals_from_wikidata(countries_wikidata_ids)

        for country in countries:
            name_en = country["name_en"]
            name_fr = country["name_fr"]
            name_native = country["name_native"]
            flag_url = country["flag"]

            # Blocks the import of the country
            iso2 = country["iso2"]
            if iso2 is None or len(iso2) != 2:
                logger.warning(f"Invalid ISO2 code: {iso2} or missing ISO2 code. Skipping country {name_en}.")
                continue

            # Blocks the import of the country
            iso3 = country["iso3"]
            if iso3 is None or len(iso3) != 3:
                logger.warning(f"Invalid ISO3 code: {iso3} or missing ISO3 code. Skipping country {name_en}.")
                continue

            # Can continue but some information will be missing
            wikidata_id = country.get("wikidata")
            if not wikidata_id:
                logger.info(f"No Wikidata ID found for country {name_en}.")

            continent = CONTINENT_MAPPING.get(continents_data.get(iso2), "Unknown")

            country_obj, country_obj_created = Country.objects.update_or_create(
                iso2_code=iso2,
                iso3_code=iso3,
                defaults={
                    "name_en": name_en,
                    "name_fr": name_fr,
                    "name_native": name_native,
                    "continent": continent,
                    "wikidata_id": wikidata_id or None,
                },
            )
            saved_flag = country_obj.save_flag(flag_url, delete_current=False)
            if not saved_flag:
                logger.warning(f"Could not save flag for country {name_en}.")

            # Capital data (some countries can have multiple capital cities)
            capitals_data_for_country = capitals_data.get(wikidata_id, {})
            if not capitals_data_for_country:
                logger.info(f"No capital data found for country {name_en} with Wikidata ID {wikidata_id}.")
                continue

            cities_to_add_to_country = []
            for capital_data in capitals_data_for_country:
                capital_city_obj, _ = City.objects.update_or_create(
                    name_en=capital_data["name_en"],
                    defaults={
                        "name_fr": capital_data["name_fr"],
                        "is_capital": True,
                    },
                )
                cities_to_add_to_country.append(capital_city_obj)

            country_obj.cities.add(*cities_to_add_to_country)
