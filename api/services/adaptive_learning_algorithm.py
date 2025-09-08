import math
import random
from typing import Generic, TypeVar, Any, Dict, List, Protocol, TYPE_CHECKING

from django.db import models
from django.utils import timezone

from core.models import User
from core.models.user_country_score import GameModes

if TYPE_CHECKING:
    from django.db.models import QuerySet

# Type variables for generic types
EntityType = TypeVar('EntityType', bound=models.Model)  # Country, Department, etc.
ScoreType = TypeVar('ScoreType', bound=models.Model)   # UserCountryScore, UserDepartmentScore, etc.


class ScoreModelProtocol(Protocol):
    """Protocol defining the interface that score models must implement"""
    user: models.ForeignKey
    game_mode: str
    updated_at: models.DateTimeField
    user_guesses: models.ManyToManyField

    def __str__(self) -> str:
        ...


class AdaptiveLearningAlgorithm(Generic[EntityType, ScoreType]):
    """
    Generic adaptive learning algorithm for spaced repetition learning.
    
    This algorithm computes question weights based on:
    - Failure rate (how often the user gets it wrong)
    - Forgetting curve (how long since last attempt)
    - Spaced repetition with cooldown periods
    
    Type parameters:
    - EntityType: The entity being learned (Country, Department, etc.)
    - ScoreType: The score model tracking user performance (UserCountryScore, etc.)
    """
    
    DECAY_CONSTANT = 4000
    COOLDOWN = 5
    DEFAULT_FORGETTING_SCORE = 70
    DEFAULT_FAILURE_SCORE = 70

    def __init__(
        self, 
        user: User, 
        game_mode: GameModes,
        entity_model: type[EntityType],
        score_model: type[ScoreType],
        entity_field_name: str,  # Name of the field in score model that references the entity
        related_name: str        # Related name for reverse lookup from entity to scores
    ):
        self.user = user
        self.datetime_now = timezone.now()
        self.game_mode = game_mode
        self.entity_model = entity_model
        self.score_model = score_model
        self.entity_field_name = entity_field_name
        self.related_name = related_name

    def _compute_failure_score(self, guesses: List[Dict[str, Any]]) -> float:
        """
        Retourne un score entre 0 et 100 où plus proche de 100 signifie plus d'échecs,
        donc qu'il y a "urgence" à poser la question
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

    def _compute_forgetting_score(self, last_guess: Dict[str, Any] | None) -> float:
        """
        Score entre 0 et 100, plus proche de 100, plus la probabilité d'oubli est élevée.
        Plus proche de 100 signifie qu'il y a "urgence" de poser la question
        """
        if not last_guess:
            return self.DEFAULT_FORGETTING_SCORE  # middle score

        last_asked = last_guess["created_at"]
        t_minutes = max((self.datetime_now - last_asked).total_seconds() / 60, 1)

        log_result = math.log(t_minutes, 10)

        retention_factor = (100 * 1.84) / (math.pow(log_result, 1.25) + 1.84)

        return min(100 - retention_factor, 100)

    @staticmethod
    def _compute_question_weight(failure_score: float, forgetting_score: float) -> float:
        return (failure_score * 0.7 + forgetting_score * 0.4) / 100

    def compute_weight(self, score_instance: ScoreType) -> Dict[str, Any]:
        """Compute the learning weight for a specific score instance"""
        guesses = score_instance.user_guesses.values("created_at", "is_correct")
        guesses = list(guesses)
        last_guess = max(guesses, key=lambda g: g["created_at"]) if guesses else None

        failure_score = self._compute_failure_score(guesses)
        forgetting_score = self._compute_forgetting_score(last_guess)

        question_weight = self._compute_question_weight(failure_score, forgetting_score)

        entity = getattr(score_instance, self.entity_field_name)
        return {
            f"user_{self.entity_field_name}_score": score_instance,
            self.entity_field_name: entity,
            "weight": round(question_weight, 4),
            "failure_score": round(failure_score, 2),
            "forgetting_score": round(forgetting_score, 2),
        }

    def get_default_weight(self, entity: EntityType) -> Dict[str, Any]:
        """Weight for an entity without any score yet. Default values."""
        return {
            f"user_{self.entity_field_name}_score": None,
            self.entity_field_name: entity,
            "weight": self._compute_question_weight(self.DEFAULT_FAILURE_SCORE, self.DEFAULT_FORGETTING_SCORE),
            "failure_score": self.DEFAULT_FAILURE_SCORE,
            "forgetting_score": self.DEFAULT_FORGETTING_SCORE,
        }

    @property
    def is_game_mode_challenge(self) -> bool:
        return "challenge" in self.game_mode.lower()

    @property
    def is_game_mode_training(self) -> bool:
        return "training" in self.game_mode.lower()

    def compute_questions(self, pack_len: int = 10) -> List[EntityType]:
        """Main method to compute which questions to ask next"""
        # Challenge mode does not need the algorithm, just classic random
        if not self.user.is_authenticated or self.is_game_mode_challenge:
            return list(self.entity_model.objects.order_by("?")[0:pack_len])
        else:
            # Apply the algorithm
            return self.personalized_questions(pack_len)

    def personalized_questions(self, pack_len: int) -> List[EntityType]:
        """Apply the adaptive learning algorithm to select personalized questions"""
        cooldown_threshold = self.datetime_now - timezone.timedelta(minutes=self.COOLDOWN)
        
        # Get scores that are past the cooldown period
        user_scores = self.score_model.objects.filter(
            user=self.user, 
            updated_at__lte=cooldown_threshold, 
            game_mode=self.game_mode
        )
        
        # Get entities that have never been attempted by this user in this game mode
        exclude_kwargs = {
            f"{self.related_name}__game_mode": self.game_mode,
            f"{self.related_name}__user": self.user,
        }
        entities_without_score = self.entity_model.objects.exclude(**exclude_kwargs)

        # Step 1: Compute weights
        scored_questions = [self.compute_weight(q) for q in user_scores]
        
        # Add never seen entities if any (no score yet, but we need to ask)
        if entities_without_score.exists():
            scored_questions.extend([self.get_default_weight(entity) for entity in entities_without_score])

        if not scored_questions:
            # Fallback to random if no data available
            return list(self.entity_model.objects.order_by("?")[0:pack_len])

        # Step 2: Normalize the weights (total amount of "chance" available)
        total_weight = sum(q["weight"] for q in scored_questions)
        
        if total_weight == 0:
            # All weights are 0, fall back to random selection
            return list(self.entity_model.objects.order_by("?")[0:pack_len])

        # Now each weight is divided by the total to convert it into a percentage of the total (values between 0 and 1).
        # E.g., if a question has weight 5 and the total is 20, its normalized weight becomes 0.25 → it gets a 25% chance of being picked.
        for q in scored_questions:
            q["normalized_weight"] = q["weight"] / total_weight

        # Step 3: Weighted random selection
        selection = []
        for _ in range(pack_len):
            # picking a random point.
            rand_val = random.random()  # nosec
            cumulative = 0
            for q in scored_questions:
                # Cumulative is a way of checking each weight, the bigger the weight the more likely it is to be in the rand_val
                cumulative += q["normalized_weight"]
                # The first time the cumulative chance exceeds the rand_val, we stop
                if rand_val <= cumulative:
                    chosen = q[self.entity_field_name]
                    selection.append(chosen)
                    break

        return selection