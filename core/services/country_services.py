import logging

import requests
from django.utils.translation import gettext as _

from core.management.commands.import_countries import CONTINENT_MAPPING, continents_url
from core.models import City, Country
from core.services.utils import get_sparql_headers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def country_update(country_obj: Country) -> None:
    """
    Update country data from Wikidata.
    """
    if country_obj.wikidata_id is None:
        raise ValueError("Wikidata ID is missing for the country.")

    sparql_url = "https://query.wikidata.org/sparql"
    query = f"""
    SELECT ?name_en ?name_fr ?iso2 ?iso3 ?flag ?capital ?capitalLabel_en ?capitalLabel_fr WHERE {{
      BIND(wd:{country_obj.wikidata_id} AS ?country)

      OPTIONAL {{ ?country rdfs:label ?name_en. FILTER(LANG(?name_en) = "en") }}
      OPTIONAL {{ ?country rdfs:label ?name_fr. FILTER(LANG(?name_fr) = "fr") }}
      OPTIONAL {{ ?country wdt:P297 ?iso2. }}
      OPTIONAL {{ ?country wdt:P298 ?iso3. }}
      OPTIONAL {{ ?country wdt:P41 ?flag. }}
      OPTIONAL {{
        ?country wdt:P36 ?capital.
        OPTIONAL {{ ?capital rdfs:label ?capitalLabel_en. FILTER(LANG(?capitalLabel_en) = "en") }}
        OPTIONAL {{ ?capital rdfs:label ?capitalLabel_fr. FILTER(LANG(?capitalLabel_fr) = "fr") }}
      }}
    }}
    """

    response = requests.get(
        sparql_url, params={"query": query, "format": "json"}, timeout=30, headers=get_sparql_headers()
    )
    response.raise_for_status()

    results = response.json().get("results", {}).get("bindings", [])

    if not results:
        raise ValueError(_("No results found for {id}:").format(id=country_obj.wikidata_id))

    # More than 3 results is odd: duplicated results come from the capital cities, and the max is 3 for South Africa
    if len(results) > 3:
        raise ValueError(_("Too many results found for {id}:").format(id=country_obj.wikidata_id))

    data = results[0]
    name_en = data.get("name_en", {}).get("value")
    name_fr = data.get("name_fr", {}).get("value")
    if not name_en or not name_fr:
        raise ValueError(_("Missing name_en or name_fr for Wikidata ID: {id}").format(id=country_obj.wikidata_id))
    country_obj.name_en = name_en
    country_obj.name_fr = name_fr

    iso2 = data.get("iso2", {}).get("value")
    iso3 = data.get("iso3", {}).get("value")
    if not iso2 or not iso3:
        raise ValueError(_("Missing iso2 or iso3 for Wikidata ID: {id}").format(id=country_obj.wikidata_id))
    country_obj.iso2_code = iso2
    country_obj.iso3_code = iso3

    # Handle continent
    continents_data = requests.get(continents_url, timeout=10).json()
    continent = CONTINENT_MAPPING.get(continents_data.get(iso2), "Unknown")
    country_obj.continent = continent

    # Handle cities: assume that duplicated results are for the capital cities of the same country
    cities_to_add_to_country = []
    for result in results:
        capital_en = result.get("capitalLabel_en", {}).get("value")
        capital_fr = result.get("capitalLabel_fr", {}).get("value")

        if not capital_en and not capital_fr:
            logger.warning(
                _("No capital data found for country {name_en} with Wikidata ID {id}").format(
                    name_en=name_en, id=country_obj.wikidata_id
                )
            )
            continue

        capital_city_obj, created = City.objects.update_or_create(
            name_en=capital_en,
            defaults={
                "name_fr": capital_fr or capital_en,
                "is_capital": True,
            },
        )
        cities_to_add_to_country.append(capital_city_obj)

    # Handle Flag
    flag_url = data.get("flag", {}).get("value")  # This is the SVG file URL (Special:FilePath)
    if flag_url:
        saved_flag = country_obj.save_flag(flag_url)
        if not saved_flag:
            raise ValueError(_("Could not save flag for country {name_en}").format(name_en=name_en))

    # Final save
    country_obj.save()
    country_obj.cities.add(*cities_to_add_to_country)
    logger.info(f"Country {country_obj.name_en} updated successfully.")
