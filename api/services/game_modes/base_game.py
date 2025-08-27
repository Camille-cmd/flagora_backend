from abc import ABC
from uuid import UUID

from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from api.schema import CorrectAnswer, NewQuestions
from core.models import Country, Guess, User, UserCountryScore, UserStats
from core.services.user_services import user_get_best_steak


class GameService(ABC):
    CACHE_TIMEOUT_SECONDS = 86400
    GAME_MODE = ""

    @classmethod
    def user_accept(cls, session_id: UUID, session_token: UUID) -> bool:
        try:
            # Get session data
            session = Session.objects.get(pk=session_token)
            session_data = session.get_decoded()

            # Get the user stored
            uid = session_data.get("_auth_user_id")
            user = User.objects.get(id=uid)

            # Cache it for later requests
            cache.set(f"{session_id}_user_id", user.id, timeout=cls.CACHE_TIMEOUT_SECONDS)
            # Reset streak in case of a new game
            cache.set(f"{session_id}_user_streak", 0, timeout=cls.CACHE_TIMEOUT_SECONDS)

            return True
        except (Session.DoesNotExist, User.DoesNotExist):
            return False

    @classmethod
    def user_get(cls, session_id: UUID) -> User:
        cache_key = f"{session_id}_user_id"
        user_id = cache.get(cache_key)
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                # Reset timeout for sliding expiration
                cache.set(cache_key, user_id, timeout=cls.CACHE_TIMEOUT_SECONDS)
                return user
            except User.DoesNotExist:
                pass

        return AnonymousUser()

    @classmethod
    def clear_cache(cls, session_id: UUID) -> None:
        cache.delete(f"{session_id}_user_id")

    @classmethod
    def get_questions(cls, session_id: UUID) -> NewQuestions:
        pass

    @classmethod
    def check_answer(
        cls,
        session_id: UUID,
        question_index: int,
        answer_submitted: str,
        user: User | AnonymousUser,
    ) -> tuple[bool, Country | None]:
        pass

    @classmethod
    def get_correct_answer(cls, user: User, country: Country) -> list[CorrectAnswer]:
        """
        As a country can have multiple capitals, we need to return a list of correct answers everytime,
        even if there is only one.
        """

    @classmethod
    @transaction.atomic
    def guess_register(cls, user: User, is_correct: bool, country: Country) -> None:
        """
        Save a user's guess
        """
        score, _ = UserCountryScore.objects.get_or_create(
            user=user,
            country=country,
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
