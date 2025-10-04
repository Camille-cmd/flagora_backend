import random
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from freezegun import freeze_time

from api.services.user_country_score import UserCountryScoreService
from core.models import Country, Guess, UserCountryScore
from core.models.user_country_score import GameModes
from core.tests.factories import CityFactory, CountryFactory, GuessFactory, UserCountryScoreFactory
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


class UserCountryScoreServiceTest(UserCountryScoreServiceTestCase):
    def test_failure_score_empty(self):
        service = UserCountryScoreService(self.user, GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE)
        service.datetime_now = self.now
        score = service._compute_failure_score([])
        self.assertEqual(score, 70)

    def test_failure_score_all_failures(self):
        service = UserCountryScoreService(self.user, GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE)
        service.datetime_now = self.now
        guesses = [{"is_correct": False, "created_at": self.now - timedelta(minutes=5)} for _ in range(3)]
        score = service._compute_failure_score(guesses)
        self.assertGreaterEqual(score, 99)  # Should be near 100

    def test_failure_score_mixed(self):
        service = UserCountryScoreService(self.user, GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE)
        service.datetime_now = self.now
        guesses = [
            {"is_correct": False, "created_at": self.now - timedelta(minutes=5)},
            {"is_correct": True, "created_at": self.now - timedelta(minutes=10)},
        ]
        score = service._compute_failure_score(guesses)
        self.assertTrue(0 < score < 100)


class ComputeForgettingScoreTest(UserCountryScoreServiceTestCase):
    def test_forgetting_score_no_guess(self):
        service = UserCountryScoreService(self.user, GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE)
        service.datetime_now = self.now
        score = service._compute_forgetting_score(None)
        self.assertEqual(score, 70)

    def test_forgetting_score_recent_guess(self):
        service = UserCountryScoreService(self.user, GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE)
        guess = {"created_at": self.now - timedelta(minutes=1)}
        with freeze_time(self.now):
            score = service._compute_forgetting_score(guess)
        self.assertLess(score, 40)

    def test_forgetting_score_old_guess(self):
        service = UserCountryScoreService(self.user, GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE)
        guess = {"created_at": self.now - timedelta(days=180)}
        with freeze_time(self.now):
            score = service._compute_forgetting_score(guess)
        self.assertGreater(score, 80)


class ComputeWeightTest(UserCountryScoreServiceTestCase):
    def test_weight_with_no_guesses(self):
        service = UserCountryScoreService(self.user, GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE)
        result = service.compute_weight(self.score)

        self.assertIn("weight", result)
        self.assertEqual(result["failure_score"], 70)
        self.assertEqual(result["forgetting_score"], 70)

    def test_weight_with_mixed_guesses(self):
        self.add_guesses([False, True, False])
        service = UserCountryScoreService(self.user, GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE)

        result = service.compute_weight(self.score)
        self.assertIn("weight", result)
        self.assertTrue(0 < result["weight"] < 1)


