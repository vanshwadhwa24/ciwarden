import unittest
from src.mod import total
class T(unittest.TestCase):
    def test_half(self):
        self.assertEqual(total(2.5), 3)
    def test_other(self):
        self.assertEqual(total(3.5), 4)
