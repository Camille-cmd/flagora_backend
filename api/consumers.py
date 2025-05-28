from channels.generic.websocket import JsonWebsocketConsumer

from api.schema import WebsocketMessage, AnswerResult
from api.services.game import GameService


class GameConsumer(JsonWebsocketConsumer):
    questions = []

    def connect(self):
        self.accept()
        # Initial questions
        self.send_questions()

    def receive_json(self, content, **kwargs):
        match content["type"]:
            case "answer_submission":
                self.answer_result(content)
            case "request_questions":
                self.send_questions()
            case _:
                raise ValueError(f"Unknown message type: {content['type']}")

    def send_questions(self):
        questions = GameService.get_questions(self.channel_name)
        self.questions = questions
        message = WebsocketMessage(
            type="new_questions",
            payload=questions.model_dump(by_alias=True)
        )
        self.send_json(message.model_dump(by_alias=True))

    def answer_result(self, content: dict[int, str]):
        question_id = int(content["id"])
        answer_submitted = content["answer"]
        is_correct = GameService.check_answer(self.channel_name, question_id, answer_submitted, self.scope["user"])

        message = WebsocketMessage(
            type="answer_result",
            payload=AnswerResult(
                id=content["id"],
                is_correct=is_correct
            ).model_dump(by_alias=True)
        )

        self.send_json(message.model_dump(by_alias=True))