class ComputeQuestionsTest(UserCountryScoreServiceTestCase):
    def test_compute_questions_weighted_random(self):
        # Add multiple scores
        UserCountryScore.objects.all().delete()
        for index in range(10):
            iso2_code = f"{random.randint(0, 9)}{index}"
            iso3_code = f"{random.randint(0, 9)}{index}{random.randint(0, 9)}"
            UserCountryScoreFactory(
                user=self.user,
                country=CountryFactory(iso2_code=iso2_code, iso3_code=iso3_code),
                user_guesses=GuessFactory.create_batch(2),
                game_mode=GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE,
            )

        # Update to avoid triggering the auto_now on the updated_at field
        UserCountryScore.objects.all().update(updated_at=self.now - timedelta(minutes=10))

        service = UserCountryScoreService(self.user, GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE)
        with freeze_time(self.now):
            result = service.compute_questions(last_question=None)

        self.assertEqual(len(result), 10)
        self.assertTrue(all(isinstance(c, type(self.country)) for c in result))

    @patch("api.services.user_country_score.UserCountryScoreService.compute_weight")
    def test_compute_questions_no_recent_guesses(self, mock_weight):
        # Delete all existing scores for this user
        self.user.user_scores.all().delete()
        Guess.objects.all().delete()

        # Score 1: Last guess was just now → should be excluded
        guess = GuessFactory()
        recent_score = UserCountryScoreFactory(
            user=self.user,
            game_mode=GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE,
            country=CountryFactory(name_en="Papua New Guinea", iso2_code="PG"),
            user_guesses=[guess],
        )
        # New guess updates the score
        # Update to avoid triggering the auto_now on the updated_at field
        UserCountryScore.objects.filter(pk=recent_score.pk).update(updated_at=self.now - timedelta(minutes=1))

        # Score 2: Last guess was old enough → should be included
        guess = GuessFactory()
        old_score = UserCountryScoreFactory(
            user=self.user,
            country=CountryFactory(name_en="Costa Rica", iso2_code="CR"),
            game_mode=GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE,
            user_guesses=[guess],
        )
        UserCountryScore.objects.filter(pk=old_score.pk).update(updated_at=self.now - timedelta(minutes=10))

        # Score 3: No guesses at all → should be included
        no_guess_country = self.country

        # Patch compute_weight to make test predictable
        mock_weight.side_effect = lambda score: {
            "user_country_score": score,
            "country": score.country,
            "weight": 1.0,
            "failure_score": 50,
            "forgetting_score": 50,
        }

        service = UserCountryScoreService(self.user, GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE)

        with freeze_time(self.now):
            questions = list(service.compute_questions(last_question=None))
        selected_countries = {c.pk for c in questions}
        expected_countries = {
            old_score.country.pk,
            no_guess_country.pk,
        }
        # Assert all selected countries are only from valid (non-recent) scores
        self.assertTrue(expected_countries.issubset(selected_countries))
        self.assertNotIn(recent_score.country.pk, selected_countries)

    def test_compute_questions_no_user_guesses(self):
        service = UserCountryScoreService(AnonymousUser(), GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE)
        with freeze_time(self.now):
            result = service.compute_questions(last_question=None)
        self.assertEqual(len(result), 1)

    def test_compute_questions_no_user_guesses_in_challenge_mode(self):
        from core.models import Country

        Country.objects.all().delete()
        CountryFactory(name_en="Country1", iso2_code="C1")

        service = UserCountryScoreService(AnonymousUser(), GameModes.GUESS_COUNTRY_FROM_FLAG_CHALLENGE_COMBO)
        with freeze_time(self.now):
            result = service.compute_questions(last_question=None)
        self.assertEqual(len(result), 1)

    def test_should_exclude_country_when_flag_is_missing(self):
        country_without_flag = CountryFactory(flag=None)

        service = UserCountryScoreService(self.user, GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE)
        with freeze_time(self.now):
            questions = service.compute_questions(last_question=None)

        self.assertNotIn(country_without_flag, questions)

    def test_should_include_country_when_flag_exists(self):
        country_with_flag = CountryFactory()

        service = UserCountryScoreService(self.user, GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE)
        with freeze_time(self.now):
            questions = service.compute_questions(last_question=None)

        self.assertIn(country_with_flag, questions)

    def test_should_exclude_country_when_capital_is_missing(self):
        country_without_capital = CountryFactory(cities=[])

        service = UserCountryScoreService(self.user, GameModes.GUESS_CAPITAL_FROM_COUNTRY_TRAINING_INFINITE)
        with freeze_time(self.now):
            questions = service.compute_questions(last_question=None)

        self.assertNotIn(country_without_capital, questions)

    def test_should_include_country_when_capital_exists(self):
        capital_city = CityFactory(is_capital=True)
        country_with_capital = CountryFactory(cities=[capital_city])

        service = UserCountryScoreService(self.user, GameModes.GUESS_CAPITAL_FROM_COUNTRY_TRAINING_INFINITE)
        with freeze_time(self.now):
            questions = service.compute_questions(last_question=None)

        self.assertIn(country_with_capital, questions)

    def test_should_exclude_from_default_weights_when_flag_is_missing_for_never_attempted_country(self):
        UserCountryScore.objects.filter(user=self.user).delete()

        CountryFactory()
        country_without_flag = CountryFactory(flag=None)

        service = UserCountryScoreService(self.user, GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE)
        with freeze_time(self.now):
            questions = service.compute_questions(last_question=None)

        self.assertNotIn(country_without_flag, questions)

    def test_should_exclude_from_default_weights_when_capital_is_missing_for_never_attempted_country(self):
        UserCountryScore.objects.filter(user=self.user).delete()

        capital_city = CityFactory(is_capital=True)
        CountryFactory(cities=[capital_city])
        country_without_capital = CountryFactory(cities=[])

        service = UserCountryScoreService(self.user, GameModes.GUESS_CAPITAL_FROM_COUNTRY_TRAINING_INFINITE)
        with freeze_time(self.now):
            questions = service.compute_questions(last_question=None)

        self.assertNotIn(country_without_capital, questions)

    def test_should_only_validate_flags_when_in_gcff_mode(self):
        country_with_flag_no_capital = CountryFactory(cities=[])

        service = UserCountryScoreService(self.user, GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE)
        with freeze_time(self.now):
            questions = service.compute_questions(last_question=None)

        self.assertIn(country_with_flag_no_capital, questions)

    def test_should_only_validate_capitals_when_in_gcfc_mode(self):
        capital_city = CityFactory(is_capital=True)
        country_with_capital_no_flag = CountryFactory(flag=None, cities=[capital_city])

        service = UserCountryScoreService(self.user, GameModes.GUESS_CAPITAL_FROM_COUNTRY_TRAINING_INFINITE)
        with freeze_time(self.now):
            questions = service.compute_questions(last_question=None)

        self.assertIn(country_with_capital_no_flag, questions)

    def test_should_return_empty_list_when_no_valid_countries_available(self):
        from core.models import Country

        Country.objects.all().delete()

        CountryFactory(flag=None)

        service = UserCountryScoreService(self.user, GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE)
        with freeze_time(self.now):
            questions = service.compute_questions(last_question=None)

        self.assertEqual(len(questions), 0)

    def test_should_respect_cooldown_and_validation_when_both_apply(self):
        from core.models import Country

        Country.objects.all().delete()
        UserCountryScore.objects.all().delete()

        country_a = CountryFactory()
        country_b = CountryFactory()
        country_c = CountryFactory(flag=None)

        score_a = UserCountryScoreFactory(
            user=self.user, country=country_a, game_mode=GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE
        )
        score_b = UserCountryScoreFactory(
            user=self.user, country=country_b, game_mode=GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE
        )
        score_c = UserCountryScoreFactory(
            user=self.user, country=country_c, game_mode=GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE
        )

        UserCountryScore.objects.filter(pk=score_a.pk).update(updated_at=self.now - timedelta(minutes=1))
        UserCountryScore.objects.filter(pk=score_b.pk).update(updated_at=self.now - timedelta(minutes=10))
        UserCountryScore.objects.filter(pk=score_c.pk).update(updated_at=self.now - timedelta(minutes=10))

        service = UserCountryScoreService(self.user, GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE)

        with freeze_time(self.now):
            questions = service.compute_questions(last_question=None)

        self.assertNotIn(country_a, questions)
        self.assertIn(country_b, questions)
        self.assertNotIn(country_c, questions)

    def test_should_filter_countries_by_continent_when_continent_is_specified(self):
        from core.models import Country

        Country.objects.all().delete()

        european_country = CountryFactory(name_en="France", iso2_code="FR", continent="EU")
        asian_country = CountryFactory(name_en="Japan", iso2_code="JP", continent="AS")
        african_country = CountryFactory(name_en="Kenya", iso2_code="KE", continent="AF")
        north_american_country = CountryFactory(name_en="Canada", iso2_code="CA", continent="NA")

        service = UserCountryScoreService(
            self.user, GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE, continents=["EU", "AS"]
        )

        with freeze_time(self.now):
            questions = service.compute_questions(last_question=None)

        self.assertIn(european_country, questions)
        self.assertIn(asian_country, questions)
        self.assertNotIn(african_country, questions)
        self.assertNotIn(north_american_country, questions)

    def test_should_return_all_available_countries_when_requesting_questions_in_challenge_mode(self):
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
        countries = [
            CountryFactory(name_en=f"Country{i}", iso2_code=iso2_codes[i], iso3_code=iso3_codes[i]) for i in range(15)
        ]

        service = UserCountryScoreService(self.user, GameModes.GUESS_COUNTRY_FROM_FLAG_CHALLENGE_COMBO)
        with freeze_time(self.now):
            questions = service.compute_questions(last_question=None)

        self.assertEqual(len(questions), 15)
        for country in countries:
            self.assertIn(country, questions)

    def test_should_return_questions_without_duplicates_when_requesting_questions_in_challenge_mode(self):
        from core.models import Country

        Country.objects.all().delete()

        CountryFactory(name_en="France", iso2_code="FR")
        CountryFactory(name_en="Germany", iso2_code="DE")
        CountryFactory(name_en="Spain", iso2_code="ES")

        service = UserCountryScoreService(self.user, GameModes.GUESS_COUNTRY_FROM_FLAG_CHALLENGE_COMBO)
        with freeze_time(self.now):
            questions = service.compute_questions(last_question=None)

        country_ids = [c.id for c in questions]
        self.assertEqual(len(country_ids), len(set(country_ids)))

    def test_should_respect_country_filtering_when_requesting_all_questions_in_challenge_mode(self):
        from core.models import Country

        Country.objects.all().delete()

        country_with_flag = CountryFactory(name_en="France", iso2_code="FR")
        country_without_flag = CountryFactory(name_en="Invalid", iso2_code="XX", flag=None)

        service = UserCountryScoreService(self.user, GameModes.GUESS_COUNTRY_FROM_FLAG_CHALLENGE_COMBO)
        with freeze_time(self.now):
            questions = service.compute_questions(last_question=None)

        self.assertIn(country_with_flag, questions)
        self.assertNotIn(country_without_flag, questions)

    def test_should_respect_continent_filtering_when_requesting_all_questions_in_challenge_mode(self):
        from core.models import Country

        Country.objects.all().delete()

        european_country = CountryFactory(name_en="France", iso2_code="FR", continent="EU")
        asian_country = CountryFactory(name_en="Japan", iso2_code="JP", continent="AS")
        african_country = CountryFactory(name_en="Kenya", iso2_code="KE", continent="AF")

        service = UserCountryScoreService(
            self.user, GameModes.GUESS_COUNTRY_FROM_FLAG_CHALLENGE_COMBO, continents=["EU", "AS"]
        )
        with freeze_time(self.now):
            questions = service.compute_questions(last_question=None)

        self.assertIn(european_country, questions)
        self.assertIn(asian_country, questions)
        self.assertNotIn(african_country, questions)

    @patch("api.services.user_country_score.random.shuffle")
    def test_should_randomize_order_when_requesting_questions_in_challenge_mode(self, mock_shuffle):
        from core.models import Country

        Country.objects.all().delete()

        CountryFactory(name_en="France", iso2_code="FR")
        CountryFactory(name_en="Germany", iso2_code="DE")
        CountryFactory(name_en="Spain", iso2_code="ES")

        service = UserCountryScoreService(self.user, GameModes.GUESS_COUNTRY_FROM_FLAG_CHALLENGE_COMBO)
        with freeze_time(self.now):
            service.compute_questions(last_question=None)

        mock_shuffle.assert_called_once()

    @patch("random.random")
    @patch("api.services.user_country_score.UserCountryScoreService.compute_weight")
    def test_should_not_add_duplicate_country_in_single_batch_when_randomly_selected_twice(
        self, mock_weight, mock_random
    ):
        UserCountryScore.objects.all().delete()
        Country.objects.all().delete()

        country1 = CountryFactory(name_en="France", iso2_code="FR")
        country2 = CountryFactory(name_en="Germany", iso2_code="DE")

        score1 = UserCountryScoreFactory(
            user=self.user, country=country1, game_mode=GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE
        )
        score2 = UserCountryScoreFactory(
            user=self.user, country=country2, game_mode=GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE
        )

        UserCountryScore.objects.all().update(updated_at=self.now - timedelta(minutes=10))

        mock_weight.side_effect = [
            {
                "user_country_score": score1,
                "country": country1,
                "weight": 0.5,
                "failure_score": 50,
                "forgetting_score": 50,
            },
            {
                "user_country_score": score2,
                "country": country2,
                "weight": 0.5,
                "failure_score": 50,
                "forgetting_score": 50,
            },
        ]

        # Make random.random() always return 0.4, which will always select country1 (first country)
        mock_random.return_value = 0.4

        service = UserCountryScoreService(self.user, GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE)
        with freeze_time(self.now):
            questions = service.compute_questions(last_question=country1.iso2_code)

        country_ids = [c.id for c in questions]
        self.assertEqual(len(country_ids), len(set(country_ids)))

    @patch("random.random")
    @patch("api.services.user_country_score.UserCountryScoreService.compute_weight")
    def test_should_not_repeat_last_question_as_first_when_randomly_selected(self, mock_weight, mock_random):
        UserCountryScore.objects.all().delete()

        country1 = CountryFactory(name_en="France", iso2_code="FR")
        country2 = CountryFactory(name_en="Germany", iso2_code="DE")

        score1 = UserCountryScoreFactory(
            user=self.user, country=country1, game_mode=GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE
        )
        score2 = UserCountryScoreFactory(
            user=self.user, country=country2, game_mode=GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE
        )

        UserCountryScore.objects.all().update(updated_at=self.now - timedelta(minutes=10))

        mock_weight.side_effect = [
            {
                "user_country_score": score1,
                "country": country1,
                "weight": 0.5,
                "failure_score": 50,
                "forgetting_score": 50,
            },
            {
                "user_country_score": score2,
                "country": country2,
                "weight": 0.5,
                "failure_score": 50,
                "forgetting_score": 50,
            },
        ]

        # Make random.random() always select country1 first
        mock_random.return_value = 0.4

        service = UserCountryScoreService(self.user, GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE)

        with freeze_time(self.now):
            questions = service.compute_questions(last_question=country1.iso2_code)

        self.assertNotEqual(questions[0].iso2_code, country1.iso2_code)
