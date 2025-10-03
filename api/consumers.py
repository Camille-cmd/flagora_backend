from channels.generic.websocket import JsonWebsocketConsumer
from django.utils.translation import gettext as _

from api.game_registery import GameServiceRegistry
from api.schema import AnswerResult, CorrectAnswer, SetUserWebsocket, WebsocketMessage
from api.services.game_modes.base_game import GameService


class GameConsumer(JsonWebsocketConsumer):
    game_service: GameService
    language: str = ""
    session_id: str = ""  # for unique sessions by game modes

    def connect(self):
        self.accept()

    def receive_json(self, content, **kwargs):
        match content["type"]:
            case "user_accept":
                self.store_user(content)
            case "answer_submission":
                self.answer_result(content)
            case "request_questions":
                self.send_questions()
            case "question_skipped":
                self.answer_result(content, skipped=True)
            case "user_change_language":
                self.language = content["language"]
            case _:
                raise ValueError(f"Unknown message type: {content['type']}")

    def store_user(self, content: dict):
        # Validate the data
        data = SetUserWebsocket.model_validate(content, by_alias=True)

        # Store the session id given from the frontend
        # This is to keep the session unique for each game mode
        self.session_id = data.game_token

        # Set the user-selected language
        self.language = data.language

        self.game_service = GameServiceRegistry.get_game_service(data.game_mode)
        if self.game_service is None:
            raise ValueError(_("Unknown game mode: {game_mode}".format(game_mode=data.game_mode)))

        is_user_authenticated = self.game_service.user_accept(self.session_id, data.token, data.continents)

        message = WebsocketMessage(
            type="user_accept",
            payload={
                "isUserAuthenticated": is_user_authenticated,
            },
        )
        self.send_json(message.model_dump(by_alias=True))

        # Initial questions
        self.send_questions()

    def send_questions(self):
        questions = self.game_service.get_questions(self.session_id)
        message = WebsocketMessage(type="new_questions", payload=questions.model_dump(by_alias=True))
        self.send_json(message.model_dump(by_alias=True))

    def answer_result(self, content: dict[int, str], skipped: bool = False):
        question_id = int(content["id"])
        answer_submitted = content["answer"] if not skipped else ""
        user = self.game_service.user_get(self.session_id)

        is_correct, country, *remaining_to_guess = self.game_service.check_answer(
            self.session_id, question_id, answer_submitted, user
        )

        # for countries with several cities as capital
        remaining_to_guess = remaining_to_guess[0] if remaining_to_guess else 0

        current_streak, game_over, best_streak = self.game_service.user_get_streak_score(
            self.session_id, user, is_correct, remaining_to_guess
        )

        correct_answer: CorrectAnswer = []  # needs to be a lis, as countries can have several cities as capital
        if skipped or game_over:
            # On skips, we send the correct answer to the frontend
            # On a challenge; game over is possible, we also send the correct answer to the frontend
            correct_answer: CorrectAnswer = self.game_service.get_correct_answer(user, country, self.language)

        message = WebsocketMessage(
            type="answer_result",
            payload=AnswerResult(
                id=content["id"],
                is_correct=is_correct,
                current_streak=current_streak,
                best_streak=best_streak,
                correct_answer=correct_answer,
                remaining_to_guess=remaining_to_guess,
            ).model_dump(by_alias=True),
        )

        self.send_json(message.model_dump(by_alias=True))
