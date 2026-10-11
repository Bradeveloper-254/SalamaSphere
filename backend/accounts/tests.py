from django.test import TestCase

from .models import User


class UserModelTests(TestCase):
    def test_user_can_be_created(self):
        user = User.objects.create_user(
            username="test_survivor",
            email="survivor@example.com",
            password="TestPassword123!",
        )

        self.assertEqual(user.username, "test_survivor")
        self.assertEqual(user.role, User.Role.SURVIVOR)
        self.assertTrue(user.check_password("TestPassword123!"))