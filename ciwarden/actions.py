"""Actuators: the only code that writes anything. Local actuator writes files and a git branch.
Every call passes through policy checks first. A GitHub actuator implements the same interface."""
import json, os, subprocess
from . import policy

AUTHOR = ("Vansh Wadhwa", "vanshreads@gmail.com")


class LocalActuator:
    def __init__(self, repo_dir, out_dir, kill):
        self.repo, self.out, self.kill = repo_dir, out_dir, kill
        os.makedirs(out_dir, exist_ok=True)

    def _write(self, name, text):
        self.kill.check()
        p = os.path.join(self.out, name)
        with open(p, "w") as f:
            f.write(text)
        return p

    def open_pr(self, branch, files, title, body):
        self.kill.check()
        policy.check_branch(branch)
        policy.check_patch_paths(files)
        env = {**os.environ, "GIT_AUTHOR_NAME": AUTHOR[0], "GIT_AUTHOR_EMAIL": AUTHOR[1],
               "GIT_COMMITTER_NAME": AUTHOR[0], "GIT_COMMITTER_EMAIL": AUTHOR[1]}
        def git(*a):
            return subprocess.run(["git", *a], cwd=self.repo, env=env, capture_output=True, text=True, check=True)
        git("checkout", "-q", "-b", branch)
        for f in files:
            with open(os.path.join(self.repo, f["path"]), "w") as fh:
                fh.write(f["content"] if f["content"].endswith("\n") else f["content"] + "\n")
            git("add", f["path"])
        git("commit", "-q", "-m", title)
        git("checkout", "-q", "-")
        path = self._write("PR.md", f"# {title}\n\nbranch: {branch}\n\n{body}\n")
        return {"kind": "pr", "branch": branch, "artifact": path}

    def open_issue(self, title, body, labels=()):
        path = self._write("ISSUE.md", f"# {title}\n\nlabels: {', '.join(labels)}\n\n{body}\n")
        return {"kind": "issue", "artifact": path}

    def escalate(self, reason, body):
        path = self._write("ESCALATION.md", f"# Escalation: needs a human\n\nreason: {reason}\n\n{body}\n")
        return {"kind": "escalation", "artifact": path}
