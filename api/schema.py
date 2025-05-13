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

class ResponseLogin(BaseSchema):
    session_id: str

class ResponseError(BaseSchema):
    error: str

class Login(BaseSchema):
    email: str
    password: str

class Register(BaseSchema):
    username: str
    password: str
    email: str
