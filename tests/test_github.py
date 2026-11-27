"""GitHub actuator against a local fake API server (no network, no token)."""
import json, os, sys, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ciwarden import github, policy

CALLS = []


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        CALLS.append(("GET", self.path))
        if self.path.endswith("/repos/o/r"):
            return self._send({"default_branch": "main"})
        if "git/ref/heads/main" in self.path:
            return self._send({"object": {"sha": "abc123"}})
        if "/contents/" in self.path:
            return self._send({"message": "Not Found"}, 404)
        self._send({}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0)); body = json.loads(self.rfile.read(n) or b"{}")
        CALLS.append(("POST", self.path, body))
        self._send({"html_url": "http://x/pr/1"} if self.path.endswith("pulls") else {"html_url": "http://x/i/1"}, 201)

    def do_PUT(self):
        n = int(self.headers.get("Content-Length", 0)); body = json.loads(self.rfile.read(n) or b"{}")
        CALLS.append(("PUT", self.path, body))
        self._send({}, 201)


class GhTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.api = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def act(self):
        CALLS.clear()
        return github.GitHubActuator(github.Client("o/r", "faketoken", api=self.api), policy.KillSwitch("/nonexistent/KILL"))

    def test_pr_flow_branch_and_author(self):
        r = self.act().open_pr("ciwarden/fix-x", [{"path": "src/a.py", "content": "x=1\n"}], "fix: x", "body")
        self.assertEqual(r["artifact"], "http://x/pr/1")
        ref = [c for c in CALLS if c[0] == "POST" and c[1].endswith("git/refs")][0][2]
        self.assertEqual(ref["ref"], "refs/heads/ciwarden/fix-x")
        put = [c for c in CALLS if c[0] == "PUT"][0][2]
        self.assertEqual(put["branch"], "ciwarden/fix-x")
        self.assertEqual(put["committer"]["email"], "vanshreads@gmail.com")

    def test_never_writes_default_branch_or_workflows(self):
        for branch, path in (("main", "src/a.py"), ("ciwarden/x", ".github/workflows/ci.yml"), ("ciwarden/x", "tests/t.py")):
            a = self.act()
            with self.assertRaises(policy.PolicyError):
                a.open_pr(branch, [{"path": path, "content": "x"}], "t", "b")
            self.assertFalse([c for c in CALLS if c[0] in ("PUT", "POST")], (branch, path))

    def test_kill_switch_blocks_writes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            k = os.path.join(d, "KILL"); open(k, "w").close()
            a = github.GitHubActuator(github.Client("o/r", "t", api=self.api), policy.KillSwitch(k))
            CALLS.clear()
            with self.assertRaises(policy.PolicyError):
                a.open_issue("t", "b")
            self.assertEqual(CALLS, [])


if __name__ == "__main__":
    unittest.main()
