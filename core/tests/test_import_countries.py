from unittest.mock import patch

import requests
from django.core.management import call_command
from django.test import TestCase
from core.models import Country, City

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Error")

class ImportCountriesCommandTest(TestCase):

    @patch("core.models.Country.save_flag", return_value=True)
    @patch("core.management.commands.import_countries.requests.get")
    def test_import_countries_from_api(self, mock_get, mock_save_flag):
        # Mock API responses
        # Mocking the countries API response
        mock_get.side_effect = [
            # curiexplore-pays API
            MockResponse(
                json_data={
                    "results": [
                        {
                            "name_en": "France",
                            "name_fr": "France",
                            "name_native": "France",
                            "iso2": "FR",
                            "iso3": "FRA",
                            "flag": "https://example.com/france.svg",
                            "wikidata": "Q142"
                        }
                    ]
                },
                status_code=200,
            ),
            # Country.io continent API
            MockResponse(
                json_data={
                    "FR": "EU"
                },
                status_code=200
            ),
            # Wikidata
            MockResponse(
                json_data={
                    'head':{
                            'vars': ['country', 'countryLabel', 'capitalLabel_en', 'capitalLabel_fr']
                        },
                    'results': {
                        'bindings': [{
                            'capitalLabel_fr': {'xml:lang': 'fr', 'type': 'literal', 'value': 'Paris'},
                            'capitalLabel_en': {'xml:lang': 'en', 'type': 'literal', 'value': 'Paris'},
                            'country': {'type': 'uri', 'value': 'http://www.wikidata.org/entity/Q142'},
                            'countryLabel': {'xml:lang': 'en', 'type': 'literal', 'value': 'France'}
                        }]
                    }},
                status_code=200
            ),
        ]

        # Call the command
        call_command("import_countries")

        # Assertions on Country object
        self.assertEqual(Country.objects.count(), 1)
        country = Country.objects.get(iso2_code="FR")
        self.assertEqual(country.name_en, "France")
        self.assertEqual(country.name_fr, "France")
        self.assertEqual(country.continent, "Europe")  # Based on CONTINENT_MAPPING
        self.assertTrue(mock_save_flag.called)  # Ensures save_flag was called

        # Assertions on City object
        self.assertEqual(City.objects.count(), 1)
        city = City.objects.get(name_en="Paris")
        self.assertEqual(city.name_fr, "Paris")

        # Ensure the capital city is linked to the country
        self.assertIn(city, country.cities.all())
