from django.test import TestCase, Client
from unittest.mock import patch
from core.models import User

class UserLoginTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = "/api/login/"
        self.user_data = {
            "email": "testuser@example.com",
            "password": "securepassword123",
        }
        self.user = User.objects.create_user(
            username="testuser",
            email=self.user_data["email"],
            password=self.user_data["password"],
        )

    @patch("django.contrib.auth.authenticate")
    @patch("django.contrib.auth.login")
    def test_user_login_successful(self, mock_login, mock_authenticate):
        mock_authenticate.return_value = self.user
        response = self.client.post(self.login_url, data=self.user_data, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["session_id"], self.client.session.session_key)
        mock_login.assert_called_once()

    @patch("django.contrib.auth.authenticate")
    def test_user_login_invalid_credentials(self, mock_authenticate):
        mock_authenticate.return_value = None
        response = self.client.post(self.login_url, data=self.user_data, content_type="application/json")
        self.assertEqual(response.status_code, 401)
        self.assertIn("error_message", response.json())
        self.assertEqual(response.json()["error_message"], "Email or password incorrect")
    
    def test_missing_fields_in_payload(self):
        incomplete_payload = {"email": "testuser@example.com"}
        response = self.client.post(self.login_url, data=incomplete_payload, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.json().get("error_message"))
