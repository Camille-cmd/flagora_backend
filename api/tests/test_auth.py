import uuid
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from flagora.tests.base import FlagoraTestCase

User = get_user_model()

class TestAuth(FlagoraTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client(headers={"Content-Type": "application/json"})
        self.login_url = reverse("api-1.0.0:user_login")
        self.logout_url = reverse("api-1.0.0:user_logout")
        self.register_url = reverse("api-1.0.0:user_register")
        self.check_username_url = reverse("api-1.0.0:user_check_username")
        self.reset_password_url = reverse("api-1.0.0:user_reset_password")
        self.reset_password_confirm_url = reverse("api-1.0.0:user_reset_password_confirm")
        self.send_email_verify_url = reverse("api-1.0.0:user_send_email_verify")
        self.email_verify_url = reverse("api-1.0.0:user_email_verify")

    #### LOGIN TESTS ####
    def test_login_success(self):
        payload = {"email": self.user.email, "password": "securepassword123"}
        response = self.client.post(self.login_url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 200, msg=response.content.decode())
        self.assertIn("sessionId", response.json())

    def test_login_failure(self):
        payload = {"email": self.user.email, "password": "wrongpassword"}
        response = self.client.post(self.login_url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 401, msg=response.content.decode())
        self.assertEqual(response.json()["errorMessage"], "Email or password incorrect")

    #### LOGOUT TESTS ####
    def test_logout(self):
        headers = self.user_do_login()
        response = self.client.get(self.logout_url, headers=headers)
        self.assertEqual(response.status_code, 200, msg=response.content.decode())

    #### CHECK USERNAME TESTS ####
    def test_check_username_available(self):
        payload = {"username": "newusername"}
        response = self.client.post(self.check_username_url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["available"])

    def test_check_username_unavailable(self):
        payload = {"username": self.user.username}
        response = self.client.post(self.check_username_url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["available"])

    #### REGISTRATION TESTS ####
    @patch("api.routes.auth.send_email_welcome")
    def test_register_success(self, mock_send_email):
        payload = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "StrongPassword123",
            "language": "en",
        }
        response = self.client.post(self.register_url,  data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())
        mock_send_email.assert_called_once()

    def test_register_existing_username(self):
        payload = {
            "username": self.user.username,
            "email": "newuser@example.com",
            "password": "StrongPassword123",
            "language": "en",
        }
        response = self.client.post(self.register_url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errorMessage"], "Username already registered")

    def test_register_existing_email(self):
        payload = {
            "username": "newuser",
            "email": self.user.email ,
            "password": "StrongPassword123",
            "language": "en",
        }
        response = self.client.post(self.register_url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errorMessage"], "Email already registered")

    #### RESET PASSWORD TESTS ####
    @patch("api.routes.auth.send_email_reset_password")
    def test_reset_password_success(self, mock_send_email):
        payload = {"email": self.user.email}
        response = self.client.post(self.reset_password_url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        mock_send_email.assert_called_once_with(
            self.user,
            mock_send_email.call_args[0][1],  # Check uid is passed
            mock_send_email.call_args[0][2],  # Check token is passed
        )

    def test_reset_password_no_user(self):
        payload = {"email": "unknown@example.com"}
        response = self.client.post(self.reset_password_url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 200)  # Toujours 200 pour éviter les fuites d'information

    #### RESET PASSWORD CONFIRM TESTS ####
    @patch("api.routes.auth.user_check_token")
    def test_reset_password_confirm_success(self, mock_user_check_token):
        mock_user_check_token.return_value = self.user
        payload = {
            "uid": urlsafe_base64_encode(force_bytes(uuid.uuid4())),  # base64 encoded uuid.uuid4()
            "token": "mock_token",
            "password": "NewStrongPassword123",
        }
        response = self.client.post(self.reset_password_confirm_url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewStrongPassword123"))

    def test_reset_password_confirm_invalid(self):
        payload = {"uid": urlsafe_base64_encode(force_bytes(uuid.uuid4())), "token": "invalid", "password": "password"}
        response = self.client.post(self.reset_password_confirm_url, data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 400)

    #### EMAIL VERIFY TESTS ####
    @patch("api.routes.auth.send_email_email_verification")
    def test_email_verify_success(self, mock_send_email_verify):
        headers = self.user_do_login()
        response = self.client.get(self.send_email_verify_url, headers=headers)
        self.assertEqual(response.status_code, 200)
        mock_send_email_verify.assert_called_once_with(self.user)

    def test_email_verify_already_verified(self):
        self.user.is_email_verified = True
        self.user.save()
        headers = self.user_do_login()
        response = self.client.get(self.send_email_verify_url, headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errorMessage"], "The email is already verified. Thank you !")

    #### EMAIL VERIFY VALIDATE TESTS ####
    def test_email_verify_validate_success(self):
        verification_uuid = uuid.uuid4()
        self.user.verification_uuid = verification_uuid
        self.user.save()
        response = self.client.get(
            self.email_verify_url,
            query_params={"uid": urlsafe_base64_encode(force_bytes(self.user.pk)), "token": verification_uuid},
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)

    def test_email_verify_validate_invalid(self):
        invalid_uuid = urlsafe_base64_encode(force_bytes(uuid.uuid4()))
        invalid_token = uuid.uuid4()
        response = self.client.get(
            self.email_verify_url,
            query_params={"uid": invalid_uuid, "token": invalid_token},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errorMessage"], "Token expired or invalid")
