import unittest
from src.mod import top
class T(unittest.TestCase):
    def test_top(self):
        self.assertEqual(top([5, 1, 9, 3], 2), [9, 5])
