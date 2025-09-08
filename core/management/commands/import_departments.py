import csv
import io
import requests
from django.core.management.base import BaseCommand

from core.models import Department


class Command(BaseCommand):
    help = "Import French departments data from official data.gouv.fr APIs"

    def fetch_prefectures_from_api(self):
        """Fetch prefectures data from official data.gouv.fr CSV."""
        url = "https://static.data.gouv.fr/resources/liste-des-departements-francais-metropolitains-doutre-mer-et-les-com-ainsi-que-leurs-prefectures/20210109-162321/liste-dpt-drom-com-v1.2.csv"

        try:
            self.stdout.write("Fetching prefectures data from data.gouv.fr...")
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Parse CSV content
            csv_content = response.content.decode("utf-8")
            csv_reader = csv.DictReader(io.StringIO(csv_content))

            prefectures = {}
            for row in csv_reader:
                dept_code = row["code"]
                prefecture = row["chefLieu"]
                prefectures[dept_code] = prefecture

            self.stdout.write(
                f"Successfully fetched {len(prefectures)} prefecture mappings"
            )
            return prefectures

        except requests.exceptions.RequestException as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to fetch prefectures data: {e}")
            )
            raise
        except (KeyError, csv.Error) as e:
            self.stdout.write(self.style.ERROR(f"Failed to parse CSV data: {e}"))
            raise

    def fetch_departments_from_api(self):
        """Fetch departments data from official data.gouv.fr API."""
        url = "https://geo.api.gouv.fr/departements?fields=nom,code,codeRegion,region"

        try:
            self.stdout.write("Fetching departments data from data.gouv.fr API...")
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            departments_data = response.json()
            self.stdout.write(
                f"Successfully fetched {len(departments_data)} departments"
            )
            return departments_data

        except requests.exceptions.RequestException as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to fetch departments data: {e}")
            )
            raise
        except ValueError as e:
            self.stdout.write(self.style.ERROR(f"Failed to parse JSON data: {e}"))
            raise

    def combine_department_data(self, departments_data, prefectures_data):
        """Combine departments and prefectures data."""
        transformed_data = []

        for dept in departments_data:
            dept_code = dept["code"]
            transformed_dept = {
                "number": dept_code,
                "name": dept["nom"],
                "region": dept["region"]["nom"],
                "prefecture": prefectures_data.get(dept_code, "Unknown"),
            }
            transformed_data.append(transformed_dept)

        return transformed_data

    def handle(self, *args, **options):
        try:
            # Fetch data from both APIs
            departments_data = self.fetch_departments_from_api()
            prefectures_data = self.fetch_prefectures_from_api()

            # Combine the data
            combined_data = self.combine_department_data(
                departments_data, prefectures_data
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Failed to fetch data from APIs: {e}. Aborting import."
                )
            )
            return

        created_count = 0
        updated_count = 0

        for dept_data in combined_data:
            department, created = Department.objects.update_or_create(
                number=dept_data["number"],
                defaults={
                    "name": dept_data["name"],
                    "region": dept_data["region"],
                    "prefecture": dept_data["prefecture"]
                }
            )

            if created:
                created_count += 1
                self.stdout.write(f"Created: {department}")
            else:
                updated_count += 1
                self.stdout.write(f"Updated: {department}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Import completed. Created: {created_count}, Updated: {updated_count} departments from data.gouv.fr APIs"
            )
        )
