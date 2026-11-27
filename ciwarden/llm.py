"""Model access. The model has NO tools: it receives text and returns text. We run OpenCode in an
empty temp directory with bash/edit/webfetch permission denied, and kill it on timeout."""
import hashlib, json, os, subprocess, tempfile, shutil, re

OPENCODE = os.environ.get("CIWARDEN_OPENCODE", "opencode")
DEFAULT_MODEL = os.environ.get("CIWARDEN_MODEL", "opencode/deepseek-v4.1-flash-free")
CONFIG = {"permission": {"bash": "deny", "edit": "deny", "webfetch": "deny", "task": "deny"}}


class ModelError(Exception):
    pass


class QuotaError(ModelError):
    """The hosted free tier refused the call. Do not retry in a loop."""


def extract_json(text):
    """First balanced {...} object in text, parsed. Raises ModelError if none."""
    start = text.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            c = text[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start:i + 1])
                        except json.JSONDecodeError:
                            break
        start = text.find("{", start + 1)
    raise ModelError("no JSON object in model output")


class OpenCodeModel:
    name = "opencode"

    def __init__(self, model=DEFAULT_MODEL, timeout=40):
        self.model, self.timeout = model, timeout

    def complete(self, prompt):
        d = tempfile.mkdtemp(prefix="ciw-llm-")
        try:
            with open(os.path.join(d, "opencode.json"), "w") as f:
                json.dump(CONFIG, f)
            try:
                p = subprocess.run([OPENCODE, "run", "--print-logs", "-m", self.model, "--format", "json", prompt],
                                   cwd=d, capture_output=True, text=True, timeout=self.timeout,
                                   env={k: v for k, v in os.environ.items()
                                        if not k.upper().endswith(("TOKEN", "KEY", "SECRET", "PASSWORD"))})
            except subprocess.TimeoutExpired as e:
                err = e.stderr.decode(errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
                if "Free usage limit reached" in err:
                    raise QuotaError("free usage limit reached (hosted free tier, resets daily; see README)")
                raise ModelError("model call timed out")
            text, tokens, tool_calls = "", 0, 0
            for line in p.stdout.splitlines():
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                part = ev.get("part", {})
                if ev.get("type") == "text":
                    text += part.get("text", "")
                if ev.get("type") == "tool_use" or part.get("type") == "tool":
                    tool_calls += 1
                if ev.get("type") == "step_finish":
                    tokens += part.get("tokens", {}).get("total", 0)
            if not text:
                raise ModelError("empty model output")
            return {"text": text, "tokens": tokens, "tool_calls_attempted": tool_calls, "model": self.model}
        finally:
            shutil.rmtree(d, ignore_errors=True)


class ReplayModel:
    """Judge-friendly mode: replays recorded model outputs keyed by prompt hash. Costs nothing."""
    name = "replay"

    def __init__(self, path):
        self.rec = {}
        for line in open(path):
            r = json.loads(line)
            self.rec[r["prompt_sha256"]] = r

    def complete(self, prompt):
        h = hashlib.sha256(prompt.encode()).hexdigest()
        if h not in self.rec:
            raise ModelError("no recorded output for this prompt (replay mode)")
        r = self.rec[h]
        return {"text": r["text"], "tokens": r.get("tokens", 0), "tool_calls_attempted": 0, "model": r.get("model", "replay")}


class RecordingModel:
    """Wraps a model and appends each call to a JSONL file for later replay."""
    name = "recording"

    def __init__(self, inner, path):
        self.inner, self.path = inner, path

    def complete(self, prompt):
        r = self.inner.complete(prompt)
        with open(self.path, "a") as f:
            f.write(json.dumps({"prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                                "text": r["text"], "tokens": r["tokens"], "model": r["model"]}) + "\n")
        return r


class StubModel:
    """For tests: a function prompt -> text."""
    name = "stub"

    def __init__(self, fn):
        self.fn = fn

    def complete(self, prompt):
        return {"text": self.fn(prompt), "tokens": 0, "tool_calls_attempted": 0, "model": "stub"}


class OfflineModel:
    """No model at all. Every call fails like an exhausted quota. Used to measure what the deterministic
    layer alone (reproduction, flaky detection, tripwire, policy) decides, with zero LLM involvement."""
    name = "offline"

    def complete(self, prompt):
        raise ModelError("offline baseline: no model configured")
