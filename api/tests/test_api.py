from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from core.models import UserPreferenceGameMode
from core.models.user_country_score import GameModes
from core.tests.factories import CityFactory, CountryFactory
from flagora.tests.base import FlagoraTestCase

User = get_user_model()


class TestApi(FlagoraTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client(headers={"Content-Type": "application/json"})
        self.user_me_url = reverse("api-1.0.0:user_me")
        self.user_set_language_url = reverse("api-1.0.0:user_set_language")
        self.user_update_url = reverse("api-1.0.0:user_update")
        self.user_update_password_url = reverse("api-1.0.0:user_update_password")
        self.country_get_list_url = reverse("api-1.0.0:country_get_list")
        self.city_get_list_url = reverse("api-1.0.0:city_get_list")
        self.user_update_preferences_url = reverse("api-1.0.0:user_me_preferences")
        self.user_stats_url = reverse("api-1.0.0:user_stats")

    #### USER ME TESTS ####
    def test_user_me_authenticated(self):
        """
        Authenticated user should receive their user data.
        """
        headers = self.user_do_login()
        response = self.client.get(self.user_me_url, headers=headers)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["username"], self.user.username)
        self.assertEqual(data["email"], self.user.email)

    def test_user_me_unauthenticated(self):
        """
        Unauthenticated request should return 401.
        """
        response = self.client.get(self.user_me_url)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["errorMessage"], "User not authenticated")

    #### LANGUAGE TESTS ####
    def test_user_set_language_authenticated(self):
        """
        Authenticated user can set their language.
        """
        self.assertEqual(self.user.language, "en")
        headers = self.user_do_login()
        payload = {"language": "fr"}
        response = self.client.post(
            self.user_set_language_url,
            data=payload,
            content_type="application/json",
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {})

        # Reload user from DB to check if language was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.language, "fr")

    def test_user_set_language_unauthenticated(self):
        """
        Unauthenticated user cannot set language.
        """
        payload = {"language": "fr"}
        response = self.client.post(self.user_set_language_url, data=payload, content_type="application/json")

        self.assertEqual(response.status_code, 401)

    #### TEST USER UPDATE ####
    def test_user_update_success(self):
        """
        Authenticated user can update their username if it's unique.
        """
        headers = self.user_do_login()
        new_username = "updated_username"
        payload = {"username": new_username}

        response = self.client.put(
            self.user_update_url,
            data=payload,
            content_type="application/json",
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, new_username)

    def test_user_update_username_already_exists(self):
        """
        User cannot update username to one that already exists.
        """
        # Create another user with a conflicting username
        User.objects.create_user(username="existing_user", email="other@example.com", password="anotherpass")

        headers = self.user_do_login()
        payload = {"username": "existing_user"}

        response = self.client.put(
            self.user_update_url,
            data=payload,
            content_type="application/json",
            headers=headers,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errorMessage"], "Username already registered")

    def test_user_update_same_username(self):
        """
        Updating to the same username should not fail.
        """
        headers = self.user_do_login()
        payload = {"username": self.user.username}

        response = self.client.put(
            self.user_update_url,
            data=payload,
            content_type="application/json",
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, payload["username"])

    ### TEST UPDATE PASSWORD ####
    def test_user_update_password_success(self):
        """
        User can change password with correct old password.
        """
        headers = self.user_do_login()
        new_password = "newsecurepassword456"
        payload = {"old_password": self.user_password, "new_password": new_password}

        response = self.client.put(
            self.user_update_password_url,
            data=payload,
            content_type="application/json",
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {})

        # User can now login with the new password
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

    def test_user_update_password_wrong_old_password(self):
        """
        Changing password with wrong old password returns 400.
        """
        headers = self.user_do_login()
        payload = {
            "old_password": "wrongpassword",
            "new_password": "newsecurepassword456",
        }

        response = self.client.put(
            self.user_update_password_url,
            data=payload,
            content_type="application/json",
            headers=headers,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errorMessage"], "Old password is incorrect")

        # Ensure password wasn't changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.user_password))

    def test_old_password_no_longer_valid_after_update(self):
        """
        Ensure that after password change, the old password no longer works.
        """
        headers = self.user_do_login()
        new_password = "another_new_password_789"
        payload = {"old_password": self.user_password, "new_password": new_password}

        # Update password
        response = self.client.put(
            self.user_update_password_url,
            data=payload,
            content_type="application/json",
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)

        # Try logging in with old password
        login_attempt = self.client.post(
            self.login_url,
            data={"email": self.user.email, "password": self.user_password},
            content_type="application/json",
        )
        self.assertEqual(login_attempt.status_code, 401)

        # Login with new password should succeed
        login_attempt = self.client.post(
            self.login_url,
            data={"email": self.user.email, "password": new_password},
            content_type="application/json",
        )
        self.assertEqual(login_attempt.status_code, 200)

    #### TEST COUNTRIES LIST ####
    def test_country_get_list_unauthenticated_language_header(self):
        """
        Unauthenticated user gets country names based on Accept-Language header.
        """
        response = self.client.get(
            self.country_get_list_url,
            HTTP_ACCEPT_LANGUAGE="fr",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        countries = response.json()["countries"]

        self.assertTrue(any(c["name"] == "Groenland" for c in countries))
        self.assertTrue(any(c["iso2Code"] == "GL" for c in countries))

    def test_country_get_list_authenticated_user_language(self):
        """
        Authenticated user gets country names in their preferred language.
        """
        self.user.language = "en"
        self.user.save()
        headers = self.user_do_login()

        response = self.client.get(self.country_get_list_url, headers=headers)

        self.assertEqual(response.status_code, 200)
        countries = response.json()["countries"]

        self.assertTrue(any(c["name"] == "Greenland" for c in countries))
        self.assertTrue(any(c["iso2Code"] == "GL" for c in countries))

    def test_country_list_is_ordered_by_name(self):
        """
        Countries should be ordered alphabetically by name in the selected language.
        """
        CountryFactory(name_fr="Zambie", name_en="Zambia", iso2_code="ZM")
        CountryFactory(name_fr="Albanie", name_en="Albania", iso2_code="AL")

        response = self.client.get(
            self.country_get_list_url,
            HTTP_ACCEPT_LANGUAGE="en",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        country_names = [c["name"] for c in response.json()["countries"]]
        self.assertEqual(country_names, sorted(country_names))  ###

    #### TEST USER PREFERENCE ####
    def test_authenticated_user_creates_preferences(self):
        headers = self.user_do_login()
        game_mode = GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE

        payload = {"game_mode": game_mode, "show_tips": True}

        response = self.client.put(
            self.user_update_preferences_url, payload, content_type="application/json", headers=headers
        )
        self.assertEqual(response.status_code, 200)

        # Check preferences created
        pref = UserPreferenceGameMode.objects.get(user=self.user, game_mode=game_mode)
        self.assertTrue(pref.show_tips)

        # Check response contains user data
        self.assertEqual(response.json()["username"], self.user.username)

    def test_authenticated_user_updates_preferences(self):
        headers = self.user_do_login()
        game_mode = GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE
        # Create initial preference that should be updated
        UserPreferenceGameMode.objects.create(user=self.user, game_mode=game_mode, show_tips=False)

        payload = {"game_mode": game_mode, "show_tips": True}

        response = self.client.put(
            self.user_update_preferences_url, payload, content_type="application/json", headers=headers
        )
        self.assertEqual(response.status_code, 200)

        # Check preference updated
        pref = UserPreferenceGameMode.objects.get(user=self.user, game_mode=game_mode)
        self.assertTrue(pref.show_tips)

    #### TEST CITIES LIST ####
    def test_city_list_default_language(self):
        country = CountryFactory(name_fr="France", name_en="France", iso2_code="FR")
        city2 = CityFactory(name_fr="ParisFR", name_en="ParisEN")
        country.cities.add(city2)

        response = self.client.get(self.city_get_list_url, HTTP_ACCEPT_LANGUAGE="en")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check that all cities are returned in English
        city_names = [c["name"] for c in data["cities"]]
        self.assertEqual(city_names, sorted(city_names))  # should be alphabetically ordered
        self.assertIn(self.city.name_en, city_names)
        self.assertIn(city2.name_en, city_names)

    def test_city_list_in_french(self):
        country = CountryFactory(name_fr="France", name_en="France", iso2_code="FR")
        city2 = CityFactory(name_fr="ParisFR", name_en="ParisEN")
        country.cities.add(city2)

        response = self.client.get(self.city_get_list_url, HTTP_ACCEPT_LANGUAGE="fr")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        city_names = [c["name"] for c in data["cities"]]
        self.assertIn(city2.name_fr, city_names)

    #### TEST STATS ####
    @patch("api.routes.api.user_get_stats")
    def test_user_get_stats(self, user_get_stats_mock):
        user_get_stats_mock.return_value = []  # tested in stats_service_test
        headers = self.user_do_login()

        response = self.client.get(self.user_stats_url, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
