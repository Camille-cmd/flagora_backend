import uuid
from django.core.exceptions import ValidationError
from django.contrib.auth.tokens import default_token_generator

from api.utils import user_check_token
from core.models import User
from flagora.tests.base import FlagoraTestCase


class UserCheckTokenTestCase(FlagoraTestCase):
    def setUp(self):
        super().setUp()
        self.user.verification_uuid = uuid.uuid4()
        self.user.save()
        self.token = default_token_generator.make_token(self.user)

    def test_valid_token(self):
        user = user_check_token(uid=self.user.id, token=self.token)
        self.assertEqual(user, self.user)

    def test_invalid_token(self):
        invalid_token = "invalid-token"
        with self.assertRaises(ValidationError):
            user_check_token(uid=self.user.id, token=invalid_token)

    def test_user_does_not_exist(self):
        """
        Vérifie la gestion lorsque l'utilisateur n'existe pas.
        """
        non_existing_uid = 99999  # non-existing user ID
        with self.assertRaises(User.DoesNotExist):
            user_check_token(uid=non_existing_uid, token=self.token)
