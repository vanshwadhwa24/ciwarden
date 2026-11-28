import unittest
from src.mod import get_port
class T(unittest.TestCase):
    def test_default(self):
        self.assertEqual(get_port({}), 8080)
    def test_set(self):
        self.assertEqual(get_port({'port': 9000}), 9000)
