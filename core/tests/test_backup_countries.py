import json
import tempfile
import shutil
from pathlib import Path
from unittest import mock

from django.test import TestCase, override_settings

from core.management.commands.generate_countries_json_backup import Command
from core.models import Country, City
from flagora.tests.base import FlagoraTestCase


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class BackupCountriesTest(FlagoraTestCase):
    def setUp(self):
        super().setUp()
        # Create temporary directory for testing JSON output
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_working_dir = Path(__file__).resolve().parent
        self.command = Command()

        # Patch __file__ location to point to the test folder structure
        Command.__module__ = "core.management.commands.generate_countries_json_backup"
        self.fake_file_path = self.temp_dir / "backup_countries.py"
        self.fake_file_path.touch()
        self.command_file = self.fake_file_path

    def tearDown(self):
        # Cleanup temporary directory
        shutil.rmtree(self.temp_dir)

    def test_generate_backup_json_creates_file_with_expected_data(self):
        # Patch the command's working directory to our test directory
        command_path = self.command.generate_backup_json.__globals__["__file__"]
        self.command.generate_backup_json.__globals__["__file__"] = str(self.fake_file_path)

        # Run the command
        self.command.generate_backup_json()

        # Restore original __file__ value
        self.command.generate_backup_json.__globals__["__file__"] = command_path

        # Find the generated JSON file
        data_dir = self.temp_dir / "data"
        json_files = list(data_dir.glob("countries_data_saved_*.json"))

        self.assertEqual(len(json_files), 1)
        backup_file = json_files[0]

        with open(backup_file, encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(len(data), 1)
        country_data = data[0]
        self.assertEqual(country_data["name_en"], "Greenland")
        self.assertEqual(len(country_data["cities"]), 2)
        city_names = {c["name_en"] for c in country_data["cities"]}
        self.assertIn("Nuuk", city_names)

    def test_generate_backup_json_skips_when_no_countries(self):
        """
        Test that no file is created when there are no countries in the database.
        """
        Country.objects.all().delete()

        # Patch the command's working directory to our test directory
        command_path = self.command.generate_backup_json.__globals__["__file__"]
        self.command.generate_backup_json.__globals__["__file__"] = str(self.fake_file_path)

        # Confirm no countries exist
        self.assertEqual(Country.objects.count(), 0)

        self.command.generate_backup_json()

        # Restore original __file__ value
        self.command.generate_backup_json.__globals__["__file__"] = command_path

        # Find the generated JSON file
        data_dir = self.temp_dir / "data"
        json_files = list(data_dir.glob("countries_data_saved_*.json"))

        self.assertEqual(len(json_files), 0, "No file should be created if database is empty.")
