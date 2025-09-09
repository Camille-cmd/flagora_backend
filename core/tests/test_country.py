from unittest.mock import Mock, patch

from core.models import City, Country
from core.services.country_services import country_update
from flagora.tests.base import FlagoraTestCase


class CountryUpdateTest(FlagoraTestCase):
    def setUp(self):
        super().setUp()

        self.country.wikidata_id = "Wikidata_id"

        self.mock_sparql_data = {
            "results": {
                "bindings": [
                    {
                        "name_en": {"value": "Exampleland"},
                        "name_fr": {"value": "Exemplepays"},
                        "iso2": {"value": "EX"},
                        "iso3": {"value": "EXP"},
                        "flag": {"value": "https://commons.wikimedia.org/wiki/Special:FilePath/Example_Flag.svg"},
                        "capitalLabel_en": {"value": "Example City"},
                        "capitalLabel_fr": {"value": "Ville Exemple"},
                    }
                ]
            }
        }

        self.mock_continents = {"EX": "EU"}

    def mock_requests_get(self, url, params=None, **kwargs):
        mock_response = Mock()
        if "wikidata.org/sparql" in url:
            mock_response.json.return_value = self.mock_sparql_data
        elif "continent" in url:
            mock_response.json.return_value = self.mock_continents
        mock_response.raise_for_status = Mock()
        return mock_response

    @patch("core.services.country_services.requests.get")
    @patch.object(Country, "save_flag", return_value=True)
    def test_successful_update(self, mock_save_flag, mock_get):
        mock_get.side_effect = self.mock_requests_get

        country_update(self.country)

        self.country.refresh_from_db()
        self.assertEqual(self.country.name_en, "Exampleland")
        self.assertEqual(self.country.iso2_code, "EX")
        self.assertEqual(self.country.continent, "EU")

        capital_city = City.objects.get(name_en="Example City")
        self.assertTrue(capital_city.is_capital)
        self.assertIn(capital_city, self.country.cities.all())

        mock_save_flag.assert_called_once()

    def test_missing_wikidata_id(self):
        self.country.wikidata_id = None
        self.country.save()
        with self.assertRaises(ValueError) as ctx:
            country_update(self.country)
        self.assertIn("Wikidata ID is missing", str(ctx.exception))

    @patch("core.services.country_services.requests.get")
    def test_empty_results_from_sparql(self, mock_get):
        mock_response = Mock()
        mock_response.json.return_value = {"results": {"bindings": []}}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError) as ctx:
            country_update(self.country)
        self.assertIn("No results found", str(ctx.exception))

    @patch("core.services.country_services.requests.get")
    def test_too_many_results(self, mock_get):
        too_many = {"results": {"bindings": self.mock_sparql_data["results"]["bindings"] * 4}}
        mock_response = Mock()
        mock_response.json.return_value = too_many
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError) as ctx:
            country_update(self.country)
        self.assertIn("Too many results found", str(ctx.exception))

    @patch("core.services.country_services.requests.get")
    def test_missing_name_fields(self, mock_get):
        broken_data = {"results": {"bindings": [{"iso2": {"value": "EX"}, "iso3": {"value": "EXP"}}]}}
        mock_response = Mock()
        mock_response.json.return_value = broken_data
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError) as ctx:
            country_update(self.country)
        self.assertIn("Missing name_en or name_fr", str(ctx.exception))

    @patch("core.services.country_services.requests.get")
    def test_missing_iso_fields(self, mock_get):
        broken_data = {
            "results": {
                "bindings": [
                    {
                        "name_en": {"value": "Exampleland"},
                        "name_fr": {"value": "Exemplepays"},
                    }
                ]
            }
        }
        mock_response = Mock()
        mock_response.json.return_value = broken_data
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with self.assertRaises(ValueError) as ctx:
            country_update(self.country)
        self.assertIn("Missing iso2 or iso3", str(ctx.exception))

    @patch("core.services.country_services.requests.get")
    @patch.object(Country, "save_flag", return_value=False)
    def test_flag_not_saved(self, mock_save_flag, mock_get):
        mock_get.side_effect = self.mock_requests_get
        with self.assertRaises(ValueError) as ctx:
            country_update(self.country)
        self.assertIn("Could not save flag", str(ctx.exception))

    @patch("core.services.country_services.requests.get")
    @patch.object(Country, "save_flag", return_value=True)
    def test_missing_capital(self, mock_save_flag, mock_get):
        no_capital = {
            "results": {
                "bindings": [
                    {
                        "name_en": {"value": "Exampleland"},
                        "name_fr": {"value": "Exemplepays"},
                        "iso2": {"value": "EX"},
                        "iso3": {"value": "EXP"},
                        "flag": {"value": "https://commons.wikimedia.org/wiki/Special:FilePath/Example_Flag.svg"},
                        # No capital data
                    }
                ]
            }
        }

        def side_effect(url, params=None, **kwargs):
            mock_response = Mock()
            if "wikidata.org/sparql" in url:
                mock_response.json.return_value = no_capital
            else:
                mock_response.json.return_value = self.mock_continents
            mock_response.raise_for_status = Mock()
            return mock_response

        mock_get.side_effect = side_effect

        country_update(self.country)
        self.assertEqual(self.country.name_en, "Exampleland")


