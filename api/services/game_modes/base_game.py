from abc import ABC
from uuid import UUID

from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from api.schema import NewQuestions
from core.models import Country, Guess, User, UserCountryScore


class GameService(ABC):
    CACHE_TIMEOUT_SECONDS = 86400

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
    def get_questions(cls, session_id: UUID) -> NewQuestions:
        pass

    @classmethod
    def check_answer(
        cls,
        session_id: UUID,
        question_index: int,
        answer_submitted: str,
        user: User | AnonymousUser,
    ) -> (bool, Country | None):
        pass

    @classmethod
    def get_correct_answer(cls, user: User, country: Country) -> dict[str, str | None]:
        pass

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
