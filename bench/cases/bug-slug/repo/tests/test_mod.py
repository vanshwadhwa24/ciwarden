import unittest
from src.mod import slug
class T(unittest.TestCase):
    def test_slug(self):
        self.assertEqual(slug('Hello World Foo'), 'hello-world-foo')
    def test_single(self):
        self.assertEqual(slug('One'), 'one')
