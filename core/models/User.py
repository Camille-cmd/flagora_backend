from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import ASCIIUsernameValidator, UnicodeUsernameValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

class CustomUsernameValidator(UnicodeUsernameValidator):
    """
    Prevent the username from containing any @ character.
    This allows to log in the user with either the username or the email.
    """
    regex = r"^[\w.-]+\Z"
    message = _(
        "Enter a valid username. This value may contain only letters, "
        "numbers, and ./-/_ characters."
    )

class User(AbstractUser):
    username_validator = CustomUsernameValidator()

    email = models.EmailField(unique=True)

    def __str__(self):
        return self.email
