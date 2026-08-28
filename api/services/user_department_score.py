import math
import random

from django.db.models import Count, Q
from django.utils import timezone

from core.models import Department, User, UserDepartmentScore
from core.models.user_country_score import GameModes


class UserDepartmentScoreService:
    DECAY_CONSTANT = 4000
    COOLDOWN = 2
    DEFAULT_FORGETTING_SCORE = 90
    DEFAULT_FAILURE_SCORE = 90

    def __init__(self, user: User, game_mode: GameModes):
        self.user = user
        self.user_department_scores = []
        self.game_mode = game_mode

    @property
    def is_game_mode_challenge(self):
        return "challenge" in self.game_mode.lower()

    @property
    def is_game_mode_training(self):
        return "training" in self.game_mode.lower()

    @staticmethod
    def _compute_question_weight(failure_score: float, forgetting_score: float):
        weight = (failure_score * 0.6 + forgetting_score * 0.4) / 100
        return max(weight, 0.0001)  # Ensure minimum weight to avoid division by zero

    def _compute_failure_score(self, guesses: list):
        """
        Retourne un score entre 0 et 100 où plus proche de 100 signifie plus d'échecs,
        donc qu'il y a "urgence" à poser la question
        """
        if len(guesses) == 0:
            return self.DEFAULT_FAILURE_SCORE  # on met un score au milieu

        total_weight = 0
        failure_weight = 0
        datetime_now = timezone.now()
        for guess in guesses:
            minutes_ago = (datetime_now - guess["created_at"]).total_seconds() / 60
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
        """
        if not last_guess:
            return self.DEFAULT_FORGETTING_SCORE  # middle score

        last_asked = last_guess["created_at"]
        datetime_now = timezone.now()
        t_minutes = max((datetime_now - last_asked).total_seconds() / 60, 1)

        log_result = math.log(t_minutes, 10)

        retention_factor = (100 * 1.84) / (math.pow(log_result, 1.25) + 1.84)

        return min(100 - retention_factor, 100)

    def compute_weight(self, user_department_score: UserDepartmentScore):
        guesses = user_department_score.user_guesses.values("created_at", "is_correct")
        guesses = list(guesses)
        last_guess = max(guesses, key=lambda g: g["created_at"]) if guesses else None

        failure_score = self._compute_failure_score(guesses)
        forgetting_score = self._compute_forgetting_score(last_guess)

        question_weight = self._compute_question_weight(failure_score, forgetting_score)

        return {
            "user_department_score": user_department_score,
            "department": user_department_score.department,
            "weight": round(question_weight, 4),
            "failure_score": round(failure_score, 2),
            "forgetting_score": round(forgetting_score, 2),
        }

    def get_default_weight(self, department: Department):
        """
        Weight for a department without any UserDepartmentScore yet. Default values.
        """
        return {
            "user_department_score": None,
            "department": department,
            "weight": self._compute_question_weight(self.DEFAULT_FAILURE_SCORE, self.DEFAULT_FORGETTING_SCORE),
            "failure_score": self.DEFAULT_FAILURE_SCORE,
            "forgetting_score": self.DEFAULT_FORGETTING_SCORE,
        }

    def compute_questions(self, last_question: str | None) -> list[Department]:
        selection_len = 10
        if not self.user.is_authenticated or self.is_game_mode_challenge:
            departments = Department.objects.all()
            if self.is_game_mode_challenge:
                departments_list = list(departments)
                random.shuffle(departments_list)
                return departments_list
            else:
                # Training mode is not available for anonymous users, but keep this line for now.
                return departments.order_by("?")[0:selection_len]
        else:
            # Apply the algorithm
            return self.personalized_questions(selection_len, last_question)

    def personalized_questions(self, selection_len: int, last_question: str | None) -> list[Department]:
        datetime_now = timezone.now()

        departments_without_score = Department.objects.none()
        # The cooldown can be too harsh depending on the user's speed
        # Reduce it until we find results
        for cooldown_seconds in range(self.COOLDOWN * 60, -1, -30):
            cooldown_threshold = datetime_now - timezone.timedelta(seconds=cooldown_seconds)

            user_department_scores = UserDepartmentScore.objects.filter(
                user=self.user,
                game_mode=self.game_mode,
                updated_at__lte=cooldown_threshold,
            )
            self.user_department_scores = list(user_department_scores)

            # We need to ask departments that have never been asked before, or that have no score yet.
            departments_without_score = Department.objects.annotate(
                score_count=Count(
                    "department_scores",
                    filter=Q(department_scores__user=self.user, department_scores__game_mode=self.game_mode),
                )
            ).filter(score_count=0)

            if self.user_department_scores or departments_without_score:
                break

        # Step 1: Compute weights
        scored_questions = [self.compute_weight(q) for q in self.user_department_scores]
        # Add never seen departments if any (no score yet, but we need to ask)
        if departments_without_score.exists():
            scored_questions.extend([self.get_default_weight(d) for d in departments_without_score])

        # Step 2: Normalize the weights (total amount of "chance" available)
        total_weight = sum(q["weight"] for q in scored_questions)

        # Now each weight is divided by the total to convert it into a percentage of the total (values between 0 and 1).
        # E.g., if a question has weight 5 and the total is 20, its normalized weight becomes 0.25 → it gets a 25% chance of being picked.
        for q in scored_questions:
            q["normalized_weight"] = q["weight"] / total_weight

        selection = []
        for _ in range(selection_len):
            # Step 3: Weighted random selection
            # picking a random point.
            rand_val = random.uniform(0, sum(q["normalized_weight"] for q in scored_questions))  # nosec
            cumulative = 0
            for q in scored_questions:
                # Cumulative is a way of checking each weight, the bigger the weight the more likely it is to be in the rand_val
                cumulative += q["normalized_weight"]
                # The first time the cumulative chance exceeds the rand_val, we stop
                if cumulative >= rand_val:
                    chosen = q["department"]
                    selection.append(chosen)
                    scored_questions.remove(q)
                    break

        # Avoid re-asking the same department twice in a row
        # This can happen if the cooldown was so small (or inexistant)
        # that the last question is able to be in the possible selected departments again
        first_selection = selection[0] if selection else None
        if first_selection and first_selection.number == last_question:
            selection = selection[1:] + [first_selection]

        return selection
