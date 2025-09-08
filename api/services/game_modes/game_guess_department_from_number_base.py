from uuid import UUID

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from api.schema import CorrectAnswer, NewQuestions
from api.services.game_modes.base_game import GameService
from api.services.user_department_score import UserDepartmentScoreService
from core.models import Department, Guess, User, UserDepartmentScore, UserStats
from core.models.user_country_score import GameModes
from core.services.user_services import user_get_best_steak


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
        departments = UserDepartmentScoreService(user, cls.GAME_MODE).compute_questions()

        for index, department in enumerate(departments):
            next_index = len_previous_data + index
            new_questions[next_index] = department.number
            questions_with_answer[next_index] = department.number

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

        department_to_guess_number = questions.get(question_index)
        department = Department.objects.get(number=department_to_guess_number)
        
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

    @classmethod
    def user_get_streak_score(
        cls, session_id: UUID, user: User, is_correct: bool, remaining_to_guess: int
    ) -> tuple[int, bool, int | None]:
        """
        Calculate and update streak score for department gamemode
        """
        cache_streak_key = f"{session_id}_user_streak"
        current_streak = cache.get(cache_streak_key) or 0

        game_over = False
        best_streak = None
        if not is_correct:
            # stop streak
            current_score = current_streak

            if "challenge" in cls.GAME_MODE.lower():
                game_over = True

            if user.is_authenticated:
                best_streak = user_get_best_steak(user, cls.GAME_MODE)

                if current_streak > best_streak:
                    UserStats.objects.update_or_create(
                        user=user,
                        game_mode=cls.GAME_MODE,
                        defaults={"best_streak": current_streak},
                    )
                    best_streak = current_streak
        # Update streak only if all answers have been guessed
        elif remaining_to_guess > 0:
            # do not update streak
            current_score = current_streak
        else:
            # update streak
            current_score = current_streak + 1

        cache.set(cache_streak_key, current_score if is_correct else 0, timeout=cls.CACHE_TIMEOUT_SECONDS)

        return (
            current_score,
            game_over,
            best_streak,
        )