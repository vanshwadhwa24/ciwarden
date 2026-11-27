"""Runs the repo's CI command in a throwaway copy with a scrubbed environment and a timeout.
The command comes from the case's trusted ci.json, never from log text."""
import os, shlex, shutil, subprocess, tempfile

SAFE_ENV_KEYS = ("PATH", "LANG", "LC_ALL", "PYTHONPATH")


def scrubbed_env(extra=None):
    env = {k: v for k, v in os.environ.items() if k in SAFE_ENV_KEYS}
    env["HOME"] = tempfile.gettempdir()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(extra or {})
    return env


def fresh_copy(repo_dir):
    d = tempfile.mkdtemp(prefix="ciw-run-")
    dst = os.path.join(d, "repo")
    shutil.copytree(repo_dir, dst, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    return d, dst


def run_command(repo_dir, command, timeout=60, env=None):
    """Returns {rc, out, timed_out}. Runs in a fresh copy so runs never contaminate each other."""
    d, dst = fresh_copy(repo_dir)
    try:
        try:
            p = subprocess.run(shlex.split(command), cwd=dst, capture_output=True, text=True,
                               timeout=timeout, env=scrubbed_env(env))
            return {"rc": p.returncode, "out": (p.stdout + p.stderr)[-8000:], "timed_out": False}
        except subprocess.TimeoutExpired as e:
            return {"rc": 124, "out": "timed out", "timed_out": True}
        except FileNotFoundError as e:
            return {"rc": 127, "out": str(e), "timed_out": False}
    finally:
        shutil.rmtree(d, ignore_errors=True)


def run_with_patch(repo_dir, command, files, timeout=60):
    """Apply files (list of {path, content}) in a fresh copy, run command, return result + changed line count."""
    d, dst = fresh_copy(repo_dir)
    try:
        changed = 0
        for f in files:
            target = os.path.normpath(os.path.join(dst, f["path"]))
            if not target.startswith(os.path.normpath(dst) + os.sep):
                return {"rc": 99, "out": "path escape", "changed_lines": 0}
            old = open(target).read().splitlines() if os.path.exists(target) else []
            new = f["content"].splitlines()
            import difflib
            changed += sum(1 for l in difflib.ndiff(old, new) if l[:2] in ("+ ", "- "))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w") as fh:
                fh.write(f["content"] if f["content"].endswith("\n") else f["content"] + "\n")
        try:
            p = subprocess.run(shlex.split(command), cwd=dst, capture_output=True, text=True,
                               timeout=timeout, env=scrubbed_env())
            return {"rc": p.returncode, "out": (p.stdout + p.stderr)[-4000:], "changed_lines": changed}
        except subprocess.TimeoutExpired:
            return {"rc": 124, "out": "timed out", "changed_lines": changed}
    finally:
        shutil.rmtree(d, ignore_errors=True)
