from unittest.mock import patch
from uuid import uuid4

from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone

from api.services.game import GameService
from core.models import UserCountryScore, Guess
from flagora.tests.base import FlagoraTestCase


@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'isolated-test-cache',
    }
})
class GameServiceTest(FlagoraTestCase):

    def setUp(self):
        super().setUp()
        cache.clear()

        # Mocked Session
        self.session_id = uuid4()
        self.session_token = uuid4()
        self._create_mock_session(self.session_token, self.user.id)

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

    def test_user_accept_success(self):
        result = GameService.user_accept(self.session_id, self.session_token)
        cached_user_id = cache.get(f"{self.session_id}_user_id")

        self.assertTrue(result)
        self.assertEqual(cached_user_id, self.user.id)

    def test_user_accept_invalid_session(self):
        fake_token = uuid4()
        result = GameService.user_accept(self.session_id, fake_token)
        cached_user_id = cache.get(f"{self.session_id}_user_id")

        self.assertFalse(result)
        self.assertIsNone(cached_user_id)

    def test_user_get_authenticated_user(self):
        cache.set(f"{self.session_id}_user_id", self.user.id)
        user = GameService.user_get(self.session_id)

        self.assertTrue(user.is_authenticated)
        self.assertEqual(user.id, self.user.id)

    def test_user_get_anonymous_user(self):
        # No user present in cache
        user = GameService.user_get(self.session_id)
        self.assertFalse(user.is_authenticated)

    @patch("api.services.user_country_score.UserCountryScoreService.compute_questions")
    @patch("api.flag_store.flag_store.get_path")
    def test_get_questions(self, mock_get_path, mock_compute_questions):
        mock_compute_questions.return_value = [self.country]
        mock_get_path.return_value = "/mock/path/to/flag.svg"

        result = GameService.get_questions(self.session_id)

        self.assertIn(0, result.questions)
        self.assertEqual(result.questions[0], "/mock/path/to/flag.svg")

        # Check internal cache structure (used for answer validation)
        questions_with_answers = cache.get(self.session_id)
        self.assertEqual(questions_with_answers[0], self.country.iso2_code)

    def test_check_answer_correct(self):
        cache.set(self.session_id, {0: self.country.iso2_code})

        is_correct, country = GameService.check_answer(self.session_id, 0, self.country.iso2_code, self.user)

        self.assertTrue(is_correct)
        self.assertEqual(country.iso2_code, self.country.iso2_code)

    def test_check_answer_incorrect(self):
        cache.set(self.session_id, {0: self.country.iso2_code})

        is_correct, country = GameService.check_answer(self.session_id, 0, "FR", self.user)

        self.assertFalse(is_correct)
        self.assertEqual(country.iso2_code, self.country.iso2_code)

    def test_check_answer_invalid_index(self):
        cache.set(self.session_id, {0: self.country.iso2_code})

        is_correct, country = GameService.check_answer(self.session_id, 1, "FR", self.user)

        self.assertFalse(is_correct)
        self.assertIsNone(country)


    def test_guess_register(self):
        self.assertEqual(UserCountryScore.objects.count(), 0)
        self.assertEqual(Guess.objects.count(), 0)

        GameService.guess_register(self.user, is_correct=True, country=self.country)

        self.assertEqual(UserCountryScore.objects.count(), 1)
        self.assertEqual(Guess.objects.count(), 1)

        score = UserCountryScore.objects.first()
        self.assertEqual(score.user, self.user)
        self.assertEqual(score.country, self.country)
        self.assertTrue(score.user_guesses.first().is_correct)
