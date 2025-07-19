from unittest.mock import mock_open, patch

from django.core.cache import cache
from django.test import override_settings

from api.flag_store import FlagStore
from flagora.tests.base import FlagoraTestCase


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "isolated-test-cache",
        }
    }
)
class FlagStoreTestCase(FlagoraTestCase):
    @patch("core.models.Country.objects.all")
    def setUp(self, mock_countries_all):
        super().setUp()
        cache.clear()
        self.flag_store = FlagStore()

    def test_get_path_no_cache(self):
        path = self.flag_store.get_path(self.country.iso2_code)
        self.assertIsNone(path)

    def test_get_path_cached_flag(self):
        cache.set(self.country.iso2_code, "mocked_flag_content")
        path = self.flag_store.get_path(self.country.iso2_code)
        self.assertEqual(path, "mocked_flag_content")

    @patch("core.models.Country.objects.get")
    def test_reload_flag(self, mock_get_country):
        mock_get_country.return_value = self.country
        with patch("builtins.open", mock_open(read_data="mocked_flag_content")) as mock_file:
            self.flag_store.reload_flag(self.country.iso2_code)

        cached_flag = cache.get(self.country.iso2_code)
        self.assertEqual(cached_flag, "mocked_flag_content")
        mock_get_country.assert_called_once_with(iso2_code=self.country.iso2_code)
        mock_file.assert_called_once_with(self.country.flag.path, "r")

    @patch("core.models.Country.objects.all")
    def test_reload_all_flags(self, mock_all_countries):
        mock_all_countries.return_value = [self.country]
        with patch("builtins.open", mock_open(read_data="mocked_flag_content")) as mock_file:
            self.flag_store.reload_all_flags()

        cached_flag = cache.get(self.country.iso2_code)
        self.assertEqual(cached_flag, "mocked_flag_content")
        mock_all_countries.assert_called_once()
        mock_file.assert_called_once_with(self.country.flag.path, "r")

    @patch("core.models.Country.objects.get")
    def test_cache_flag(self, mock_get_country):
        mock_get_country.return_value = self.country
        with patch("builtins.open", mock_open(read_data="mocked_flag_content")) as mock_file:
            self.flag_store._cache_flag(self.country.iso2_code)

        cached_flag = cache.get(self.country.iso2_code)
        self.assertEqual(cached_flag, "mocked_flag_content")
        mock_file.assert_called_once_with(self.country.flag.path, "r")

    @patch("core.models.Country.objects.all")
    def test_cache_flags_all(self, mock_all_countries):
        mock_all_countries.return_value = [self.country]
        with patch("builtins.open", mock_open(read_data="mocked_flag_content")) as mock_file:
            self.flag_store._cache_flags()

        cached_flag = cache.get(self.country.iso2_code)
        self.assertEqual(cached_flag, "mocked_flag_content")
        mock_all_countries.assert_called_once()
        mock_file.assert_called_once_with(self.country.flag.path, "r")
