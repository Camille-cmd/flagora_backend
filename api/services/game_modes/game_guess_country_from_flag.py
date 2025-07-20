from uuid import UUID

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache

from api.flag_store import flag_store
from api.game_registery import GameServiceRegistry
from api.schema import NewQuestions
from api.services.game_modes.base_game import GameService
from api.services.user_country_score import UserCountryScoreService
from api.utils import user_get_language
from core.models import Country, User, UserCountryScore


@GameServiceRegistry.register(UserCountryScore.GameModes.GUESS_COUNTRY_FROM_FLAG)
class GameServiceGuessCountryFromFlag(GameService):
    GAME_MODE = UserCountryScore.GameModes.GUESS_COUNTRY_FROM_FLAG

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
        countries = UserCountryScoreService(user, cls.GAME_MODE).compute_questions()

        for index, country in enumerate(countries):
            next_index = len_previous_data + index
            new_questions[next_index] = flag_store.get_path(country.iso2_code) or ""
            questions_with_answer[next_index] = country.iso2_code

        cache.set(session_id, questions_with_answer, timeout=cls.CACHE_TIMEOUT_SECONDS)
        print("CAMILLE IS CHEATING", questions_with_answer)
        return NewQuestions(questions=new_questions)

    @classmethod
    def check_answer(
        cls,
        session_id: UUID,
        question_index: int,
        answer_submitted: str,
        user: User | AnonymousUser,
    ) -> (bool, Country | None):
        """
        Return whether the answer received is the expected one.
        """
        questions = cache.get(session_id)

        if not questions or question_index not in questions:
            return False, None

        country_to_guess_iso2_code = questions.get(question_index)
        is_correct = country_to_guess_iso2_code == answer_submitted

        country = Country.objects.get(iso2_code=country_to_guess_iso2_code)
        if user.is_authenticated:
            cls.guess_register(user, is_correct, country)

        return is_correct, country

    @classmethod
    def get_correct_answer(cls, user: User, country: Country) -> dict[str, str | None]:
        user_language = user_get_language(user)
        name_field = f"name_{user_language}"
        correct_answer = getattr(country, name_field)
        code = country.iso2_code
        wikipedia_link = f"https://fr.wikipedia.org/wiki/{correct_answer}"

        return {
            "correct_answer": correct_answer,
            "code": code,
            "wikipedia_link": wikipedia_link,
        }
