import unittest
from src.mod import price
class T(unittest.TestCase):
    def test_price(self):
        self.assertEqual(price(200, 10), 180)
    def test_zero(self):
        self.assertEqual(price(50, 0), 50)
