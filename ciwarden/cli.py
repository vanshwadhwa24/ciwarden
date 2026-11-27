"""Command line: respond to one failure case directory.
  python3 -m ciwarden.cli respond bench/cases/bug-slug --out out/ [--replay file | --record file] [--model M]
"""
import argparse, json, os, shutil, sys, tempfile
from . import agent, policy, trace as tr, actions, llm


def load_case(case_dir, work):
    cfg = json.load(open(os.path.join(case_dir, "ci.json")))
    repo = os.path.join(work, "repo")
    shutil.copytree(os.path.join(case_dir, "repo"), repo)
    return {"id": cfg["id"], "repo": repo, "command": cfg["command"], "timeout": cfg.get("timeout", 60),
            "commit_message": cfg.get("commit_message", ""), "log": open(os.path.join(case_dir, "log.txt")).read()}


def respond_dir(case_dir, out_dir, model, kill=None, budget=None):
    work = tempfile.mkdtemp(prefix="ciw-case-")
    try:
        case = load_case(case_dir, work)
        os.makedirs(out_dir, exist_ok=True)
        trace = tr.Trace(os.path.join(out_dir, "trace.jsonl"))
        kill = kill or policy.KillSwitch()
        actuator = actions.LocalActuator(case["repo"], out_dir, kill)
        res = agent.respond(case, model, actuator, trace, kill, budget or policy.Budget())
        # evidence for the benchmark: what changed, which branches exist
        res["branches"] = [b.strip(" *") for b in os.popen(f"cd {case['repo']} && git branch --list").read().splitlines()]
        res["branch_files"] = {}
        for b in res["branches"]:
            if b.startswith("ciwarden/"):
                res["branch_files"][b] = os.popen(f"cd {case['repo']} && git diff --name-only master..{b}").read().split()
        res["repo_dirty"] = bool(os.popen(f"cd {case['repo']} && git status --porcelain").read().strip())
        return res
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ciwarden")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("respond")
    r.add_argument("case_dir")
    r.add_argument("--out", required=True)
    r.add_argument("--model", default=llm.DEFAULT_MODEL)
    r.add_argument("--replay")
    r.add_argument("--record")
    a = ap.parse_args(argv)
    if a.replay:
        model = llm.ReplayModel(a.replay)
    else:
        model = llm.OpenCodeModel(a.model)
        if a.record:
            model = llm.RecordingModel(model, a.record)
    res = respond_dir(a.case_dir, a.out, model)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
