from datetime import timedelta
from unittest.mock import patch

import freezegun
from django.utils import timezone
from freezegun import freeze_time

from core.models import Guess, UserCountryScore, UserStats
from core.models.user_country_score import GameModes
from core.services.stats_sevices import user_get_stats
from core.tests.factories import CityFactory, CountryFactory, GuessFactory, UserCountryScoreFactory
from flagora.tests.base import FlagoraTestCase


class UserStatsTestCase(FlagoraTestCase):
    def setUp(self):
        super().setUp()

        # Create additional test data
        self.country2 = CountryFactory(
            name_fr="France",
            name_en="France",
            iso2_code="FR",
            iso3_code="FRA",
        )

        self.city2 = CityFactory(
            name_fr="Paris",
            name_en="Paris",
            is_capital=True,
        )
        self.country2.cities.add(self.city2)

        # Create another country for variety
        self.country3 = CountryFactory(
            name_fr="Allemagne",
            name_en="Germany",
            iso2_code="DE",
            iso3_code="DEU",
        )

        self.city3 = CityFactory(
            name_fr="Berlin",
            name_en="Berlin",
            is_capital=True,
        )
        self.country3.cities.add(self.city3)

        with freeze_time("2025-08-22 18:00:00"):
            self.now = timezone.now()

        self.stats = UserStats.objects.create(
            user=self.user, game_mode=GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE
        )

    def create_user_scores_and_guesses(self, game_mode, country_guess_data):
        """
        Helper method to create user scores and guesses for testing.

        Args:
            game_mode: The game mode to test
            country_guess_data: List of tuples (country, [is_correct_list])
        """
        scores = []
        all_guesses = []

        for country, correct_results in country_guess_data:
            score = UserCountryScoreFactory(user=self.user, country=country, game_mode=game_mode)
            scores.append(score)

            # Create guesses for this score
            for i, is_correct in enumerate(correct_results):
                guess = GuessFactory(is_correct=is_correct)
                score.user_guesses.add(guess)
                all_guesses.append(guess)

        return scores, all_guesses

    @patch("api.flag_store.flag_store")
    def test_user_get_stats_flag_guessing_mode(self, mock_flag_store):
        """Test user stats for flag guessing game mode."""
        mock_flag_store.get_path.return_value = "/flags/test.png"

        # Create test data
        country_guess_data = [
            (self.country, [True, True, True, False]),  # 75% success rate, 3 fails total
            (self.country2, [True, False, False, False]),  # 25% success rate, 1 fail total
            (self.country3, [True, True, False]),  # 66.67% success rate, 2 fails total
        ]

        self.create_user_scores_and_guesses(GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE, country_guess_data)

        # update best streak
        self.stats.best_streak = 3
        self.stats.save()

        # Call the function
        results = user_get_stats(self.user)

        # Find the flag guessing mode result
        flag_result = next(r for r in results if r.game_mode == GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE)

        # Assertions
        self.assertEqual(flag_result.stats.success_rate, 54.55)
        self.assertEqual(flag_result.stats.most_strikes, 3)  # Max consecutive correct

        # Most failed should be country2 (3 fails)
        self.assertEqual(flag_result.stats.most_failed.iso2_code, self.country2.iso2_code)
        self.assertEqual(flag_result.stats.most_failed.success_rate, 25.0)

        # Most correct should be country1 (3 correct)
        self.assertEqual(flag_result.stats.most_correctly_guessed.iso2_code, self.country.iso2_code)

    @patch("api.flag_store.flag_store")
    def test_user_get_stats_capital_guessing_mode(self, mock_flag_store):
        """Test user stats for capital guessing game mode."""
        mock_flag_store.get_path.return_value = "/flags/test.png"

        # Create test data for capital guessing
        country_guess_data = [
            (self.country, [True, False, True]),  # 2 correct, 1 fail
            (self.country2, [False, False, True]),  # 1 correct, 2 fails
        ]

        self.create_user_scores_and_guesses(
            GameModes.GUESS_CAPITAL_FROM_COUNTRY_TRAINING_INFINITE,
            country_guess_data,
        )

        # create best streak
        UserStats.objects.create(
            user=self.user, game_mode=GameModes.GUESS_CAPITAL_FROM_COUNTRY_TRAINING_INFINITE, best_streak=1
        )

        results = user_get_stats(self.user)

        capital_result = next(
            r for r in results if r.game_mode == GameModes.GUESS_CAPITAL_FROM_COUNTRY_TRAINING_INFINITE
        )

        # Assertions
        self.assertEqual(capital_result.stats.success_rate, 50.0)  # 3/6 * 100
        self.assertEqual(capital_result.stats.most_strikes, 1)

        # Most failed should be country2 (2 fails)
        self.assertEqual(capital_result.stats.most_failed.name, ["Paris"])
        self.assertEqual(capital_result.stats.most_failed.success_rate, 33.33)
        self.assertEqual(capital_result.stats.most_failed.country.iso2_code, "FR")

    def test_user_get_stats_no_data(self):
        """Test user stats when user has no guesses."""
        results = user_get_stats(self.user)

        # Should still return results for all game modes, but with zeros
        self.assertEqual(len(results), len(GameModes.values))
        for result in results:
            # Cities is a list of dicts, so we need to check the name attribute
            if "GCFF" in result.game_mode:
                expected_name = ""
            else:
                expected_name = [""]
            self.assertEqual(result.stats.success_rate, 0)
            self.assertEqual(result.stats.most_strikes, 0)
            self.assertEqual(result.stats.most_failed.name, expected_name)
            self.assertEqual(result.stats.most_correctly_guessed.name, expected_name)

    @patch("api.flag_store.flag_store")
    def test_user_get_stats_old_guesses_filtered(self, mock_flag_store):
        """Test that guesses older than 365 days are filtered out."""
        mock_flag_store.get_path.return_value = "/flags/test.png"

        score = UserCountryScoreFactory(
            user=self.user, country=self.country, game_mode=GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE
        )
        # Create old guess (should be filtered out)
        guess1 = GuessFactory(is_correct=True)
        # Update to avoid triggering the auto_now on the updated_at field
        Guess.objects.filter(pk=guess1.pk).update(created_at=self.now - timedelta(days=400))
        # Create recent guess
        guess2 = GuessFactory(is_correct=False)
        Guess.objects.filter(pk=guess2.pk).update(created_at=self.now - timedelta(days=10))
        score.user_guesses.add(guess1, guess2)

        results = user_get_stats(self.user)
        flag_result = next(r for r in results if r.game_mode == GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE)

        # Should only count the recent guess
        self.assertEqual(flag_result.stats.success_rate, 0.0)  # Only the False guess counted

    @patch("api.flag_store.flag_store")
    def test_user_language_handling(self, mock_flag_store):
        mock_flag_store.get_path.return_value = "/flags/test.png"

        """Test that user language is properly handled for country/city names."""
        # Change user language to French
        self.user.language = "fr"
        self.user.save()

        score = UserCountryScoreFactory(
            user=self.user, country=self.country, game_mode=GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE
        )

        guess = GuessFactory(is_correct=False)
        score.user_guesses.add(guess)

        results = user_get_stats(self.user)

        flag_result = next(r for r in results if r.game_mode == GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE)

        # Should use French name
        self.assertEqual(flag_result.stats.most_failed.name, "Groenland")

    @patch("api.flag_store.flag_store")
    def test_edge_case_single_guess(self, mock_flag_store):
        """Test edge case with only one guess."""
        mock_flag_store.get_path.return_value = "/flags/test.png"

        score = UserCountryScoreFactory(
            user=self.user, country=self.country, game_mode=GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE
        )

        guess = GuessFactory(is_correct=True)
        score.user_guesses.add(guess)

        # update best streak
        self.stats.best_streak = 1
        self.stats.save()

        results = user_get_stats(self.user)
        flag_result = next(r for r in results if r.game_mode == GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE)

        self.assertEqual(flag_result.stats.success_rate, 100.0)
        self.assertEqual(flag_result.stats.most_strikes, 1)

    def test_multiple_game_modes(self):
        """Test that all game modes are included in results."""
        results = user_get_stats(self.user)

        returned_game_modes = {r.game_mode for r in results}
        expected_game_modes = set(GameModes.values)

        self.assertEqual(returned_game_modes, expected_game_modes)
