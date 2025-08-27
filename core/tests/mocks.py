from unittest.mock import MagicMock

from api.schema import CorrectAnswer


class MockGameService:
    def __init__(self, check_answer_result=False):
        country = MagicMock()
        country.name_fr = "Allemagne"
        country.iso2_code = "DE"

        user = MagicMock()
        user.language = "fr"

        self._user = user
        self._country = country

        # Methods as mocks so tests can override .return_value
        self.user_accept = MagicMock(return_value=True)
        self.user_get = MagicMock(return_value=self._user)
        self.check_answer = MagicMock(return_value=(check_answer_result, self._country))
        self.get_correct_answer = MagicMock(
            return_value=[
                CorrectAnswer(
                    name="Allemagne",
                    code="DE",
                    wikipedia_link="https://fr.wikipedia.org/wiki/Allemagne",
                )
            ]
        )
        self.user_get_streak_score = MagicMock(return_value=(0, False, 0))

        # get_questions returns a mock with a .model_dump() method
        questions_mock = MagicMock()
        questions_mock.model_dump.return_value = {"questions": []}
        self.get_questions = MagicMock(return_value=questions_mock)
