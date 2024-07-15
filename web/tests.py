from django.test import TestCase
from .models import Post


# Create your tests here.


class ModelTestCase(TestCase):
    def setUp(self):
        self.post = Post.objects.create(title="django", author="ekeeya", slug="django")

    def test_instance(self):
        self.assertTrue(isinstance(self.post, Post))
