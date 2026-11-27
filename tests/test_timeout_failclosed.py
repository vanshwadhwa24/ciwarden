"""A timeout-class failure must escalate before any model call or patch (post-change guard, see bench/results/POSTCHANGE.md)."""
import os, sys, json, unittest, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ciwarden import agent

class NoModel:
    def complete(self, prompt):
        raise AssertionError("model must not be called for a timeout-class failure")

class T(unittest.TestCase):
    def test_signs(self):
        self.assertTrue(agent.TIMEOUT_SIGNS.search("Job cancelled: exceeded 4s step timeout"))
        self.assertFalse(agent.TIMEOUT_SIGNS.search("AssertionError: 3 != 4"))

if __name__ == "__main__":
    unittest.main()
