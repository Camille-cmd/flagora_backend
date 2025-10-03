import math
import random

from django.utils import timezone

from core.models import Country, User, UserCountryScore
from core.models.user_country_score import GameModes


class UserCountryScoreService:
    DECAY_CONSTANT = 4000
    COOLDOWN = 5
    DEFAULT_FORGETTING_SCORE = 70
    DEFAULT_FAILURE_SCORE = 70

    def __init__(self, user: User, game_mode: GameModes, continents: list[str] | None = None):
        self.user = user
        self.datetime_now = timezone.now()
        self.user_country_scores = []
        self.game_mode = game_mode
        self.continents = continents

    def _compute_failure_score(self, guesses: list):
        """
        Retourne un score entre 0 et 100 où plus proche de 100 signifie plus d'échecs,
        donc qu'il y a "urgence" à poser la question
        Args:
            guesses:

        Returns:

        """
        if len(guesses) == 0:
            return self.DEFAULT_FAILURE_SCORE  # on met un score au milieu

        total_weight = 0
        failure_weight = 0
        for guess in guesses:
            minutes_ago = (self.datetime_now - guess["created_at"]).total_seconds() / 60
            weight = math.exp(-minutes_ago / self.DECAY_CONSTANT)

            if guess["is_correct"] is False:
                failure_weight += weight

            total_weight += weight

        failure_score = (failure_weight / total_weight) * 100
        return min(failure_score, 100)

    def _compute_forgetting_score(self, last_guess: dict):
        """
        Score entre 0 et 100, plus proche de 100, plus la probabilité d'oubli est élevée.
        Plus proche de 100 signifie qu'il y a "urgence" de poser la question
        Args:
            last_guess:

        Returns:
        """
        if not last_guess:
            return self.DEFAULT_FORGETTING_SCORE  # middle score

        last_asked = last_guess["created_at"]
        t_minutes = max((self.datetime_now - last_asked).total_seconds() / 60, 1)

        log_result = math.log(t_minutes, 10)

        retention_factor = (100 * 1.84) / (math.pow(log_result, 1.25) + 1.84)

        return min(100 - retention_factor, 100)

    @staticmethod
    def _compute_question_weight(failure_score: float, forgetting_score: float):
        return (failure_score * 0.7 + forgetting_score * 0.4) / 100

    def compute_weight(self, user_country_score: UserCountryScore):
        guesses = user_country_score.user_guesses.values("created_at", "is_correct")
        guesses = list(guesses)
        last_guess = max(guesses, key=lambda g: g["created_at"]) if guesses else None

        failure_score = self._compute_failure_score(guesses)
        forgetting_score = self._compute_forgetting_score(last_guess)

        question_weight = self._compute_question_weight(failure_score, forgetting_score)

        return {
            "user_country_score": user_country_score,
            "country": user_country_score.country,
            "weight": round(question_weight, 4),
            "failure_score": round(failure_score, 2),
            "forgetting_score": round(forgetting_score, 2),
        }

    def get_default_weight(self, country: Country):
        """
        Weight for a country without any UserCountryScore yet. Default values.
        """
        return {
            "user_country_score": None,
            "country": country,
            "weight": self._compute_question_weight(self.DEFAULT_FAILURE_SCORE, self.DEFAULT_FORGETTING_SCORE),
            "failure_score": self.DEFAULT_FAILURE_SCORE,
            "forgetting_score": self.DEFAULT_FORGETTING_SCORE,
        }

    @property
    def is_game_mode_challenge(self):
        return "challenge" in self.game_mode.lower()

    @property
    def is_game_mode_training(self):
        return "training" in self.game_mode.lower()

    @property
    def is_game_mode_gcff(self):
        return "gcff" in self.game_mode.lower()

    @property
    def is_game_mode_gcfc(self):
        return "gcfc" in self.game_mode.lower()

    def get_valid_countries_filter(self, queryset):
        if self.is_game_mode_gcff:
            return queryset.exclude(flag__isnull=True).exclude(flag="")
        elif self.is_game_mode_gcfc:
            return queryset.filter(cities__is_capital=True).distinct()
        return queryset

    def compute_questions(self) -> list[Country]:
        pack_len = 10
        if not self.user.is_authenticated or self.is_game_mode_challenge:
            countries = Country.objects.all()
            if self.continents:
                countries = countries.filter(continent__in=self.continents)
            countries = self.get_valid_countries_filter(countries)

            if self.is_game_mode_challenge:
                countries_list = list(countries)
                random.shuffle(countries_list)
                return countries_list
            else:
                return countries.order_by("?")[0:pack_len]
        else:
            # Apply the algorithm
            return self.personalized_questions(pack_len)

    def personalized_questions(self, pack_len: int) -> list[Country]:
        cooldown_threshold = self.datetime_now - timezone.timedelta(minutes=self.COOLDOWN)
        user_country_scores = UserCountryScore.objects.filter(
            user=self.user, updated_at__lte=cooldown_threshold, game_mode=self.game_mode
        )

        if self.continents:
            user_country_scores = user_country_scores.filter(country__continent__in=self.continents)

        if self.is_game_mode_gcff:
            user_country_scores = user_country_scores.exclude(country__flag__isnull=True).exclude(country__flag="")
        elif self.is_game_mode_gcfc:
            user_country_scores = user_country_scores.filter(country__cities__is_capital=True).distinct()

        self.user_country_scores = user_country_scores

        countries_without_score = Country.objects.exclude(
            country_scores__game_mode=self.game_mode,
            country_scores__user=self.user,
        )
        if self.continents:
            countries_without_score = countries_without_score.filter(continent__in=self.continents)
        countries_without_score = self.get_valid_countries_filter(countries_without_score)

        # Step 1: Compute weights
        scored_questions = [self.compute_weight(q) for q in self.user_country_scores]
        # Add never seen countries if any (no score yet, but we need to ask)
        if countries_without_score.exists():
            scored_questions.extend([self.get_default_weight(c) for c in countries_without_score])

        # Step 2: Normalize the weights (total amount of "chance" available)
        total_weight = sum(q["weight"] for q in scored_questions)

        # Now each weight is divided by the total to convert it into a percentage of the total (values between 0 and 1).
        # E.g., if a question has weight 5 and the total is 20, its normalized weight becomes 0.25 → it gets a 25% chance of being picked.
        for q in scored_questions:
            q["normalized_weight"] = q["weight"] / total_weight

        selection = []
        for _ in range(pack_len):
            # Step 3: Weighted random selection
            # picking a random point.
            rand_val = random.random()  # nosec
            cumulative = 0
            for q in scored_questions:
                # Cumulative is a way of checking each weight, the bigger the weight the more likely it is to be in the rand_val
                cumulative += q["normalized_weight"]
                # The first time the cumulative chance exceeds the rand_val, we stop
                if rand_val <= cumulative:
                    chosen = q["country"]
                    selection.append(chosen)
                    break

        return selection
