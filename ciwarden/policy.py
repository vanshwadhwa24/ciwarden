"""Capability limits enforced in code. The model never executes anything; it only proposes."""
import fnmatch, os, time

FORBIDDEN_PATTERNS = [
    ".github/*", ".git/*", "*.env", ".env*", "*secret*", "*credential*", "*.pem", "*.key",
    "tests/*", "test/*", "*_test.py", "test_*.py", "*conftest.py",
    "*lock*", "package-lock.json", "poetry.lock", "uv.lock", "Pipfile.lock",
    "Makefile", "*.sh", "setup.cfg", "tox.ini", "pytest.ini", "pyproject.toml",
]
ALLOWED_SUFFIXES = (".py", ".js", ".ts", ".go", ".rs", ".java", ".txt", ".md", ".json", ".toml", ".cfg")
MAX_FILES = 3
MAX_CHANGED_LINES = 60
MAX_FILE_BYTES = 40_000


class PolicyError(Exception):
    pass


class KillSwitch:
    """Checked before every tool call and every model call. Trips on file or env var."""

    def __init__(self, path=None):
        self.path = path or os.environ.get("CIWARDEN_KILL_FILE", "KILL")

    def check(self):
        if os.environ.get("CIWARDEN_KILL") == "1" or os.path.exists(self.path):
            raise PolicyError("kill switch engaged")


class Budget:
    def __init__(self, max_steps=40, max_seconds=600, max_model_calls=6, max_tokens=400_000):
        self.max_steps, self.max_seconds = max_steps, max_seconds
        self.max_model_calls, self.max_tokens = max_model_calls, max_tokens
        self.steps = 0
        self.model_calls = 0
        self.tokens = 0
        self.t0 = time.time()

    def step(self):
        self.steps += 1
        if self.steps > self.max_steps:
            raise PolicyError("step budget exhausted")
        if time.time() - self.t0 > self.max_seconds:
            raise PolicyError("time budget exhausted")

    def model_call(self):
        self.model_calls += 1
        if self.model_calls > self.max_model_calls:
            raise PolicyError("model call budget exhausted")
        if self.tokens > self.max_tokens:
            raise PolicyError("token budget exhausted")

    def add_tokens(self, n):
        self.tokens += n


def _norm(p):
    p = os.path.normpath(p).replace("\\", "/")
    return p


def _canonical(raw):
    """Reject anything that is not a plain, ASCII, relative, forward-slash path. This runs before any
    pattern check so encodings and look-alikes cannot reach the allowlist."""
    if not isinstance(raw, str) or not raw:
        raise PolicyError("bad path")
    if not raw.isascii() or any(ord(c) < 32 or c in "\\%:*?\"<>|~$`;" for c in raw):
        raise PolicyError(f"path has disallowed characters: {raw!r}")
    if raw != raw.strip() or raw.endswith(".") or " " in raw:
        raise PolicyError(f"path has spaces or trailing dots: {raw!r}")
    parts = raw.split("/")
    if any(seg in ("", ".", "..") for seg in parts) or raw.startswith("/"):
        raise PolicyError(f"path has empty or dot segments: {raw!r}")
    if any(seg.startswith(".") for seg in parts):
        raise PolicyError(f"hidden path segment not allowed: {raw!r}")
    return raw


def check_patch_paths(files):
    """files: list of {path, content}. Raises PolicyError on anything outside the allowlist."""
    if not files:
        raise PolicyError("empty patch")
    if len(files) > MAX_FILES:
        raise PolicyError("too many files in patch")
    for f in files:
        p = _canonical(f.get("path", ""))
        if p.startswith("/") or p.startswith("..") or "/../" in p or p == ".":
            raise PolicyError(f"path escapes repo: {p}")
        low = p.lower()
        for pat in FORBIDDEN_PATTERNS:
            if fnmatch.fnmatch(low, pat.lower()) or fnmatch.fnmatch(os.path.basename(low), pat.lower()):
                raise PolicyError(f"path not allowed by policy: {p}")
        if not low.endswith(ALLOWED_SUFFIXES):
            raise PolicyError(f"file type not allowed: {p}")
        if len(f.get("content", "").encode()) > MAX_FILE_BYTES:
            raise PolicyError(f"file too large: {p}")


def check_diff_size(changed_lines):
    if changed_lines > MAX_CHANGED_LINES:
        raise PolicyError(f"patch too large ({changed_lines} changed lines)")


ALLOWED_BRANCH_PREFIX = "ciwarden/"


def check_branch(name, protected=("main", "master", "develop", "release")):
    if name in protected or not name.startswith(ALLOWED_BRANCH_PREFIX):
        raise PolicyError(f"branch not allowed: {name}")
