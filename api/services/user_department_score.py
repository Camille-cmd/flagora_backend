from typing import List

from api.services.adaptive_learning_algorithm import AdaptiveLearningAlgorithm
from core.models import Department, User, UserDepartmentScore
from core.models.user_country_score import GameModes


class UserDepartmentScoreService:
    """
    Service for managing user scores for departments using adaptive learning algorithm.
    """

    def __init__(self, user: User, game_mode: GameModes):
        self.user = user
        self.game_mode = game_mode
        self.algorithm = AdaptiveLearningAlgorithm[Department, UserDepartmentScore](
            user=user,
            game_mode=game_mode,
            entity_model=Department,
            score_model=UserDepartmentScore,
            entity_field_name="department",
            related_name="department_scores"
        )

    def compute_weight(self, user_department_score: UserDepartmentScore):
        """Compute the learning weight for a specific department score"""
        return self.algorithm.compute_weight(user_department_score)

    def get_default_weight(self, department: Department):
        """Weight for a department without any UserDepartmentScore yet. Default values."""
        return self.algorithm.get_default_weight(department)

    @property
    def is_game_mode_challenge(self) -> bool:
        return self.algorithm.is_game_mode_challenge

    @property
    def is_game_mode_training(self) -> bool:
        return self.algorithm.is_game_mode_training

    def compute_questions(self) -> List[Department]:
        """Main method to compute which departments to ask next"""
        return self.algorithm.compute_questions()

    def personalized_questions(self, pack_len: int) -> List[Department]:
        """Apply the adaptive learning algorithm to select personalized questions"""
        return self.algorithm.personalized_questions(pack_len)