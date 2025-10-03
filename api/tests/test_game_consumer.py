from unittest.mock import MagicMock, patch

from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase, override_settings

from api.consumers import GameConsumer
from api.routing import websocket_urlpatterns
from core.models.user_country_score import GameModes
from core.tests.factories import UserFactory
from core.tests.mocks import MockGameService


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
        self.user = UserFactory(username="test_user", email="testuser@example.com")
        self.token = "dummy-token"
        self.url = "/ws/game/"

    async def test_connects(self):
        communicator = WebsocketCommunicator(self.application, self.url)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    @patch("api.consumers.GameServiceRegistry.get_game_service")
    async def test_user_accept_sends_auth_and_questions(self, mock_get_game_service):
        communicator = WebsocketCommunicator(self.application, self.url)
        await communicator.connect()

        mock_service = MockGameService()
        mock_questions = MagicMock()
        mock_questions.model_dump.return_value = {"questions": ["France", "Japan"]}
        mock_service.get_questions.return_value = mock_questions
        mock_get_game_service.return_value = mock_service

        await communicator.send_json_to(
            {
                "type": "user_accept",
                "gameMode": GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE,
                "gameToken": "dummy-token",
                "token": self.token,
                "language": "en",
            }
        )

        auth_response = await communicator.receive_json_from()
        self.assertEqual(auth_response["type"], "user_accept")
        self.assertTrue(auth_response["payload"]["isUserAuthenticated"])

        question_response = await communicator.receive_json_from()
        self.assertEqual(question_response["type"], "new_questions")
        self.assertEqual(question_response["payload"], {"questions": ["France", "Japan"]})

    async def test_user_accept_no_game_service(self):
        communicator = WebsocketCommunicator(self.application, self.url)
        await communicator.connect()

        await communicator.send_json_to(
            {
                "type": "user_accept",
                "gameMode": "unsupported game mode",
                "gameToken": "dummy-token",
                "token": self.token,
                "language": "fr",
            }
        )

        with self.assertRaises(ValueError):
            await communicator.receive_json_from()

    @patch("api.consumers.GameServiceRegistry.get_game_service")
    async def test_request_questions_sends_questions(self, mock_get_game_service):
        communicator = WebsocketCommunicator(self.application, self.url)
        await communicator.connect()

        mock_service = MockGameService()
        mock_questions = MagicMock()
        mock_questions.model_dump.return_value = {"questions": ["Brazil", "Kenya"]}
        mock_service.get_questions.return_value = mock_questions
        mock_get_game_service.return_value = mock_service

        # First simulate user_accept to initialize game_service
        mock_service.user_accept.return_value = True
        await communicator.send_json_to(
            {
                "type": "user_accept",
                "gameMode": GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE,
                "gameToken": "dummy-token",
                "token": self.token,
                "language": "fr",
            }
        )
        await communicator.receive_json_from()  # auth
        await communicator.receive_json_from()  # questions

        # Then send request_questions
        await communicator.send_json_to({"type": "request_questions"})

        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "new_questions")
        self.assertEqual(response["payload"], {"questions": ["Brazil", "Kenya"]})

    @patch("api.consumers.GameServiceRegistry.get_game_service")
    async def test_answer_submission_correct(self, mock_get_game_service):
        communicator = WebsocketCommunicator(self.application, self.url)
        await communicator.connect()

        mock_service = MockGameService(check_answer_result=True)
        mock_service.get_questions.return_value.model_dump.return_value = {"questions": []}
        mock_get_game_service.return_value = mock_service

        # Simulate user_accept first to initialize game_service
        await communicator.send_json_to(
            {
                "type": "user_accept",
                "gameMode": GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE,
                "gameToken": "dummy-token",
                "token": self.token,
                "language": "fr",
            }
        )
        await communicator.receive_json_from()  # auth
        await communicator.receive_json_from()  # questions

        # Now send answer_submission
        await communicator.send_json_to({"type": "answer_submission", "id": 1, "answer": "Paris"})
        response = await communicator.receive_json_from()

        self.assertEqual(response["type"], "answer_result")
        self.assertEqual(response["payload"]["id"], 1)
        self.assertTrue(response["payload"]["isCorrect"])

    @patch("api.consumers.GameServiceRegistry.get_game_service", return_value=MockGameService())
    async def test_question_skipped_sends_correct_info(self, _mock_get_game_service):
        communicator = WebsocketCommunicator(self.application, self.url)
        await communicator.connect()

        # Authenticate first
        await communicator.send_json_to(
            {
                "type": "user_accept",
                "gameMode": GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE,
                "gameToken": "dummy-token",
                "token": self.token,
                "language": "fr",
            }
        )
        await communicator.receive_json_from()  # auth
        await communicator.receive_json_from()  # questions

        await communicator.send_json_to({"type": "question_skipped", "id": 456, "answer": ""})
        response = await communicator.receive_json_from()

        self.assertEqual(response["type"], "answer_result")
        self.assertFalse(response["payload"]["isCorrect"])
        self.assertEqual(len(response["payload"]["correctAnswer"]), 1)
        self.assertEqual(response["payload"]["correctAnswer"][0]["name"], "Allemagne")
        self.assertEqual(response["payload"]["correctAnswer"][0]["code"], "DE")
        self.assertEqual(
            response["payload"]["correctAnswer"][0]["wikipediaLink"], "https://fr.wikipedia.org/wiki/Allemagne"
        )

    async def test_receive_json_invalid_type_raises(self):
        consumer = GameConsumer()
        consumer.scope = {"type": "websocket"}
        consumer.channel_name = "test_channel"
        consumer.send_json = MagicMock()

        with self.assertRaises(ValueError) as context:
            consumer.receive_json({"type": "invalid_type"})

        self.assertIn("Unknown message type", str(context.exception))

    def test_game_token_set_to_session_id(self):
        consumer = GameConsumer()
        consumer.scope = {"type": "websocket"}
        consumer.channel_name = "test_channel"
        consumer.send_json = MagicMock()

        game_token = "very-real-token"
        consumer.receive_json(
            {
                "type": "user_accept",
                "gameMode": GameModes.GUESS_COUNTRY_FROM_FLAG_TRAINING_INFINITE,
                "gameToken": game_token,
                "token": self.token,
                "language": "fr",
            }
        )

        self.assertEqual(consumer.session_id, game_token)
