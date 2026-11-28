import unittest
from src.mod import sign
class T(unittest.TestCase):
    def test_zero_positive(self):
        self.assertEqual(sign(0), 1)
    def test_zero_negative(self):
        self.assertEqual(sign(0), -1)
