"""Runs the repo's CI command in a throwaway copy with a scrubbed environment and a timeout.
The command comes from the case's trusted ci.json, never from log text."""
import os, shlex, shutil, subprocess, tempfile

SAFE_ENV_KEYS = ("PATH", "LANG", "LC_ALL", "PYTHONPATH")


class IsolationUnavailable(RuntimeError):
    """Raised when sandboxed execution is required but bubblewrap cannot run. Fail closed."""


FIXTURE_MODE = os.environ.get("CIWARDEN_UNISOLATED_FIXTURE_MODE") == "1"
# FIXTURE_MODE runs commands WITHOUT filesystem/process containment. It exists only for the synthetic
# benchmark fixtures that we generated ourselves. It is never the default and watch refuses it.
_STATE = {}


def _bwrap_ok():
    try:
        r = subprocess.run(["bwrap", "--unshare-all", "--ro-bind", "/usr", "/usr", "--symlink", "usr/bin", "/bin",
                            "--symlink", "usr/lib", "/lib"] + (["--symlink", "usr/lib64", "/lib64"] if os.path.isdir("/usr/lib64") else []) + ["--proc", "/proc", "--dev", "/dev", "/usr/bin/python3", "-c", "pass"],
                           capture_output=True, timeout=10)
        return r.returncode == 0
    except Exception:
        return False


SANDBOX_AVAILABLE = _bwrap_ok()


def capability():
    """Honest label of what execution containment is active right now."""
    if SANDBOX_AVAILABLE:
        return "bwrap: new user/pid/net/ipc/uts/mount namespaces, read-only /usr only, no home, no env, no network, tmpfs-only writes"
    return "UNISOLATED_FIXTURE_MODE (synthetic fixtures only)" if FIXTURE_MODE else "NONE: untrusted execution refused"


def _state_dir(repo_dir):
    d = _STATE.get(repo_dir)
    if d is None:
        d = _STATE[repo_dir] = tempfile.mkdtemp(prefix="ciw-state-")
    return d


def cleanup_state():
    for d in _STATE.values():
        shutil.rmtree(d, ignore_errors=True)
    _STATE.clear()


import atexit
atexit.register(cleanup_state)


def sandbox_argv(dst, state, argv, timeout):
    if not SANDBOX_AVAILABLE:
        if FIXTURE_MODE:
            return argv
        raise IsolationUnavailable("bubblewrap is not usable here; refusing to run untrusted code unisolated. "
                                   "Set CIWARDEN_UNISOLATED_FIXTURE_MODE=1 only for synthetic fixtures.")
    b = ["bwrap", "--unshare-all", "--die-with-parent", "--new-session", "--clearenv",
         "--setenv", "PATH", "/usr/bin:/bin", "--setenv", "HOME", "/tmp", "--setenv", "TMPDIR", "/tmp",
         "--setenv", "PYTHONDONTWRITEBYTECODE", "1", "--setenv", "LANG", "C.UTF-8",
         "--ro-bind", "/usr", "/usr", "--symlink", "usr/bin", "/bin", "--symlink", "usr/lib", "/lib"]
    if os.path.isdir("/usr/lib64"):
        b += ["--symlink", "usr/lib64", "/lib64"]
    b += ["--proc", "/proc", "--dev", "/dev", "--bind", state, "/tmp", "--bind", dst, "/work", "--chdir", "/work", "--"]
    limits = ["prlimit", f"--cpu={int(timeout) + 5}", "--fsize=52428800", "--nproc=256", "--core=0"]
    return b + limits + argv


def _has_symlink(root, path):
    cur = root
    for seg in path.split("/"):
        cur = os.path.join(cur, seg)
        if os.path.islink(cur):
            return True
    return False


def scrubbed_env(extra=None):
    env = {k: v for k, v in os.environ.items() if k in SAFE_ENV_KEYS}
    env["HOME"] = tempfile.gettempdir()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(extra or {})
    return env


def fresh_copy(repo_dir):
    d = tempfile.mkdtemp(prefix="ciw-run-")
    dst = os.path.join(d, "repo")
    shutil.copytree(repo_dir, dst, symlinks=True, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".git"))
    return d, dst


def run_command(repo_dir, command, timeout=60, env=None):
    """Returns {rc, out, timed_out}. Runs in a fresh copy so runs never contaminate each other."""
    d, dst = fresh_copy(repo_dir)
    try:
        try:
            p = subprocess.run(sandbox_argv(dst, _state_dir(repo_dir), shlex.split(command), timeout), cwd=(dst if FIXTURE_MODE and not SANDBOX_AVAILABLE else None),
                               capture_output=True, text=True, timeout=timeout, env=scrubbed_env(env), start_new_session=True)
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
            if _has_symlink(dst, f["path"]):
                return {"rc": 98, "out": "symlink in patch path", "changed_lines": 0}
            old = open(target).read().splitlines() if os.path.exists(target) else []
            new = f["content"].splitlines()
            import difflib
            changed += sum(1 for l in difflib.ndiff(old, new) if l[:2] in ("+ ", "- "))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w") as fh:
                fh.write(f["content"] if f["content"].endswith("\n") else f["content"] + "\n")
        try:
            p = subprocess.run(sandbox_argv(dst, _state_dir(repo_dir), shlex.split(command), timeout), cwd=(dst if FIXTURE_MODE and not SANDBOX_AVAILABLE else None),
                               capture_output=True, text=True, timeout=timeout, env=scrubbed_env(), start_new_session=True)
            return {"rc": p.returncode, "out": (p.stdout + p.stderr)[-4000:], "changed_lines": changed}
        except subprocess.TimeoutExpired:
            return {"rc": 124, "out": "timed out", "changed_lines": changed}
    finally:
        shutil.rmtree(d, ignore_errors=True)
