import requests
from core.management.commands.import_countries import continents_url, CONTINENT_MAPPING
from core.models import Country, City


def country_update(country_obj: Country) -> None:
    """
    Update country data from Wikidata.
    """
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

    response = requests.get(sparql_url, params={'query': query, 'format': 'json'})
    response.raise_for_status()

    results = response.json().get('results', {}).get('bindings', [])
    if not results:
        raise ValueError(f"No results found for Wikidata ID: {country_obj.wikidata_id}")

    # More than 3 results is odd: duplicated results come from the capital cities, and the max is 3 for South Africa
    if len(results) > 3:
        raise ValueError(f"Too many results found for Wikidata ID: {country_obj.wikidata_id}")

    data = results[0]
    country_obj.name_en = data.get('name_en', {}).get('value')
    country_obj.name_fr = data.get('name_fr', {}).get('value')
    iso2 = data.get('iso2', {}).get('value')
    country_obj.iso2_code = iso2
    country_obj.iso3_code = data.get('iso3', {}).get('value')

    flag_url = data.get('flag', {}).get('value')  # This is the SVG file URL (Special:FilePath)
    if flag_url:
        country_obj.save_flag(flag_url)

    continents_data = requests.get(continents_url).json()
    continent = CONTINENT_MAPPING.get(continents_data.get(iso2), "Unknown")
    country_obj.continent = continent

    # Assume that duplicated results are for the capital cities of the same country
    cities_to_add_to_country = []
    for result in results:
        capital_en = result.get("capitalLabel_en", {}).get("value")
        capital_fr = result.get("capitalLabel_fr", {}).get("value")
        capital_city_obj, _ = City.objects.update_or_create(
            name_en=capital_en,
            defaults={
                "name_fr":capital_fr,
                "is_capital": True,
            }
        )
        cities_to_add_to_country.append(capital_city_obj)

    country_obj.cities.add(*cities_to_add_to_country)

    country_obj.save()
