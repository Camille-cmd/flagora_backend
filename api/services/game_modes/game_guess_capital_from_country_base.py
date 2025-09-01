from uuid import UUID

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache

from api.schema import CorrectAnswer, NewQuestions
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

        question_index = 0
        for country in countries:
            if not country.cities.exists():
                continue
            next_index = len_previous_data + question_index
            new_questions[next_index] = country.iso2_code
            # Send name field to keep a consistent answer check
            found_capitals = []
            questions_with_answer[next_index] = (
                list(country.cities.values_list("id", flat=True)),
                found_capitals,
            )

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
    ) -> tuple[bool, Country | None, int]:
        """
        Return whether the answer received is the expected one comparing it with what is stored in the cache.
        """
        questions = cache.get(session_id)

        if not questions or question_index not in questions:
            return False, None, 0

        cities_ids_list, found_capitals_ids = questions.get(question_index)

        cities_ids = City.objects.filter(id__in=cities_ids_list, is_capital=True).values_list("pk", flat=True)
        is_correct = answer_submitted in cities_ids

        # Case of a country with multiple capitals
        remaining_cities = 0
        if len(cities_ids_list) > 1:
            if answer_submitted not in found_capitals_ids:
                found_capitals_ids.append(answer_submitted)
            remaining_cities = len(cities_ids_list) - len(found_capitals_ids)
            # cache what has been found so far
            questions[question_index] = (cities_ids_list, found_capitals_ids)
            cache.set(session_id, questions, timeout=cls.CACHE_TIMEOUT_SECONDS)

        countries = Country.objects.filter(cities__in=cities_ids_list).distinct()
        if countries.count() != 1:
            raise ValueError(f"Multiple countries found for cities: {list(cities_ids_list)}")
        country = countries.first()

        if user.is_authenticated:
            cls.guess_register(user, is_correct, country)

        return is_correct, country, remaining_cities

    @classmethod
    def get_correct_answer(cls, user: User, country: Country, user_language: str) -> list[CorrectAnswer]:
        """
        As a country can have multiple capitals, we need to return a list of correct answers.
        """
        name_field = f"name_{user_language}"
        cities = list(country.cities.filter(is_capital=True).values_list(name_field, flat=True))

        correct_answer_data = []
        for city_name in cities:
            correct_answer_data.append(
                CorrectAnswer(
                    name=city_name,
                    code="",
                    wikipedia_link=f"https://{user_language}.wikipedia.org/wiki/{city_name}",
                )
            )

        return correct_answer_data
