from uuid import UUID

from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.db import transaction

from api.flag_store import flag_store
from api.schema import NewQuestions
from core.models import Country, User, Guess, UserCountryScore



class GameService:
    CACHE_TIMEOUT_SECONDS = 86400

    @classmethod
    def user_accept(cls, session_id: UUID, session_token: UUID) -> bool:
        try:
            # Get session data
            session = Session.objects.get(pk=session_token)
            session_data = session.get_decoded()

            # Get the user stored
            uid = session_data.get('_auth_user_id')
            user = User.objects.get(id=uid)

            # Cache it for later requests
            cache.set(f"{session_id}_user", user, timeout=cls.CACHE_TIMEOUT_SECONDS)

            return True
        except (Session.DoesNotExist, User.DoesNotExist):
            return False


    @classmethod
    def user_get(cls, session_id: UUID) -> User:
        return cache.get(f"{session_id}_user", AnonymousUser(), timeout=cls.CACHE_TIMEOUT_SECONDS)

    @classmethod
    def get_questions(cls, session_id: UUID) -> NewQuestions:
        """
        Get the selected questions.
        Append questions in the cache for answer checking after.
        """
        questions_with_answer = cache.get(session_id) or {}
        len_previous_data = len(questions_with_answer)

        new_questions = {}
        countries = Country.objects.order_by('?')[0:10]

        for index, country in enumerate(countries):
            next_index = len_previous_data + index
            new_questions[next_index] = flag_store.get_path(country.iso2_code) or ""
            questions_with_answer[next_index] = country.iso2_code

        cache.set(session_id, questions_with_answer, timeout=cls.CACHE_TIMEOUT_SECONDS)
        print("CAMILLE IS CHEATING", questions_with_answer)
        return NewQuestions(questions=new_questions)


    @classmethod
    def check_answer(cls, session_id: UUID, question_index: int, answer_submitted: str, user: User | AnonymousUser) -> (bool, Country | None):
        """
        Return whether the answer received is the expected one.
        """
        questions = cache.get(session_id)

        if not questions or question_index not in questions:
            return False

        country_to_guess_iso2_code = questions.get(question_index)
        is_correct = country_to_guess_iso2_code == answer_submitted

        country = Country.objects.get(iso2_code=country_to_guess_iso2_code)
        if not isinstance(user, AnonymousUser):
            cls.guess_register(user, is_correct, country)

        return is_correct, country

    @classmethod
    @transaction.atomic
    def guess_register(cls, user: User, is_correct: bool, country: Country) -> None:
        """
        Save a user's guess
        """
        score, _ = UserCountryScore.objects.get_or_create(
            user=user,
            country=country,
            game_mode=UserCountryScore.GameModes.GUESS_COUNTRY_FROM_FLAG,  # TODO: le front doit envoyer le mode de jeu
        )
        guess = Guess.objects.create(is_correct=is_correct)
        score.user_guesses.add(guess)
