from uuid import UUID

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache

from api.schema import NewQuestions
from api.services.game_modes.base_game import GameService
from api.services.user_country_score import UserCountryScoreService
from api.utils import user_get_language
from core.models import City, Country, User


class GameServiceGuessCapitalFromCountryBase(GameService):
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
        countries = UserCountryScoreService(user, game_mode=cls.GAME_MODE).compute_questions()
        user_language = user_get_language(user)
        name_field = f"name_{user_language}"

        question_index = 0
        for country in countries:
            if not country.cities.exists():
                continue
            next_index = len_previous_data + question_index
            new_questions[next_index] = getattr(country, name_field)
            # Send name field to keep a consistent answer check
            questions_with_answer[next_index] = (list(country.cities.values_list("id", flat=True)), name_field)

            question_index += 1

        cache.set(session_id, questions_with_answer, timeout=cls.CACHE_TIMEOUT_SECONDS)

        return NewQuestions(questions=new_questions)

    @classmethod
    def check_answer(
        cls,
        session_id: UUID,
        question_index: int,
        answer_submitted: str,
        user: User | AnonymousUser,
    ) -> tuple[bool, Country | None]:
        """
        Return whether the answer received is the expected one.
        """
        questions = cache.get(session_id)

        if not questions or question_index not in questions:
            return False, None

        cities_ids_list, name_field = questions.get(question_index)

        cities_names = City.objects.filter(id__in=cities_ids_list, is_capital=True).values_list(name_field, flat=True)
        is_correct = answer_submitted in cities_names

        countries = Country.objects.filter(cities__in=cities_ids_list).distinct()
        if countries.count() != 1:
            raise ValueError(f"Multiple countries found for cities: {list(cities_names)}")
        country = countries.first()
        if user.is_authenticated:
            cls.guess_register(user, is_correct, country)

        return is_correct, country

    @classmethod
    def get_correct_answer(cls, user: User, country: Country) -> dict[str, str | None]:
        user_language = user_get_language(user)
        name_field = f"name_{user_language}"
        cities = list(country.cities.filter(is_capital=True).values_list(name_field, flat=True))
        correct_answer = ", ".join(cities)
        wikipedia_link = f"https://fr.wikipedia.org/wiki/{cities[0]}"  # Todo how to handle several cities?

        return {
            "correct_answer": correct_answer,
            "code": "",
            "wikipedia_link": wikipedia_link,
        }
