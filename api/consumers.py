from channels.generic.websocket import JsonWebsocketConsumer
from django.templatetags.i18n import language
from django.utils.translation import get_language

from api.schema import WebsocketMessage, AnswerResult, SetUserWebsocket
from api.services.game import GameService


class GameConsumer(JsonWebsocketConsumer):
    questions = []

    def connect(self):
        self.accept()
        # Initial questions
        self.send_questions()

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

    def store_user(self, content: SetUserWebsocket):
        token = content["token"]
        is_user_authenticated = GameService.user_accept(self.channel_name, token)

        message = WebsocketMessage(
            type="user_accept",
            payload={
                "is_user_authenticated": is_user_authenticated,
            }
        )
        self.send_json(message.model_dump(by_alias=True))

    def send_questions(self):
        questions = GameService.get_questions(self.channel_name)
        self.questions = questions
        message = WebsocketMessage(
            type="new_questions",
            payload=questions.model_dump(by_alias=True)
        )
        self.send_json(message.model_dump(by_alias=True))

    def answer_result(self, content: dict[int, str], skipped: bool = False):
        question_id = int(content["id"])
        answer_submitted = content["answer"]
        user = GameService.user_get(self.channel_name)

        is_correct, country = GameService.check_answer(self.channel_name, question_id, answer_submitted, user)

        correct_answer = ""
        code = ""
        wikipedia_link = ""
        if skipped:
            # On skips, we send the correct answer to the frontend
            user_language = get_language()
            if user.is_authenticated:
                user_language = user.language
            name_field = f"name_{user_language}"
            correct_answer = getattr(country, name_field)
            code = country.iso2_code
            wikipedia_link = f"https://fr.wikipedia.org/wiki/{correct_answer}"

        message = WebsocketMessage(
            type="answer_result",
            payload=AnswerResult(
                id=content["id"],
                is_correct=is_correct,
                correct_answer=correct_answer,
                code=code,
                wikipedia_link=wikipedia_link
            ).model_dump(by_alias=True)
        )

        self.send_json(message.model_dump(by_alias=True))
