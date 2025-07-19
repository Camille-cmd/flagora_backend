from unittest.mock import ANY, MagicMock, patch

from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase, override_settings

from api.routing import websocket_urlpatterns
from core.tests.factories import UserFactory


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        }
    }
)
class GameConsumerTestCase(TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.application = URLRouter(websocket_urlpatterns)

        self.user = UserFactory(
            username="test_user",
            email="testuser@example.com",
            password="securepassword123",
        )

        self.token = "dummy-token"
        self.questions = MagicMock()
        self.questions.model_dump.return_value = {"questions": ["France", "Japan"]}
        self.url = "/ws/game/"

    async def test_connects(self):
        """Test that the WishlistConsumer successfully connects."""
        communicator = WebsocketCommunicator(self.application, self.url)

        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        await communicator.disconnect()

    @patch("api.consumers.GameService.get_questions")
    @patch("api.consumers.GameService.user_accept", return_value=True)
    async def test_user_accept_sends_auth_and_questions(self, mock_user_accept, mock_get_questions):
        communicator = WebsocketCommunicator(self.application, self.url)
        mock_get_questions.return_value = self.questions

        await communicator.send_json_to({"type": "user_accept", "token": self.token})

        # Expect auth response
        auth_response = await communicator.receive_json_from()
        self.assertEqual(auth_response["type"], "user_accept")
        self.assertTrue(auth_response["payload"]["is_user_authenticated"])

        # Expect questions response
        question_response = await communicator.receive_json_from()
        self.assertEqual(question_response["type"], "new_questions")
        self.assertEqual(question_response["payload"], {"questions": ["France", "Japan"]})

        # Channel name is not exposed, just check that it's called.
        mock_user_accept.assert_called_once_with(ANY, self.token)
        mock_get_questions.assert_called_once_with(ANY)

    @patch("api.consumers.GameService.get_questions")
    async def test_request_questions_sends_questions(self, mock_get_questions):
        communicator = WebsocketCommunicator(self.application, self.url)

        questions = MagicMock()
        questions.model_dump.return_value = {"questions": ["Brazil", "Kenya"]}
        mock_get_questions.return_value = questions

        await communicator.send_json_to({"type": "request_questions"})

        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "new_questions")
        self.assertEqual(response["payload"], {"questions": ["Brazil", "Kenya"]})

        mock_get_questions.assert_called_once_with(ANY)

    @patch("api.consumers.GameService.check_answer")
    @patch("api.consumers.GameService.user_get")
    async def test_answer_submission_correct(self, mock_user_get, mock_check_answer):
        communicator = WebsocketCommunicator(self.application, self.url)

        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user_get.return_value = mock_user
        mock_check_answer.return_value = (True, MagicMock())

        await communicator.send_json_to({"type": "answer_submission", "id": 123, "answer": "Berlin"})

        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "answer_result")
        self.assertTrue(response["payload"]["isCorrect"])
        self.assertEqual(response["payload"]["id"], 123)
        self.assertEqual(response["payload"]["correctAnswer"], "")
        self.assertEqual(response["payload"]["code"], "")
        self.assertEqual(response["payload"]["wikipediaLink"], "")

        mock_user_get.assert_called_once_with(ANY)
        mock_check_answer.assert_called_once_with(ANY, 123, "Berlin", mock_user)

    @patch("api.consumers.GameService.check_answer")
    @patch("api.consumers.GameService.user_get")
    @patch("api.consumers.get_language", return_value="fr")
    async def test_question_skipped_sends_correct_info(self, mock_get_language, mock_user_get, mock_check_answer):
        communicator = WebsocketCommunicator(self.application, self.url)

        country = MagicMock()
        setattr(country, "name_fr", "Allemagne")
        country.iso2_code = "DE"

        user = MagicMock()
        user.is_authenticated = True
        user.language = "fr"

        mock_user_get.return_value = user
        mock_check_answer.return_value = (False, country)

        await communicator.send_json_to({"type": "question_skipped", "id": 456, "answer": ""})

        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "answer_result")
        self.assertFalse(response["payload"]["isCorrect"])
        self.assertEqual(response["payload"]["correctAnswer"], "Allemagne")
        self.assertEqual(response["payload"]["code"], "DE")
        self.assertEqual(
            response["payload"]["wikipediaLink"],
            "https://fr.wikipedia.org/wiki/Allemagne",
        )

        mock_user_get.assert_called_once_with(ANY)
        mock_check_answer.assert_called_once_with(ANY, 456, "", user)