class CountryFlagTest(FlagoraTestCase):
    def setUp(self):
        super().setUp()

    @patch("core.models.country.requests.get")
    @patch("api.flag_store.flag_store.reload_flag")
    def test_save_flag_success(self, mock_reload_flag, mock_requests_get):
        # Mock requests.get to return 200 with fake SVG
        mock_requests_get.return_value.status_code = 200
        mock_requests_get.return_value.content = b"<svg>fakeflag</svg>"

        result = self.country.save_flag("http://fake-url/flag.svg")

        self.assertTrue(result)
        self.country.refresh_from_db()
        self.assertTrue("flag_" in self.country.flag.name)
        mock_reload_flag.assert_called_once_with(self.country.iso2_code)

    @patch("core.models.country.requests.get")
    @patch("api.flag_store.flag_store.reload_flag")
    def test_save_flag_failure(self, mock_reload_flag, mock_requests_get):
        # Mock requests.get to fail
        mock_requests_get.return_value.status_code = 404

        result = self.country.save_flag("http://fake-url/flag.svg")

        self.assertFalse(result)
        self.assertFalse(bool(self.country.flag))
        mock_reload_flag.assert_not_called()

    @patch("core.models.country.requests.get")
    @patch("api.flag_store.flag_store.reload_flag")
    def test_old_flag_deleted_when_requested(self, mock_reload_flag, mock_requests_get):
        # Save first flag
        mock_requests_get.return_value.status_code = 200
        mock_requests_get.return_value.content = b"<svg>flag1</svg>"
        self.country.save_flag("http://fake-url/flag.svg")

        old_flag_path = self.country.flag.path

        # Save new flag with delete_current=True (default)
        mock_requests_get.return_value.content = b"<svg>flag2</svg>"
        self.country.save_flag("http://fake-url/flag.svg", delete_current=True)

        # Old file should no longer exist
        self.assertFalse(self.country.flag.storage.exists(old_flag_path))

    @patch("core.models.country.requests.get")
    @patch("api.flag_store.flag_store.reload_flag")
    def test_old_flag_kept_when_delete_disabled(self, mock_reload_flag, mock_requests_get):
        # Save first flag
        mock_requests_get.return_value.status_code = 200
        mock_requests_get.return_value.content = b"<svg>flag1</svg>"
        self.country.save_flag("http://fake-url/flag.svg")

        old_flag_path = self.country.flag.path

        # Save new flag with delete_current=False
        mock_requests_get.return_value.content = b"<svg>flag2</svg>"
        self.country.save_flag("http://fake-url/flag.svg", delete_current=False)

        # Old file should still exist
        self.assertTrue(self.country.flag.storage.exists(old_flag_path))
