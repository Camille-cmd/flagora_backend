from channels.generic.websocket import JsonWebsocketConsumer
from django.utils.translation import gettext as _

from api.game_registery import GameServiceRegistry
from api.schema import AnswerResult, CorrectAnswer, SetUserWebsocket, WebsocketMessage
from api.services.game_modes.base_game import GameService


class GameConsumer(JsonWebsocketConsumer):
    questions = []
    game_service: GameService

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
            case _:
                raise ValueError(f"Unknown message type: {content['type']}")

    def store_user(self, content: dict):
        data = SetUserWebsocket.model_validate(content, by_alias=True)
        self.game_service = GameServiceRegistry.get_game_service(data.game_mode)
        if self.game_service is None:
            raise ValueError(_("Unknown game mode: {game_mode}".format(game_mode=data.game_mode)))

        token = data.token
        is_user_authenticated = self.game_service.user_accept(self.channel_name, token)

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
        questions = self.game_service.get_questions(self.channel_name)
        self.questions = questions
        message = WebsocketMessage(type="new_questions", payload=questions.model_dump(by_alias=True))
        self.send_json(message.model_dump(by_alias=True))

    def answer_result(self, content: dict[int, str], skipped: bool = False):
        question_id = int(content["id"])
        answer_submitted = content["answer"] if not skipped else ""
        user = self.game_service.user_get(self.channel_name)

        is_correct, country, *remaining_to_guess = self.game_service.check_answer(
            self.channel_name, question_id, answer_submitted, user
        )

        # for countries with several cities as capital
        remaining_to_guess = remaining_to_guess[0] if remaining_to_guess else None

        current_streak, game_over, best_streak = self.game_service.user_get_streak_score(
            self.channel_name, user, is_correct, remaining_to_guess
        )

        correct_answer: CorrectAnswer = []  # needs to be a lis, as countries can have several cities as capital
        if skipped or game_over:
            # On skips, we send the correct answer to the frontend
            # On a challenge; game over is possible, we also send the correct answer to the frontend
            correct_answer: CorrectAnswer = self.game_service.get_correct_answer(user, country)

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
