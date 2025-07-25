from unittest.mock import patch
from uuid import uuid4

from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone

from api.services.game_modes import GameServiceGuessCapitalFromCountry, GameServiceGuessCountryFromFlag
from core.models import Guess, UserCountryScore
from core.tests.factories import CityFactory, CountryFactory
from flagora.tests.base import FlagoraTestCase


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "isolated-test-cache",
        }
    }
)
class GameServiceTest(FlagoraTestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

        # Mocked Session
        self.session_id = uuid4()
        self.session_token = uuid4()
        self._create_mock_session(self.session_token, self.user.id)

        self.game_service = GameServiceGuessCountryFromFlag

    def _create_mock_session(self, session_key, user_id):
        session_data = {"_auth_user_id": user_id}
        encoded_data = Session.objects.encode(session_data)
        session = Session(
            session_key=str(session_key),
            session_data=encoded_data,
            expire_date=timezone.now() + timezone.timedelta(days=1),
        )
        session.save()
        return session

    def tearDown(self):
        super().tearDown()
        cache.clear()

    def _set_cache(self, index, country_name, country_iso2_code):
        cache.set(self.session_id, {index: (country_name, country_iso2_code)})

    def test_user_accept_success(self):
        result = self.game_service.user_accept(self.session_id, self.session_token)
        cached_user_id = cache.get(f"{self.session_id}_user_id")

        self.assertTrue(result)
        self.assertEqual(cached_user_id, self.user.id)

    def test_user_accept_invalid_session(self):
        fake_token = uuid4()
        result = self.game_service.user_accept(self.session_id, fake_token)
        cached_user_id = cache.get(f"{self.session_id}_user_id")

        self.assertFalse(result)
        self.assertIsNone(cached_user_id)

    def test_user_get_authenticated_user(self):
        cache.set(f"{self.session_id}_user_id", self.user.id)
        user = self.game_service.user_get(self.session_id)

        self.assertTrue(user.is_authenticated)
        self.assertEqual(user.id, self.user.id)

    def test_user_get_anonymous_user(self):
        # No user present in cache
        user = self.game_service.user_get(self.session_id)
        self.assertFalse(user.is_authenticated)

    @patch("api.services.user_country_score.UserCountryScoreService.compute_questions")
    @patch("api.flag_store.flag_store.get_path")
    def test_get_questions(self, mock_get_path, mock_compute_questions):
        mock_compute_questions.return_value = [self.country]
        mock_get_path.return_value = "/mock/path/to/flag.svg"

        result = self.game_service.get_questions(self.session_id)

        self.assertIn(0, result.questions)
        self.assertEqual(result.questions[0], "/mock/path/to/flag.svg")

        # Check the internal cache structure (used for answer validation)
        questions_with_answers = cache.get(self.session_id)
        self.assertEqual(questions_with_answers[0], (self.country.name_en, self.country.iso2_code))

    def test_check_answer_correct(self):
        self._set_cache(0, self.country.name_fr, self.country.iso2_code)

        is_correct, country = self.game_service.check_answer(self.session_id, 0, self.country.name_fr, self.user)

        self.assertTrue(is_correct)
        self.assertEqual(country.iso2_code, self.country.iso2_code)

    def test_check_answer_incorrect(self):
        self._set_cache(0, self.country.name_fr, self.country.iso2_code)

        is_correct, country = self.game_service.check_answer(self.session_id, 0, "FR", self.user)

        self.assertFalse(is_correct)
        self.assertEqual(country.iso2_code, self.country.iso2_code)

    def test_check_answer_invalid_index(self):
        self._set_cache(0, self.country.name_fr, self.country.iso2_code)

        is_correct, country = self.game_service.check_answer(self.session_id, 1, "FR", self.user)

        self.assertFalse(is_correct)
        self.assertIsNone(country)

    def test_guess_register(self):
        self.assertEqual(UserCountryScore.objects.count(), 0)
        self.assertEqual(Guess.objects.count(), 0)

        self.game_service.guess_register(self.user, is_correct=True, country=self.country)

        self.assertEqual(UserCountryScore.objects.count(), 1)
        self.assertEqual(Guess.objects.count(), 1)

        score = UserCountryScore.objects.first()
        self.assertEqual(score.user, self.user)
        self.assertEqual(score.country, self.country)
        self.assertTrue(score.user_guesses.first().is_correct)


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "isolated-test-cache",
        }
    },
    LANGUAGE_CODE="en",
)
class GameServiceGuessCapitalFromCountryTest(FlagoraTestCase):
    def setUp(self):
        super().setUp()
        self.session_id = uuid4()

        # Patch the compute_questions method to return our country
        patcher = patch("api.services.user_country_score.UserCountryScoreService.compute_questions")
        self.addCleanup(patcher.stop)
        self.mock_compute_questions = patcher.start()
        self.mock_compute_questions.return_value = [self.country]

        # Patch user_get
        patcher_user = patch(
            "api.services.game_modes.game_guess_capital_from_country.GameServiceGuessCapitalFromCountry.user_get"
        )
        self.addCleanup(patcher_user.stop)
        self.mock_user_get = patcher_user.start()
        self.mock_user_get.return_value = self.user

    def test_get_questions_stores_correct_data_in_cache(self):
        result = GameServiceGuessCapitalFromCountry.get_questions(self.session_id)

        self.assertIn(0, result.questions)
        self.assertEqual(result.questions[0], self.country.name_en)

        cached_data = cache.get(self.session_id)
        self.assertIsNotNone(cached_data)
        self.assertIn(0, cached_data)
        self.assertEqual(cached_data[0][1], "name_en")

    def test_check_answer_correct(self):
        GameServiceGuessCapitalFromCountry.get_questions(self.session_id)
        is_correct, country = GameServiceGuessCapitalFromCountry.check_answer(
            self.session_id,
            0,
            self.city.name_fr,
            self.user,
        )
        self.assertTrue(is_correct)
        self.assertEqual(country, self.country)

    def test_check_answer_incorrect(self):
        GameServiceGuessCapitalFromCountry.get_questions(self.session_id)
        is_correct, country = GameServiceGuessCapitalFromCountry.check_answer(
            self.session_id, 0, "WrongCity", self.user
        )
        self.assertFalse(is_correct)
        self.assertEqual(country, self.country)

    def test_check_answer_invalid_question_index(self):
        GameServiceGuessCapitalFromCountry.get_questions(self.session_id)
        is_correct, country = GameServiceGuessCapitalFromCountry.check_answer(self.session_id, 999, "Paris", self.user)
        self.assertFalse(is_correct)
        self.assertIsNone(country)

    def test_get_correct_answer(self):
        result = GameServiceGuessCapitalFromCountry.get_correct_answer(self.user, self.country)
        self.assertIn("correct_answer", result)
        self.assertIn("wikipedia_link", result)
        self.assertTrue(result["correct_answer"].startswith(self.city.name_en))

    def test_check_answer_raises_value_error_if_multiple_countries(self):
        country2 = CountryFactory(name_en="Country2")
        city2 = CityFactory(name_en="City2")
        country2.cities.add(city2)
        questions_with_answer = {0: ([self.city.id, city2.id], "name_en")}
        cache.set(self.session_id, questions_with_answer)

        with self.assertRaises(ValueError) as cm:
            GameServiceGuessCapitalFromCountry.check_answer(
                session_id=self.session_id,
                question_index=0,
                answer_submitted="SomeAnswer",
                user=self.user,
            )

        self.assertIn("Multiple countries found for cities", str(cm.exception))
