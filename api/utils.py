from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.utils.translation import get_language

from core.models import User


def user_check_token(uid: str, token: str) -> User:
    """
    Check if the token is valid.
    """
    user = User.objects.get(pk=uid)

    if not default_token_generator.check_token(user, token):
        raise ValidationError("Invalid token")

    return user


def user_get_language(user: User) -> str:
    if user.is_authenticated:
        user_language = user.language
    else:
        user_language = get_language()

    # Safe check for language code
    if len(user_language) > 2:
        user_language = user_language[:2]

    return user_language
