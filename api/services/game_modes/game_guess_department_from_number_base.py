from uuid import UUID

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from api.schema import CorrectAnswer, NewQuestions
from api.services.game_modes.base_game import GameService
from api.services.user_department_score import UserDepartmentScoreService
from core.models import Department, Guess, User, UserDepartmentScore


class GameServiceGuessDepartmentFromNumberBase(GameService):
    GAME_MODE = ""

    @classmethod
    def get_questions(cls, session_id: UUID) -> NewQuestions:
        """
        Get the selected questions.
        Append questions in the cache for answer checking after.
        """
        questions_with_answer = cache.get(session_id) or {}
        len_previous_data = len(questions_with_answer)

        new_questions = {}
        user = cls.user_get(session_id)
        last_question = cls.get_last_question(questions_with_answer)

        departments = UserDepartmentScoreService(user, cls.GAME_MODE).compute_questions(last_question)

        for index, department in enumerate(departments):
            next_index = len_previous_data + index
            new_questions[next_index] = department.number
            questions_with_answer[next_index] = department

        cache.set(session_id, questions_with_answer, timeout=cls.CACHE_TIMEOUT_SECONDS)
        return NewQuestions(questions=new_questions)

    @classmethod
    def check_answer(
        cls,
        session_id: UUID,
        question_index: int,
        answer_submitted: str,
        user: User | AnonymousUser,
    ) -> tuple[bool, Department | None]:
        """
        Return whether the answer received is the expected one.
        """
        questions = cache.get(session_id)

        if not questions or question_index not in questions:
            return False, None

        department = questions.get(question_index)

        # Check if the submitted answer matches the department name (case insensitive)
        is_correct = answer_submitted.lower().strip() == department.name.lower().strip()

        if user.is_authenticated:
            cls.guess_register(user, is_correct, department)

        return is_correct, department

    @classmethod
    def get_correct_answer(cls, user: User, department: Department, user_language: str) -> list[CorrectAnswer]:
        correct_answer = department.name
        code = department.number
        wikipedia_link = f"https://{user_language}.wikipedia.org/wiki/{correct_answer}"

        return [CorrectAnswer(name=correct_answer, code=code, wikipedia_link=wikipedia_link)]

    @classmethod
    @transaction.atomic
    def guess_register(cls, user: User, is_correct: bool, department: Department) -> None:
        """
        Save a user's guess for a department
        """
        score, _ = UserDepartmentScore.objects.get_or_create(
            user=user,
            department=department,
            game_mode=cls.GAME_MODE,
        )
        guess = Guess.objects.create(is_correct=is_correct)
        score.user_guesses.add(guess)

        score.updated_at = timezone.now()
        score.save()
