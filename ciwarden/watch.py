"""watch: poll a repo's failed workflow runs, build a case from each new one, respond via GitHubActuator.
The CI command comes from the repo owner's `.ciwarden.json` on the default branch ({"command": "...", "timeout": 60}),
never from log text. Cloned repo code is treated as hostile: it only ever runs through runner.py
(scrubbed env, no network when the kernel allows it, fresh copy, timeout)."""
import json, os, subprocess, tempfile, shutil, time
from . import agent, policy, trace as tr, github


def clone_repo(repo, sha, token, dest):
    url = f"https://github.com/{repo}.git"
    env = {"PATH": os.environ["PATH"], "GIT_TERMINAL_PROMPT": "0"}
    if token:  # token is given to git through a header, never in the URL or the model env
        env["GIT_CONFIG_COUNT"] = "1"; env["GIT_CONFIG_KEY_0"] = "http.extraHeader"
        import base64
        env["GIT_CONFIG_VALUE_0"] = "Authorization: Basic " + base64.b64encode(f"x-access-token:{token}".encode()).decode()
    subprocess.run(["git", "clone", "-q", url, dest], check=True, env=env, timeout=90)
    subprocess.run(["git", "checkout", "-q", sha], cwd=dest, check=True, env=env, timeout=30)


def build_case(run, log, repo_dir):
    cfgp = os.path.join(repo_dir, ".ciwarden.json")
    if not os.path.isfile(cfgp) or os.path.islink(cfgp):
        return None
    cfg = json.load(open(cfgp))
    return {"id": f"run-{run['id']}", "repo": repo_dir, "command": cfg["command"], "timeout": cfg.get("timeout", 60),
            "commit_message": (run.get("head_commit") or {}).get("message", ""), "log": log}


def watch_once(client, model, kill, out_root, seen, clone=clone_repo, token=None, budget=None):
    done = []
    for run in client.failed_runs():
        if run["id"] in seen:
            continue
        seen.add(run["id"])
        work = tempfile.mkdtemp(prefix="ciw-watch-")
        try:
            repo_dir = os.path.join(work, "repo")
            clone(client.repo, run["head_sha"], token, repo_dir)
            case = build_case(run, client.run_log_text(run["id"]), repo_dir)
            out = os.path.join(out_root, case["id"] if case else f"run-{run['id']}")
            os.makedirs(out, exist_ok=True)
            trace = tr.Trace(os.path.join(out, "trace.jsonl"))
            act = github.GitHubActuator(client, kill)
            if case is None:
                done.append({"run": run["id"], "outcome": "SKIPPED no .ciwarden.json"})
                continue
            done.append({"run": run["id"], **agent.respond(case, model, act, trace, kill, budget or policy.Budget())})
        finally:
            shutil.rmtree(work, ignore_errors=True)
    return done


def watch_loop(client, model, kill, out_root, interval=60, clone=clone_repo, token=None):
    seen = set()
    while True:
        kill.check()
        print(json.dumps(watch_once(client, model, kill, out_root, seen, clone, token)), flush=True)
        time.sleep(interval)
