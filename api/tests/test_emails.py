import uuid

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from api.services.emails import send_email_email_verification, send_email_reset_password, send_email_welcome
from flagora.settings import FRONTEND_URL
from flagora.tests.base import FlagoraTestCase

User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class TestEmails(FlagoraTestCase):
    def test_send_email_reset_password_french(self):
        """
        Test that the password reset email is sent correctly in French.
        """
        self.user.language = "fr"
        self.user.email = "user@example.com"
        self.user.save()

        uid = "uid123"
        token = "token456"

        send_email_reset_password(self.user, uid, token)

        # One email should be sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        # Subject and recipient check
        self.assertIn("Flagora - Réinitialiser votre mot de passe", email.subject)
        self.assertIn(self.user.email, email.to)

        # URL and language check
        reset_url = f"{FRONTEND_URL}/reset-password/{uid}/{token}"
        self.assertIn(reset_url, email.body)
        self.assertIn("réinitialiser votre mot de passe", email.body)

        # Ensure HTML part is present
        self.assertEqual(email.alternatives[0].mimetype, "text/html")

    def test_send_email_welcome_french(self):
        """
        Sends the welcome email in French using the correct confirmation URL.
        """
        self.user.language = "fr"
        self.user.email = "testuser@example.com"
        self.user.verification_uuid = uuid.uuid4()
        self.user.save()

        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = self.user.verification_uuid

        send_email_welcome(self.user)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        # Check subject and recipient
        self.assertIn("Flagora - Bienvenue", email.subject)
        self.assertIn(self.user.email, email.to)

        # Check content
        expected_url = f"{FRONTEND_URL}/email-confirmation/{uid}/{token}"
        self.assertIn(expected_url, email.body)
        self.assertIn(str(timezone.now().year), email.body)

        # Ensure HTML part is present
        self.assertEqual(email.alternatives[0].mimetype, "text/html")
        self.assertIn("Merci d'avoir créé votre compte", email.body)

    def test_send_email_verification_french(self):
        """
        Sends the email verification message in French.
        """
        self.user.language = "fr"
        self.user.email = "testuser@example.com"
        self.user.verification_uuid = uuid.uuid4()
        self.user.save()

        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = self.user.verification_uuid

        send_email_email_verification(self.user)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        # Check subject and recipient
        self.assertIn("Flagora - Confirmer votre adresse e-mail", email.subject)
        self.assertIn(self.user.email, email.to)

        # Check email content
        expected_url = f"{FRONTEND_URL}/email-confirmation/{uid}/{token}"
        self.assertIn(expected_url, email.body)
        self.assertIn(str(timezone.now().year), email.body)

        # Ensure HTML part is present
        self.assertEqual(email.alternatives[0].mimetype, "text/html")
