import json, os, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock

from ciwarden import llm


class H(BaseHTTPRequestHandler):
    SCRIPT = []  # list of (status, body)
    CALLS = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0)); self.rfile.read(n)
        H.CALLS.append(self.path)
        status, body = H.SCRIPT.pop(0) if H.SCRIPT else (200, {"choices": [{"message": {"content": "ok"}}], "usage": {"total_tokens": 3}})
        b = json.dumps(body).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers()
        self.wfile.write(b)


class CompatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def env(self, d, **extra):
        e = {"CIWARDEN_API_BASE": self.base, "CIWARDEN_API_KEY": "k", "CIWARDEN_QUOTA_FILE": os.path.join(d, "q.json"),
             "CIWARDEN_MAX_RPM": "100", "CIWARDEN_MAX_RPD": "100", "CIWARDEN_MIN_INTERVAL_S": "0", "CIWARDEN_503_BACKOFF_S": "0.01"}
        e.update(extra)
        return mock.patch.dict(os.environ, e)

    def test_503_retried_once_then_succeeds(self):
        with tempfile.TemporaryDirectory() as d, self.env(d):
            H.SCRIPT = [(503, {"error": "overloaded"}), (200, {"choices": [{"message": {"content": "fixed"}}], "usage": {"total_tokens": 5}})]
            H.CALLS.clear()
            r = llm.OpenAICompatModel("m").complete("p")
            self.assertEqual(r["text"], "fixed")
            self.assertEqual(len(H.CALLS), 2)  # retry made a second real request
            st = json.load(open(os.path.join(d, "q.json")))
            self.assertEqual(st["n"], 2)  # both attempts counted against the limiter

    def test_second_503_raises_model_error(self):
        with tempfile.TemporaryDirectory() as d, self.env(d):
            H.SCRIPT = [(503, {}), (503, {})]
            with self.assertRaises(llm.ModelError):
                llm.OpenAICompatModel("m").complete("p")

    def test_min_interval_waits_between_calls(self):
        with tempfile.TemporaryDirectory() as d, self.env(d, CIWARDEN_MIN_INTERVAL_S="0.2"):
            H.SCRIPT = []
            import time
            t0 = time.time()
            m = llm.OpenAICompatModel("m")
            m.complete("p1"); m.complete("p2")
            self.assertGreaterEqual(time.time() - t0, 0.2)

    def test_daily_limit_still_hard_stops(self):
        with tempfile.TemporaryDirectory() as d, self.env(d, CIWARDEN_MAX_RPD="1"):
            H.SCRIPT = []
            m = llm.OpenAICompatModel("m")
            m.complete("p1")
            with self.assertRaises(llm.QuotaError):
                m.complete("p2")


if __name__ == "__main__":
    unittest.main()
