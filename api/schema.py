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
    error: str
    code: str

class ResponseCheckUsername(BaseSchema):
    available: bool

class Login(BaseSchema):
    email: str
    password: str

class Register(BaseSchema):
    email: str
    username: str
    password: str

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
