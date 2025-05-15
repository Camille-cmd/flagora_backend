from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _

from flagora import settings


def send_email_reset_password(user, reset_url):
    subject = _("Flagora - Réinitialisation de votre mot de passe")
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = [user.email]

    context = {
        "reset_url": reset_url,
        "current_year": timezone.now().year,
    }


    text_content = render_to_string("emails/reset_password.txt", context)
    html_content = render_to_string("emails/reset_password.html", context)

    email = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    email.attach_alternative(html_content, "text/html")
    email.send()


def send_email_welcome(user):
    subject = _("Flagora - Bienvenue")
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = [user.email]

    context = {
        "current_year": timezone.now().year,
    }

    text_content = render_to_string("emails/welcome.txt", context)
    html_content = render_to_string("emails/welcome.html", context)

    email = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    email.attach_alternative(html_content, "text/html")
    email.send()
