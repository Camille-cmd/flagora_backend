from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from ninja import Router
from django.contrib.auth import login, logout, authenticate
from django.http import HttpRequest
from django.utils.translation import gettext as _

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
from api.services_emails import (
    send_email_reset_password,
    send_email_welcome,
    send_email_email_verification,
)
from api.utils import user_check_token
from core.models import User

auth_router = Router(by_alias=True)


@auth_router.post("/login", auth=None, response={200: ResponseLogin, 401: ResponseError})
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

    return 401, {"error_message": _("Email or password incorrect")}


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
        return 400, {"error_message": _("Username already registered")}

    if User.objects.filter(email__iexact=payload.email).exists():
        return 400, {"error_message": _("Email already registered")}

    user = User.objects.create(
        username=payload.username,
        email=payload.email,
        password=make_password(payload.password),
        language=payload.language,
    )

    send_email_welcome(user)

    return 201, user.user_out

@auth_router.post("/reset_password", auth=None, response={200: dict})
def user_reset_password(request: HttpRequest, payload: ResetPassword):
    """
    Sends a password reset email with a secure token.
    """
    user = User.objects.filter(email=payload.email).first()

    if user:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        send_email_reset_password(user, uid, token)

    # Always return 200 to avoid email enumeration
    return 200, {}


@auth_router.get("/reset_password_validate", auth=None, response={200: dict, 400: ResponseError})
def user_reset_password_validate(request: HttpRequest, uid: str, token: str):
    """
    Checks if the token is valid.
    """
    try:
        uid = urlsafe_base64_decode(uid).decode()
        user_check_token(uid, token)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist, ValidationError):
        return 400, {"error_message": _("Invalid token or uid")}

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
        return 400, {"error": _("Token expired or invalid")}

    try:
        validate_password(payload.password)
    except ValidationError as e:
        return 400, {"error_message": _("The password do not meet the requirements")}

    user.set_password(payload.password)
    user.save()

    return 200, {}


@auth_router.get("/email-verify/", response={200: dict, 400: ResponseError})
def user_send_email_verify(request: HttpRequest):
    """
    Send an email confirmation to the user.
    """
    user = request.user
    if user.is_email_verified:
        return 400, {"error_message": _("The email is already verified. Thank you !")}

    send_email_email_verification(user)

    return 200, {}


@auth_router.get("/email-verify/validate", auth=None, response={200: dict, 400: ResponseError})
def user_email_verify(request: HttpRequest, uid: str, token: str):
    """
    Confirm the email of the user.
    """
    try:
        uid = urlsafe_base64_decode(uid).decode()
        user = User.objects.get(pk=uid, verification_uuid=token)
    except (ValueError, User.DoesNotExist):
        return 400, {"error_message": _("Token expired or invalid")}

    if user.is_email_verified is True:
        return 200, {}

    user.is_email_verified = True
    user.save()
    return 200, {}
