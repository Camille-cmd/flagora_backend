from typing import List

from api.services.adaptive_learning_algorithm import AdaptiveLearningAlgorithm
from core.models import Country, User, UserCountryScore
from core.models.user_country_score import GameModes


class UserCountryScoreService:
    """
    Service for managing user scores for countries using adaptive learning algorithm.
    """

    def __init__(self, user: User, game_mode: GameModes):
        self.user = user
        self.game_mode = game_mode
        self.algorithm = AdaptiveLearningAlgorithm[Country, UserCountryScore](
            user=user,
            game_mode=game_mode,
            entity_model=Country,
            score_model=UserCountryScore,
            entity_field_name="country",
            related_name="country_scores"
        )

    def compute_weight(self, user_country_score: UserCountryScore):
        """Compute the learning weight for a specific country score"""
        return self.algorithm.compute_weight(user_country_score)

    def get_default_weight(self, country: Country):
        """Weight for a country without any UserCountryScore yet. Default values."""
        return self.algorithm.get_default_weight(country)

    @property
    def is_game_mode_challenge(self) -> bool:
        return self.algorithm.is_game_mode_challenge

    @property
    def is_game_mode_training(self) -> bool:
        return self.algorithm.is_game_mode_training

    def compute_questions(self) -> List[Country]:
        """Main method to compute which countries to ask next"""
        return self.algorithm.compute_questions()

    def personalized_questions(self, pack_len: int) -> List[Country]:
        """Apply the adaptive learning algorithm to select personalized questions"""
        return self.algorithm.personalized_questions(pack_len)
