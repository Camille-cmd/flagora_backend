from ninja import Schema
from pydantic.v1.utils import to_lower_camel


class BaseSchema(Schema):
    pass

    class Config:
        populate_by_name = True
        alias_generator = to_lower_camel

class ResponseRegister(BaseSchema):
    user_id: int

class ResponseUserOut(BaseSchema):
    user_id: int
    username: str
    email: str
    is_email_verified: bool
    language: str

class ResponseLogin(BaseSchema):
    session_id: str

class ResponseError(BaseSchema):
    """
    Backend is responsible for clean error messages for the frontend.
    Error messages should be in English and should be translated.
    """
    error_message: str

class ResponseCheckUsername(BaseSchema):
    available: bool

class Login(BaseSchema):
    email: str
    password: str

class Register(BaseSchema):
    email: str
    username: str
    password: str
    language: str

class CheckUsername(BaseSchema):
    username: str

class ResetPassword(BaseSchema):
    email: str

class ResetPasswordValidate(BaseSchema):
    uid: str
    token: str

class ResetPasswordConfirm(BaseSchema):
    uid: str
    token: str
    password: str

class UserLanguageSet(BaseSchema):
    language: str

class UserUpdate(BaseSchema):
    username: str

class UserUpdatePassword(BaseSchema):
    old_password: str
    new_password: str

class WebsocketMessage(BaseSchema):
    type: str
    payload: dict

class NewQuestions(BaseSchema):
    questions: dict[int, str]

class AnswerResult(BaseSchema):
    id: int
    is_correct: bool
    correct_answer: str = ""

class CountryOut(BaseSchema):
    iso2_code: str
    name: str

class CountriesOut(BaseSchema):
    countries: list[CountryOut]

class SetUserWebsocket(BaseSchema):
    type: str
    token: str
