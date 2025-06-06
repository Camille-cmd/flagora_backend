import random
from datetime import datetime

import math
from django.db.models import Subquery, OuterRef, Q
from django.utils import timezone

from core.models import Country, User, UserCountryScore, Guess


class UserCountryScoreService:
    DECAY_CONSTANT = 4000
    COOLDOWN = 5

    def __init__(self, user: User):
        self.user = user
        self.datetime_now = timezone.now()
        self.user_country_scores = []

    def _compute_failure_score(self, guesses: list):
        """
        Retourne un score entre 0 et 100 où plus proche de 100 signifie plus d'échecs,
        donc qu'il y a "urgence" à poser la question
        Args:
            guesses:

        Returns:

        """
        if len(guesses) == 0:
            return 70  # on met un score au milieu

        total_weight = 0
        failure_weight = 0
        for guess in guesses:
            minutes_ago = (self.datetime_now - guess["created_at"]).total_seconds() / 60
            weight = math.exp(-minutes_ago / self.DECAY_CONSTANT)

            if guess["is_correct"] is False:
                failure_weight += weight

            total_weight += weight

        failure_score = (failure_weight / total_weight)*100
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
            return 70  # middle score

        last_asked = last_guess["created_at"]
        t_minutes = max((self.datetime_now - last_asked).total_seconds() / 60, 1)

        log_result = math.log(t_minutes, 10)

        retention_factor = (100 * 1.84) / (math.pow(log_result, 1.25) + 1.84)

        return min(100 - retention_factor, 100)

    def compute_weight(self, user_country_score: UserCountryScore):
        guesses = user_country_score.user_guesses.values("created_at", "is_correct")
        guesses = list(guesses)
        last_guess = max(guesses, key=lambda g: g["created_at"]) if guesses else None

        failure_score = self._compute_failure_score(guesses)
        forgetting_score = self._compute_forgetting_score(last_guess)

        question_weight = (failure_score * 0.7 + forgetting_score * 0.4) / 100

        return {
            "user_country_score": user_country_score,
            "weight":  round(question_weight, 4),
            "failure_score": round(failure_score, 2),
            "forgetting_score": round(forgetting_score, 2)
        }


    def compute_questions(self) -> list[Country]:
        pack_len = 10
        if not self.user.is_authenticated:
            return Country.objects.order_by('?')[0:pack_len]

        latest_guess_subquery = (
            Guess.objects
            .filter(user_scores=OuterRef('pk'))
            .order_by('-created_at')
            .values('created_at')[:1]
        )
        # TODO : GAME MODE
        cooldown_threshold = self.datetime_now - timezone.timedelta(minutes=self.COOLDOWN)
        self.user_country_scores = (
            UserCountryScore.objects
            .filter(user=self.user)
            # Ignore if a guess has been made too recently
            .annotate(latest_guess_time=Subquery(latest_guess_subquery))
            .filter(Q(latest_guess_time__lte=cooldown_threshold) | Q(latest_guess_time__isnull=True))
        )

        # Step 1: Compute weights
        scored_questions = [self.compute_weight(q) for q in self.user_country_scores.all()]

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
            rand_val = random.random()
            cumulative = 0
            for q in scored_questions:
                # Cumulative is a way of checking each weight, the bigger the weight the more likely it is to be in the rand_val
                cumulative += q["normalized_weight"]
                # The first time the cumulative chance exceeds the rand_val, we stop
                if rand_val <= cumulative:
                    chosen = q["user_country_score"].country
                    selection.append(chosen)
                    break

        return selection
