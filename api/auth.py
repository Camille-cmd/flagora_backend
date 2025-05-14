from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from ninja import Router
from django.contrib.auth import login, logout, authenticate
from django.http import HttpRequest

from api.schema import (
    ResponseLogin,
    Register,
    Login,
    ResponseUserOut,
    ResponseError,
    ResponseCheckUsername,
    CheckUsername,
    ResetPassword,
    ResetPasswordConfirm,
)
from core.models import User
from flagora.settings import FRONTEND_URL, DEFAULT_FROM_EMAIL
from utils import user_check_token

auth_router = Router(by_alias=True)


@auth_router.post("/login", response={200: ResponseLogin, 401: ResponseError}, auth=None)
def user_login(request: HttpRequest, payload: Login):
    """
    Login a user.
    """
    # Login with username or email
    user = authenticate(request, username=payload.email, password=payload.password)
    if user is not None:
        login(request, user)
        session_id = request.session.session_key
        return 200, {"session_id": session_id}

    return 401, {"error": "Invalid credentials", "code": "invalid_credentials"}


@auth_router.get("/logout", response={200: dict})
def user_logout(request: HttpRequest):
    """
    Logout a user.
    """
    logout(request)

    return 200, {}


@auth_router.post("/check_username", auth=None, response={200: ResponseCheckUsername})
def user_check_username(request: HttpRequest, payload: CheckUsername):
    """
    Check if a username is available.
    """
    is_available = not User.objects.filter(username__iexact=payload.username).exists()
    return 200, {"available": is_available}


@auth_router.post("/register", auth=None, response={201: ResponseUserOut, 400: ResponseError})
def user_register(request: HttpRequest, payload: Register):
    """
    Register a new user.
    """
    if User.objects.filter(username__iexact=payload.username).exists():
        return 400, {"error": "Username already registered", "code": "username_already_registered"}

    if User.objects.filter(email__iexact=payload.email).exists():
        return 400, {"error": "Email already registered", "code": "email_already_registered"}

    user = User.objects.create(
        username=payload.username,
        email=payload.email,
        password=make_password(payload.password),
    )
    return 201, {"username": user.username, "email": user.email, "user_id": user.id}


@auth_router.get("/me", auth=None, response={ 200: ResponseUserOut, 401: ResponseError})
def user_me(request: HttpRequest):
    """"
    Get the current user information.
    """
    user = request.user
    if not user.is_authenticated:
        return 401, {"error": "Not authenticated", "code": "not_authenticated"}

    return 200, {"username": user.username, "email": user.email, "user_id": user.id}


@auth_router.post("/reset_password", auth=None, response={200: dict})
def user_reset_password(request: HttpRequest, payload: ResetPassword):
    """
    Sends a password reset email with a secure token.
    """
    user = User.objects.filter(email=payload.email).first()

    if user:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        reset_url = f"{FRONTEND_URL}/reset-password/{uid}/{token}"

        send_mail(
            subject="Réinitialisation de votre mot de passe",
            message=f"Bonjour,\n\nVous pouvez réinitialiser votre mot de passe ici :\n\n{reset_url}\n\nCe lien est valable pendant un temps limité.",
            from_email=DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )

    # Always return 200 to avoid email enumeration
    return 200, {"message": "If this email exists, a reset link has been sent."}


@auth_router.get("/reset_password_validate", auth=None, response={200: dict, 400: ResponseError})
def user_reset_password_validate(request: HttpRequest, uid: str, token: str):
    """
    Checks if the token is valid.
    """
    try:
        uid = urlsafe_base64_decode(uid).decode()
        user_check_token(uid, token)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist, ValidationError):
        return 400, {"error": "Invalid token or uid", "code": "invalid_token"}

    return 200, {}


@auth_router.post("/reset_password_confirm", auth=None, response={200: dict, 400: ResponseError})
def user_reset_password_confirm(request: HttpRequest, payload: ResetPasswordConfirm):
    """
    Sets a new password for the user from the reset password token.
    """
    try:
        uid = urlsafe_base64_decode(payload.uid).decode()
        user = user_check_token(uid, payload.token)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist, ValidationError):
        return 400, {"error": "Invalid token or uid", "code": "invalid_token"}

    try:
        validate_password(payload.password)
    except ValidationError as e:
        return 400, {"error": str(e), "code": "invalid_password"}

    user.set_password(payload.password)
    user.save()

    return 200, {}
