from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone

from api.services.game_modes.challenge_modes.game_guess_country_from_flag import (
    GameServiceGuessCountryFromFlagChallengeCombo,
)
from api.services.game_modes.training_modes.game_guess_capital_from_country import (
    GameServiceGuessCapitalFromCountryTrainingInfinite,
)
from api.services.game_modes.training_modes.game_guess_country_from_flag import (
    GameServiceGuessCountryFromFlagTrainingInfinite,
)
from core.models import Guess, UserCountryScore, UserStats
from core.tests.factories import CountryFactory
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

        self.game_service = GameServiceGuessCountryFromFlagTrainingInfinite

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

    def _set_cache(self, index, country_iso2_code):
        cache.set(self.session_id, {index: country_iso2_code})

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
        self.assertEqual(questions_with_answers[0], self.country.iso2_code)

    def test_check_answer_correct(self):
        self._set_cache(0, self.country.iso2_code)

        is_correct, country = self.game_service.check_answer(self.session_id, 0, self.country.iso2_code, self.user)

        self.assertTrue(is_correct)
        self.assertEqual(country.iso2_code, self.country.iso2_code)

    def test_check_answer_incorrect(self):
        self._set_cache(0, self.country.iso2_code)

        is_correct, country = self.game_service.check_answer(self.session_id, 0, "FR", self.user)

        self.assertFalse(is_correct)
        self.assertEqual(country.iso2_code, self.country.iso2_code)

    def test_check_answer_invalid_index(self):
        self._set_cache(0, self.country.iso2_code)

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

    def test_user_get_streak_score_no_remaining(self):
        cache.set(f"{self.session_id}_user_streak", 2)  # current streak is 2

        (
            current_score,
            game_over,
            best_streak,
        ) = self.game_service.user_get_streak_score(self.session_id, self.user, is_correct=True, remaining_to_guess=0)

        self.assertEqual(current_score, 3)
        self.assertFalse(game_over)
        self.assertEqual(best_streak, None)  # beast streak only if failure
        self.assertEqual(cache.get(f"{self.session_id}_user_streak"), 3)

    def test_user_get_streak_score_with_remaining(self):
        cache.set(f"{self.session_id}_user_streak", 2)  # the current streak is 2

        (
            current_score,
            game_over,
            best_streak,
        ) = self.game_service.user_get_streak_score(self.session_id, self.user, is_correct=True, remaining_to_guess=1)

        self.assertEqual(current_score, 2)  # score is not incremented as we have remaining to guess
        self.assertFalse(game_over)
        self.assertEqual(best_streak, None)  # beast streak only if failure
        self.assertEqual(cache.get(f"{self.session_id}_user_streak"), 2)

    def test_user_get_streak_score_incorrect(self):
        cache.set(f"{self.session_id}_user_streak", 2)  # the current streak is 2

        # unauthenticated user
        user = AnonymousUser()

        # training mode, no game over
        (
            current_score,
            game_over,
            best_streak,
        ) = self.game_service.user_get_streak_score(self.session_id, user, is_correct=False, remaining_to_guess=1)

        self.assertEqual(current_score, 2)  # score is not incremented as we have an incorrect answer
        self.assertFalse(game_over)
        self.assertEqual(best_streak, None)
        self.assertEqual(cache.get(f"{self.session_id}_user_streak"), 2)

        # challenge mode, game over
        cache.set(f"{self.session_id}_user_streak", 2)  # reset streak
        game_service = GameServiceGuessCountryFromFlagChallengeCombo
        (
            current_score,
            game_over,
            best_streak,
        ) = game_service.user_get_streak_score(self.session_id, user, is_correct=False, remaining_to_guess=1)

        self.assertEqual(current_score, 0)  # score back to 0 as we have game over
        self.assertTrue(game_over)
        self.assertEqual(best_streak, None)
        self.assertEqual(cache.get(f"{self.session_id}_user_streak"), 0)

    def test_user_get_streak_score_authenticated_user(self):
        # No best streak stored yet, should create one
        cache.set(f"{self.session_id}_user_streak", 9)
        (
            current_score,
            game_over,
            best_streak,
        ) = self.game_service.user_get_streak_score(self.session_id, self.user, is_correct=False, remaining_to_guess=1)

        self.assertEqual(current_score, 9)
        self.assertFalse(game_over)  # training mode, no game over
        self.assertEqual(best_streak, 9)  # new best streak
        self.assertEqual(cache.get(f"{self.session_id}_user_streak"), 9)  # training, streak doesn't move
        created_stats = UserStats.objects.get(user=self.user, game_mode=self.game_service.GAME_MODE)
        self.assertEqual(created_stats.best_streak, 9)

        # Take the previous best streak into account
        cache.set(f"{self.session_id}_user_streak", 2)
        (
            current_score,
            game_over,
            best_streak,
        ) = self.game_service.user_get_streak_score(self.session_id, self.user, is_correct=False, remaining_to_guess=1)
        self.assertEqual(current_score, 2)
        self.assertEqual(best_streak, 9)  # got the already stored best streak
        self.assertEqual(cache.get(f"{self.session_id}_user_streak"), 2)  # training, streak doesn't move

        # Combo has another best streak
        cache.set(f"{self.session_id}_user_streak", 4)
        game_service = GameServiceGuessCountryFromFlagChallengeCombo
        UserStats.objects.create(user=self.user, game_mode=game_service.GAME_MODE, best_streak=10)
        (
            current_score,
            game_over,
            best_streak,
        ) = game_service.user_get_streak_score(self.session_id, self.user, is_correct=False, remaining_to_guess=1)
        self.assertEqual(current_score, 0)
        self.assertTrue(game_over)
        self.assertEqual(best_streak, 10)
        self.assertEqual(cache.get(f"{self.session_id}_user_streak"), 0)  # game over, streak reset to 0

    def test_should_cache_all_questions_at_session_start_when_in_challenge_mode(self):
        from core.models import Country

        Country.objects.all().delete()

        CountryFactory(name_en="France", iso2_code="FR")
        CountryFactory(name_en="Germany", iso2_code="DE")

        session_id = uuid4()

        GameServiceGuessCountryFromFlagChallengeCombo.get_questions(session_id)

        cached_data = cache.get(session_id)

        self.assertEqual(len(cached_data), 2)
        self.assertIn(0, cached_data)
        self.assertIn(1, cached_data)

    def test_should_send_all_questions_at_once_in_challenge_mode(self):
        from core.models import Country

        Country.objects.all().delete()

        iso2_codes = ["FR", "DE", "ES", "IT", "PT", "BE", "NL", "CH", "AT", "SE", "NO", "DK", "FI", "PL", "CZ"]
        iso3_codes = [
            "FRA",
            "DEU",
            "ESP",
            "ITA",
            "PRT",
            "BEL",
            "NLD",
            "CHE",
            "AUT",
            "SWE",
            "NOR",
            "DNK",
            "FIN",
            "POL",
            "CZE",
        ]
        for i in range(15):
            CountryFactory(name_en=f"Country{i}", iso2_code=iso2_codes[i], iso3_code=iso3_codes[i])

        session_id = uuid4()

        response = GameServiceGuessCountryFromFlagChallengeCombo.get_questions(session_id)
        self.assertEqual(len(response.questions), 15)


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
            "api.services.game_modes.training_modes.game_guess_capital_from_country.GameServiceGuessCapitalFromCountryTrainingInfinite.user_get"
        )
        self.addCleanup(patcher_user.stop)
        self.mock_user_get = patcher_user.start()
        self.mock_user_get.return_value = self.user

    def test_get_questions_stores_correct_data_in_cache(self):
        result = GameServiceGuessCapitalFromCountryTrainingInfinite.get_questions(self.session_id)

        self.assertIn(0, result.questions)
        self.assertEqual(result.questions[0], self.country.iso2_code)

        cached_data = cache.get(self.session_id)
        self.assertIsNotNone(cached_data)
        self.assertIn(0, cached_data)

    def test_check_answer_correct(self):
        GameServiceGuessCapitalFromCountryTrainingInfinite.get_questions(self.session_id)
        is_correct, country, remaining_cities = GameServiceGuessCapitalFromCountryTrainingInfinite.check_answer(
            self.session_id,
            0,
            self.city.pk,
            self.user,
        )
        self.assertTrue(is_correct)
        self.assertEqual(country, self.country)

    def test_check_answer_incorrect(self):
        GameServiceGuessCapitalFromCountryTrainingInfinite.get_questions(self.session_id)
        is_correct, country, remaining_cities = GameServiceGuessCapitalFromCountryTrainingInfinite.check_answer(
            self.session_id, 0, 9889798798797987, self.user
        )
        self.assertFalse(is_correct)
        self.assertEqual(country, self.country)

    def test_check_answer_invalid_question_index(self):
        GameServiceGuessCapitalFromCountryTrainingInfinite.get_questions(self.session_id)
        is_correct, country, remaining_cities = GameServiceGuessCapitalFromCountryTrainingInfinite.check_answer(
            self.session_id, 999, self.city.pk, self.user
        )
        self.assertFalse(is_correct)
        self.assertIsNone(country)
        self.assertEqual(remaining_cities, 0)

    def test_get_correct_answer(self):
        result = GameServiceGuessCapitalFromCountryTrainingInfinite.get_correct_answer(self.user, self.country, "en")
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].name.startswith(self.city.name_en))
        self.assertEqual(result[0].wikipedia_link, self.city.wikipedia_link_en)

    def test_check_answer_raises_value_error_if_multiple_countries(self):
        # Create a second country with the same city as the first one:
        # in theory, it is not possible, it should raise an error
        country2 = CountryFactory(name_en="Country2")
        country2.cities.add(self.city)

        # Cache questions
        questions_with_answer = {0: ([self.city.id], [])}
        cache.set(self.session_id, questions_with_answer)

        with self.assertRaises(ValueError) as cm:
            GameServiceGuessCapitalFromCountryTrainingInfinite.check_answer(
                session_id=self.session_id,
                question_index=0,
                answer_submitted="SomeAnswer",
                user=self.user,
            )

        self.assertIn("Multiple countries found for cities", str(cm.exception))
