from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from core.models import User
from flagora import settings
from flagora.settings import FRONTEND_URL


def send_email_reset_password(user: User, uid: str, token: str):
    with translation.override(user.language):
        subject = _("Flagora - Reset your password")
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [user.email]

        reset_url = f"{FRONTEND_URL}/reset-password/{uid}/{token}"

        context = {
            "reset_url": reset_url,
            "current_year": timezone.now().year,
        }

        text_content = render_to_string("emails/reset_password.txt", context)
        html_content = render_to_string("emails/reset_password.html", context)

    email = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    email.attach_alternative(html_content, "text/html")
    email.send()


def send_email_welcome(user: User):
    with translation.override(user.language):
        subject = _("Flagora - Bienvenue")
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [user.email]

        uid, email_token = user.email_tokens

        context = {
            "confirmation_url": f"{settings.FRONTEND_URL}/email-confirmation/{uid}/{email_token}",
            "current_year": timezone.now().year,
        }

        text_content = render_to_string("emails/welcome.txt", context)
        html_content = render_to_string("emails/welcome.html", context)

    email = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    email.attach_alternative(html_content, "text/html")
    email.send()


def send_email_email_verification(user: User):
    with translation.override(user.language):
        subject = _("Flagora - Confirm your email address")
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [user.email]

        uid, email_token = user.email_tokens

        context = {
            "confirmation_url": f"{settings.FRONTEND_URL}/email-confirmation/{uid}/{email_token}",
            "current_year": timezone.now().year,
        }

        text_content = render_to_string("emails/email_verify.txt", context)
        html_content = render_to_string("emails/email_verify.html", context)

    email = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    email.attach_alternative(html_content, "text/html")
    email.send()
