"""GitHub integration (REST, stdlib). Token comes from the GITHUB_TOKEN env var only, is never logged,
and never reaches the model subprocess. All writes go through the same policy checks as the local actuator."""
import base64, io, json, os, re, urllib.parse, urllib.request, urllib.error, zipfile
from . import policy

API = os.environ.get("CIWARDEN_GITHUB_API", "https://api.github.com")
AUTHOR = {"name": "Vansh Wadhwa", "email": "vanshreads@gmail.com"}


class GitHubError(Exception):
    pass


class Client:
    def __init__(self, repo, token=None, api=API):
        self.repo, self.api = repo, api.rstrip("/")
        self.token = token or os.environ.get("GITHUB_TOKEN", "")

    def _req(self, method, path, body=None, raw=False):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.api + path, data=data, method=method)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("User-Agent", "ciwarden")
        if self.token:
            req.add_header("Authorization", "Bearer " + self.token)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                b = r.read()
                return b if raw else (json.loads(b) if b else {})
        except urllib.error.HTTPError as e:
            raise GitHubError(f"{method} {path} -> {e.code}: {e.read()[:200].decode(errors='replace')}")

    # ---- reads
    def failed_runs(self, limit=10):
        d = self._req("GET", f"/repos/{self.repo}/actions/runs?status=failure&per_page={limit}")
        return d.get("workflow_runs", [])

    def run_log_text(self, run_id, max_chars=60000):
        z = zipfile.ZipFile(io.BytesIO(self._req("GET", f"/repos/{self.repo}/actions/runs/{run_id}/logs", raw=True)))
        out = ""
        for n in sorted(z.namelist()):
            out += f"\n### {n}\n" + z.read(n).decode(errors="replace")
        return out[-max_chars:]

    def commit_message(self, sha):
        return self._req("GET", f"/repos/{self.repo}/commits/{sha}")["commit"]["message"]

    def default_branch_sha(self):
        r = self._req("GET", f"/repos/{self.repo}")
        b = r["default_branch"]
        return b, self._req("GET", f"/repos/{self.repo}/git/ref/heads/{b}")["object"]["sha"]

    # ---- writes (policy checked by the actuator before these are called)
    def create_branch(self, name, sha):
        return self._req("POST", f"/repos/{self.repo}/git/refs", {"ref": "refs/heads/" + name, "sha": sha})

    def put_file(self, branch, path, content, message):
        existing = None
        try:
            existing = self._req("GET", f"/repos/{self.repo}/contents/{urllib.parse.quote(path)}?ref={urllib.parse.quote(branch, safe='/')}")["sha"]
        except GitHubError:
            pass
        body = {"message": message, "content": base64.b64encode(content.encode()).decode(), "branch": branch,
                "author": AUTHOR, "committer": AUTHOR}
        if existing:
            body["sha"] = existing
        return self._req("PUT", f"/repos/{self.repo}/contents/{urllib.parse.quote(path)}", body)

    def open_pr(self, head, base, title, body):
        return self._req("POST", f"/repos/{self.repo}/pulls", {"title": title, "head": head, "base": base, "body": body})

    def open_issue(self, title, body, labels):
        return self._req("POST", f"/repos/{self.repo}/issues", {"title": title, "body": body, "labels": list(labels)})


class GitHubActuator:
    """Same interface as LocalActuator. Never writes to the default branch, workflows, or tests."""

    def __init__(self, client, kill):
        self.c, self.kill = client, kill

    def open_pr(self, branch, files, title, body):
        self.kill.check()
        policy.check_branch(branch)
        policy.check_patch_paths(files)
        base, sha = self.c.default_branch_sha()
        self.kill.check()
        self.c.create_branch(branch, sha)
        for f in files:
            self.kill.check()
            self.c.put_file(branch, f["path"], f["content"], title)
        pr = self.c.open_pr(branch, base, title, body)
        return {"kind": "pr", "branch": branch, "artifact": pr.get("html_url")}

    def open_issue(self, title, body, labels=()):
        self.kill.check()
        i = self.c.open_issue(title, body, labels)
        return {"kind": "issue", "artifact": i.get("html_url")}

    def escalate(self, reason, body):
        self.kill.check()
        i = self.c.open_issue("[ciwarden] needs a human: " + reason[:80], f"{reason}\n\n{body}", ["needs-human"])
        return {"kind": "escalation", "artifact": i.get("html_url")}
