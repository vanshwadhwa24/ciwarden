"""watch: poll a repo's failed workflow runs, build a case from each new one, respond via GitHubActuator.
.ciwarden.json is untrusted too: it may only pick a runner NAME from a fixed allowlist (unittest, pytest), never a command line. Cloned repo code is treated as hostile: it only ever runs through runner.py
(scrubbed env, no network when the kernel allows it, fresh copy, timeout)."""
import json, os, subprocess, tempfile, shutil, time
from . import agent, policy, trace as tr, github, runner

RUNNERS = {"unittest": "python3 -m unittest discover -s tests", "pytest": "python3 -m pytest -q"}


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
    command = RUNNERS.get(cfg.get("runner"))  # the repo file picks a NAME; it never supplies a command line
    if command is None:
        return None
    return {"id": f"run-{run['id']}", "repo": repo_dir, "command": command, "timeout": min(int(cfg.get("timeout", 60)), 120),
            "commit_message": (run.get("head_commit") or {}).get("message", ""), "log": log}


def watch_once(client, model, kill, out_root, seen, clone=clone_repo, token=None, budget=None, dry_run=False):
    if not runner.SANDBOX_AVAILABLE or runner.FIXTURE_MODE:
        raise runner.IsolationUnavailable("watch runs untrusted repo code and requires the bwrap sandbox; unisolated fixture mode is refused")
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
            act = github.DryRunActuator(kill) if dry_run else github.GitHubActuator(client, kill, base=run.get("head_branch"))
            if case is None:
                done.append({"run": run["id"], "outcome": "SKIPPED no .ciwarden.json"})
                continue
            res = agent.respond(case, model, act, trace, kill, budget or policy.Budget())
            if dry_run:
                res["planned"] = act.planned
                json.dump(act.planned, open(os.path.join(out, "planned.json"), "w"), indent=2)
            done.append({"run": run["id"], "branch": run.get("head_branch"), **res})
        finally:
            shutil.rmtree(work, ignore_errors=True)
    return done


def watch_loop(client, model, kill, out_root, interval=60, clone=clone_repo, token=None):
    seen = set()
    while True:
        kill.check()
        print(json.dumps(watch_once(client, model, kill, out_root, seen, clone, token)), flush=True)
        time.sleep(interval)
