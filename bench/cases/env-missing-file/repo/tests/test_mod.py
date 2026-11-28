import unittest
from src.mod import load
class T(unittest.TestCase):
    def test_load(self):
        self.assertTrue(load())
