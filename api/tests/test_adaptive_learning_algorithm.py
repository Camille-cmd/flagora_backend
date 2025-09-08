from django.test import TestCase
from django.contrib.auth import get_user_model

from api.services.adaptive_learning_algorithm import AdaptiveLearningAlgorithm
from api.services.user_country_score import UserCountryScoreService
from api.services.user_department_score import UserDepartmentScoreService
from core.models import Country, Department, UserCountryScore, UserDepartmentScore
from core.models.user_country_score import GameModes

User = get_user_model()


class AdaptiveLearningAlgorithmTestCase(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username="testuser", 
            email="test@example.com", 
            password="testpass123"
        )
        
        # Create test entities
        self.country = Country.objects.create(
            name_en="France",
            name_fr="France", 
            name_native="France",
            iso2_code="FR",
            iso3_code="FRA",
            continent="EU"
        )
        
        self.department = Department.objects.create(
            number="75", 
            name="Paris", 
            region="Île-de-France", 
            prefecture="Paris"
        )

    def test_generic_algorithm_with_countries(self):
        """Test that the generic algorithm works with countries"""
        algorithm = AdaptiveLearningAlgorithm[Country, UserCountryScore](
            user=self.user,
            game_mode=GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE,
            entity_model=Country,
            score_model=UserCountryScore,
            entity_field_name="country",
            related_name="country_scores"
        )
        
        # Test basic functionality
        self.assertFalse(algorithm.is_game_mode_challenge)
        self.assertTrue(algorithm.is_game_mode_training)
        
        # Test question computation
        questions = algorithm.compute_questions()
        self.assertIsInstance(questions, list)

    def test_generic_algorithm_with_departments(self):
        """Test that the generic algorithm works with departments"""
        algorithm = AdaptiveLearningAlgorithm[Department, UserDepartmentScore](
            user=self.user,
            game_mode=GameModes.GUESS_DEPARTMENT_FROM_NUMBER_TRAINING_INFINITE,
            entity_model=Department,
            score_model=UserDepartmentScore,
            entity_field_name="department",
            related_name="department_scores"
        )
        
        # Test basic functionality
        self.assertFalse(algorithm.is_game_mode_challenge)
        self.assertTrue(algorithm.is_game_mode_training)
        
        # Test question computation
        questions = algorithm.compute_questions()
        self.assertIsInstance(questions, list)

    def test_country_service_uses_generic_algorithm(self):
        """Test that UserCountryScoreService uses the generic algorithm"""
        service = UserCountryScoreService(
            self.user, 
            GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE
        )
        
        # Test that service has algorithm attribute
        self.assertIsInstance(service.algorithm, AdaptiveLearningAlgorithm)
        
        # Test that methods still work
        questions = service.compute_questions()
        self.assertIsInstance(questions, list)
        
        # Test default weight computation
        default_weight = service.get_default_weight(self.country)
        self.assertIn("country", default_weight)
        self.assertIn("weight", default_weight)

    def test_department_service_uses_generic_algorithm(self):
        """Test that UserDepartmentScoreService uses the generic algorithm"""
        service = UserDepartmentScoreService(
            self.user, 
            GameModes.GUESS_DEPARTMENT_FROM_NUMBER_TRAINING_INFINITE
        )
        
        # Test that service has algorithm attribute
        self.assertIsInstance(service.algorithm, AdaptiveLearningAlgorithm)
        
        # Test that methods still work
        questions = service.compute_questions()
        self.assertIsInstance(questions, list)
        
        # Test default weight computation
        default_weight = service.get_default_weight(self.department)
        self.assertIn("department", default_weight)
        self.assertIn("weight", default_weight)

    def test_backward_compatibility(self):
        """Test that the refactoring maintains backward compatibility"""
        # Test country service interface
        country_service = UserCountryScoreService(
            self.user, 
            GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE
        )
        
        # All these methods should still exist and work
        self.assertTrue(hasattr(country_service, 'compute_questions'))
        self.assertTrue(hasattr(country_service, 'compute_weight'))
        self.assertTrue(hasattr(country_service, 'get_default_weight'))
        self.assertTrue(hasattr(country_service, 'is_game_mode_challenge'))
        self.assertTrue(hasattr(country_service, 'is_game_mode_training'))
        
        # Test department service interface
        dept_service = UserDepartmentScoreService(
            self.user, 
            GameModes.GUESS_DEPARTMENT_FROM_NUMBER_TRAINING_INFINITE
        )
        
        # All these methods should still exist and work
        self.assertTrue(hasattr(dept_service, 'compute_questions'))
        self.assertTrue(hasattr(dept_service, 'compute_weight'))
        self.assertTrue(hasattr(dept_service, 'get_default_weight'))
        self.assertTrue(hasattr(dept_service, 'is_game_mode_challenge'))
        self.assertTrue(hasattr(dept_service, 'is_game_mode_training'))