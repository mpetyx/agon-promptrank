from django.test import TestCase
from .models import CustomUser, Department

class UserModelTests(TestCase):
    def test_department_creation(self):
        dept = Department.objects.create(name="QA", handicap_multiplier=1.2)
        self.assertEqual(str(dept), "QA")
        
    def test_user_creation(self):
        user = CustomUser.objects.create(username="testuser", email="test@test.com")
        self.assertEqual(str(user), "test@test.com")
        
    def test_anonymized_user(self):
        user = CustomUser.objects.create(username="anon", is_anonymized=True)
        self.assertTrue("Anonymous" in str(user))
