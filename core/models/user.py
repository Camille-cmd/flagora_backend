import uuid

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _

from api.schema import UserPreferences
from flagora import settings


class CustomUsernameValidator(UnicodeUsernameValidator):
    """
    Prevent the username from containing any @ character.
    This allows to log in the user with either the username or the email.
    """

    regex = r"^[\w.-]+\Z"
    message = _("Enter a valid username. This value may contain only letters, numbers, and ./-/_ characters.")


class User(AbstractUser):
    username_validator = CustomUsernameValidator()

    email = models.EmailField(unique=True)
    is_email_verified = models.BooleanField(default=False, verbose_name=_("is email verified"))
    language = models.CharField(max_length=2, choices=settings.LANGUAGES, verbose_name=_("language"))
    verification_uuid = models.UUIDField(
        default=uuid.uuid4,
        verbose_name=_("Email verification uuid"),
        editable=False,
        unique=True,
    )

    def __str__(self):
        return self.email

    @property
    def user_out(self):
        """
        Return the user information to be sent to the frontend.
        """
        from .user_preference_game_mode import UserPreferenceGameMode

        tooltip_preferences = []
        try:
            user_preferences = UserPreferenceGameMode.objects.filter(user=self).values("game_mode", "show_tips")
            for user_preference in user_preferences:
                tooltip_preferences.append(
                    UserPreferences(
                        show_tips=user_preference["show_tips"],
                        game_mode=user_preference["game_mode"],
                    )
                )
        except UserPreferenceGameMode.DoesNotExist:
            tooltip_preferences = None

        return {
            "user_id": self.id,
            "username": self.username,
            "email": self.email,
            "is_email_verified": self.is_email_verified,
            "language": self.language,
            "tooltip_preferences": tooltip_preferences,
        }

    @property
    def email_tokens(self):
        """
        Get the uid and confirmation token for the email verification.
        """
        uid = urlsafe_base64_encode(force_bytes(self.pk))
        confirm_token = self.verification_uuid
        return uid, confirm_token
