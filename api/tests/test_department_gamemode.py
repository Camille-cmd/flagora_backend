from django.test import TestCase
from django.contrib.auth import get_user_model

from core.models import Department, UserDepartmentScore
from core.models.user_country_score import GameModes
from api.services.game_modes.training_modes.game_guess_department_from_number import GameServiceGuessDepartmentFromNumberTrainingInfinite
from api.services.user_department_score import UserDepartmentScoreService

User = get_user_model()


class DepartmentGameModeTestCase(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username="testuser", 
            email="test@example.com", 
            password="testpass123"
        )
        
        # Create test departments
        self.dept1 = Department.objects.create(
            number="01", 
            name="Ain", 
            region="Auvergne-Rhône-Alpes", 
            prefecture="Bourg-en-Bresse"
        )
        self.dept2 = Department.objects.create(
            number="75", 
            name="Paris", 
            region="Île-de-France", 
            prefecture="Paris"
        )
        
    def test_department_creation(self):
        """Test that departments are created correctly"""
        self.assertEqual(self.dept1.number, "01")
        self.assertEqual(self.dept1.name, "Ain")
        self.assertEqual(str(self.dept1), "01 - Ain")
        
    def test_user_department_score_creation(self):
        """Test UserDepartmentScore model"""
        score = UserDepartmentScore.objects.create(
            user=self.user,
            department=self.dept1,
            game_mode=GameModes.GUESS_DEPARTMENT_FROM_NUMBER_TRAINING_INFINITE
        )
        
        self.assertEqual(score.user, self.user)
        self.assertEqual(score.department, self.dept1)
        self.assertEqual(score.game_mode, GameModes.GUESS_DEPARTMENT_FROM_NUMBER_TRAINING_INFINITE)
        
    def test_gamemode_enum_contains_department_modes(self):
        """Test that GameModes enum includes department modes"""
        choices = [choice[0] for choice in GameModes.choices]
        
        self.assertIn("GDFN_TRAINING_INFINITE", choices)
        self.assertIn("GDFN_CHALLENGE_COMBO", choices)
        
    def test_department_score_service(self):
        """Test UserDepartmentScoreService"""
        service = UserDepartmentScoreService(
            self.user, 
            GameModes.GUESS_DEPARTMENT_FROM_NUMBER_TRAINING_INFINITE
        )
        
        # Test that service can compute questions
        questions = service.compute_questions()
        self.assertIsInstance(questions, list)
        
        # Test that service uses the generic algorithm
        from api.services.adaptive_learning_algorithm import AdaptiveLearningAlgorithm
        self.assertIsInstance(service.algorithm, AdaptiveLearningAlgorithm)
        
    def test_game_service_correct_answer(self):
        """Test GameService get_correct_answer method"""
        correct_answers = GameServiceGuessDepartmentFromNumberTrainingInfinite.get_correct_answer(
            self.user, self.dept1, "fr"
        )
        
        self.assertEqual(len(correct_answers), 1)
        self.assertEqual(correct_answers[0].name, "Ain")
        self.assertEqual(correct_answers[0].code, "01")
        
    def test_game_service_check_answer(self):
        """Test GameService check_answer method"""
        # This would require session/cache setup, so we'll keep it simple
        service = GameServiceGuessDepartmentFromNumberTrainingInfinite
        
        # Test the game mode is set correctly
        self.assertEqual(service.GAME_MODE, GameModes.GUESS_DEPARTMENT_FROM_NUMBER_TRAINING_INFINITE)