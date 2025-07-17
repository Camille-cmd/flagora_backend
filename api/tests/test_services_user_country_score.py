from freezegun import freeze_time
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from api.services.user_country_score import UserCountryScoreService
from core.tests.factories import (
    CountryFactory,
    GuessFactory,
    UserCountryScoreFactory,
)
from flagora.tests.base import FlagoraTestCase

class UserCountryScoreServiceTestCase(FlagoraTestCase):

    def setUp(self):
        super().setUp()
        self.score = UserCountryScoreFactory(user=self.user, country=self.country)
        with freeze_time("2025-06-07 18:00:00"):
            self.now = timezone.now()

    def add_guesses(self, is_correct_list, spacing_minutes=5):
        """
        Utility to add guesses to self.score spaced by `spacing_minutes`.
        """
        guesses = []
        for i, is_correct in enumerate(is_correct_list):
            created_at = self.now - timedelta(minutes=i * spacing_minutes)
            guess = GuessFactory(is_correct=is_correct, created_at=created_at)
            self.score.user_guesses.add(guess)
            guesses.append(guess)
        return guesses

class TestUserCountryScoreService(UserCountryScoreServiceTestCase):
    
    def test_failure_score_empty(self):
        service = UserCountryScoreService(self.user)
        service.datetime_now = self.now
        score = service._compute_failure_score([])
        self.assertEqual(score, 70)

    def test_failure_score_all_failures(self):
        service = UserCountryScoreService(self.user)
        service.datetime_now = self.now
        guesses = [{"is_correct": False, "created_at": self.now - timedelta(minutes=5)} for _ in range(3)]
        score = service._compute_failure_score(guesses)
        self.assertGreaterEqual(score, 99)  # Should be near 100

    def test_failure_score_mixed(self):
        service = UserCountryScoreService(self.user)
        service.datetime_now = self.now
        guesses = [
            {"is_correct": False, "created_at": self.now - timedelta(minutes=5)},
            {"is_correct": True, "created_at": self.now - timedelta(minutes=10)},
        ]
        score = service._compute_failure_score(guesses)
        self.assertTrue(0 < score < 100)

class ComputeForgettingScoreTest(UserCountryScoreServiceTestCase):

    def test_forgetting_score_no_guess(self):
        service = UserCountryScoreService(self.user)
        service.datetime_now = self.now
        score = service._compute_forgetting_score(None)
        self.assertEqual(score, 70)

    def test_forgetting_score_recent_guess(self):
        service = UserCountryScoreService(self.user)
        service.datetime_now = self.now
        guess = {"created_at": self.now - timedelta(minutes=1)}
        score = service._compute_forgetting_score(guess)
        self.assertLess(score, 40)

    def test_forgetting_score_old_guess(self):
        service = UserCountryScoreService(self.user)
        service.datetime_now = self.now
        guess = {"created_at": self.now - timedelta(days=180)}
        score = service._compute_forgetting_score(guess)
        self.assertGreater(score, 80)

class ComputeWeightTest(UserCountryScoreServiceTestCase):

    def test_weight_with_no_guesses(self):
        service = UserCountryScoreService(self.user)
        service.datetime_now = self.now
        result = service.compute_weight(self.score)

        self.assertIn("weight", result)
        self.assertEqual(result["failure_score"], 70)
        self.assertEqual(result["forgetting_score"], 70)

    def test_weight_with_mixed_guesses(self):
        self.add_guesses([False, True, False])
        service = UserCountryScoreService(self.user)
        service.datetime_now = self.now

        result = service.compute_weight(self.score)
        self.assertIn("weight", result)
        self.assertTrue(0 < result["weight"] < 1)

class ComputeQuestionsTest(UserCountryScoreServiceTestCase):

    @patch("api.services.user_country_score.UserCountryScoreService.compute_weight")
    @patch("random.random")
    def test_compute_questions_weighted_random(self, mock_random, mock_weight):
        # Add multiple scores
        scores = [
            UserCountryScoreFactory(user=self.user, country=CountryFactory(), user_guesses=GuessFactory.create_batch(2))
            for _ in range(3)
        ]

        # Patch weights
        mock_weight.side_effect = [
            {"user_country_score": score, "weight": w, "failure_score": 0, "forgetting_score": 0}
            for score, w in zip(scores, [0.1, 0.3, 0.6])
        ]

        # Always pick the highest
        mock_random.return_value = 0.9

        service = UserCountryScoreService(self.user)
        service.datetime_now = self.now

        result = service.compute_questions()

        self.assertEqual(len(result), 10)
        self.assertTrue(all(isinstance(c, type(self.country)) for c in result))

    @patch("api.services.user_country_score.UserCountryScoreService.compute_weight")
    def test_compute_questions_no_recent_guesses(self, mock_weight):
        self.user.user_scores.all().delete()

        # Score 1: Last guess was just now → should be excluded
        guess = GuessFactory()
        recent_score = UserCountryScoreFactory(user=self.user, country=CountryFactory(iso2_code="TT"), user_guesses=[guess])
        # New guess updates the score
        recent_score.updated_at=self.now - timedelta(minutes=1)
        recent_score.save()

        # Score 2: Last guess was old enough → should be included
        guess = GuessFactory()
        old_score = UserCountryScoreFactory(user=self.user, country=CountryFactory(iso2_code="DD"), user_guesses=[guess])
        old_score.updated_at=self.now - timedelta(minutes=10)
        old_score.save()

        # Score 3: No guesses at all → should be included
        no_guess_score = UserCountryScoreFactory(user=self.user, country=CountryFactory(iso2_code="PP"))

        # Patch compute_weight to make test predictable
        mock_weight.side_effect = lambda score: {
            "user_country_score": score,
            "weight": 1.0,
            "failure_score": 50,
            "forgetting_score": 50,
        }

        service = UserCountryScoreService(self.user)
        service.datetime_now = self.now

        questions = service.compute_questions()

        selected_countries = {c.pk for c in questions}
        expected_countries = {
            old_score.country.pk,
            no_guess_score.country.pk,
        }
        # Assert all selected countries are only from valid (non-recent) scores
        self.assertTrue(expected_countries.issubset(selected_countries))
        self.assertNotIn(recent_score.country.pk, selected_countries)


    def test_compute_questions_no_user_guesses(self):
        service = UserCountryScoreService(AnonymousUser())
        service.datetime_now = self.now
        result = service.compute_questions()
        # Only one country available
        self.assertEqual(len(result), 1)
