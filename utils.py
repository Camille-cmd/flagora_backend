from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError

from core.models import User


def user_check_token(uid: str, token: str) -> User:
    """
    Check if the token is valid.
    """
    user = User.objects.get(pk=uid)

    if not default_token_generator.check_token(user, token):
        raise ValidationError("Invalid token")

    return user
