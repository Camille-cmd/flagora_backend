from django.contrib.auth.hashers import make_password
from ninja import Router
from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest
from ninja.errors import HttpError
from ninja.responses import Response

from api.schema import ResponseLogin, Register, Login, ResponseUserOut, ResponseError
from core.models import User

auth_router = Router(by_alias=True)



@auth_router.post("/login", response={200: ResponseLogin, 401: ResponseError}, auth=None)
def user_login(request: HttpRequest, payload: Login):
    """
    Login a user.
    """
    # if request.user.is_authenticated:
    #     return 200, {"success": True, "message": "Already logged in"}
    user = authenticate(request, email="superuser@localhost", password="password")
    if user is not None:
        login(request, user)
        session_id = request.session.session_key
        return 200, {"session_id": session_id, "user": {"username": user.username, "email": user.email, "user_id": user.id}}

    return 401, {"error": "Invalid credentials"}

@auth_router.get("/logout", response={200: dict})
def user_logout(request: HttpRequest):
    """
    Logout a user.
    """
    logout(request)

    return 200, {}


@auth_router.post("/register", auth=None, response={201: ResponseUserOut, 400: dict})
def user_register(request: HttpRequest, payload: Register):
    """
    Register a new user.
    """
    if User.objects.filter(username=payload.username).exists():
        raise HttpError(400, "Username already taken")
    if User.objects.filter(email=payload.email).exists():
        raise HttpError(400, "Email already registered")

    user = User.objects.create(
        username=payload.username,
        email=payload.email,
        password=make_password(payload.password),
    )
    return 201, {"username": user.username, "email": user.email, "user_id": user.id}

@auth_router.get("/me", response={ 200: ResponseUserOut, 401: ResponseError})
def user_me(request: HttpRequest):
    user = request.user
    if not user.is_authenticated:
        return 401, {"error": "Not authenticated"}

    return 200, {"username": user.username, "email": user.email, "user_id": user.id}
