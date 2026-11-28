import unittest
from src.mod import page
class T(unittest.TestCase):
    def test_page(self):
        self.assertEqual(page(list(range(10)), 1, 3), [3, 4, 5])
    def test_first(self):
        self.assertEqual(page(list(range(10)), 0, 2), [0, 1])
