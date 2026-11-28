import unittest
from src.mod import add
class T(unittest.TestCase):
    def test_independent(self):
        self.assertEqual(add(1), [1])
        self.assertEqual(add(2), [2])
