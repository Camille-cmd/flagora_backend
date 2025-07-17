from django.test import TestCase
from django.urls import reverse
from ninja.testing import TestClient

from api.routes.auth import auth_router
from core.tests.factories import UserFactory, CountryFactory, CityFactory


class FlagoraTestCase(TestCase):

    def setUp(self):
        self.user_password = "securepassword123"
        self.user = UserFactory(
            username="test_user",
            email="testuser@example.com",
            language="en",
        )
        self.user.set_password(self.user_password)
        self.user.save()

        self.city = CityFactory(
            name_fr="Nuuk",
            name_en="Nuuk",
            is_capital=True,
        )

        self.country = CountryFactory(
            name_fr="Groenland",
            name_en="Greenland",
            iso2_code="GL",
            iso3_code="GRL",
        )
        self.country.cities.add(self.city)

        self.login_url = reverse("api-1.0.0:user_login")

    def user_do_login(self):
        """
        Our app does not use traditional session, so we need to login manually.
        """
        payload = {"email": self.user.email, "password": self.user_password}
        r = self.client.post(self.login_url, data=payload, content_type="application/json")
        return {"Authorization": f"Bearer {r.json()["sessionId"]}"}
