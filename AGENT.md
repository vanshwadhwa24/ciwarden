# AGENT.md
Track: Developer Workflow (failed-build diagnosis). Solo entry.

## What it is
ciwarden is a loop in plain Python (standard library only, no framework): fetch a failed CI run, reproduce it in a bubblewrap sandbox 3 times, classify, and act. Actions: open a fix PR (only if verified), file an issue (flaky, outage, environment), or escalate with a written reason.

## Modules
- ciwarden/watch.py, github.py: poll GitHub Actions, fetch run and log, clone at the failing sha, actuators (real GitHub, dry-run, local files).
- ciwarden/runner.py: sandboxed command execution, runner allowlist, cancel-on-kill.
- ciwarden/agent.py: the decision loop and budgets. policy.py: patch policy, branch policy, kill switch.
- ciwarden/sanitize.py: instruction-like-text tripwire. llm.py: model adapters. trace.py: hash-chained audit log. monitor.py: live view.

## Tools and permissions
The model has no tools. Code has: run the CI command in the sandbox, write a branch named ciwarden/*, open a PR or issue, write files in an output folder. A GitHub token (repo-scoped, short expiry) is needed only for `watch` against a real repo.

## Models used
Default: OpenCode free tier, `opencode/deepseek-v4.1-flash-free` (CIWARDEN_MODEL to change). Any OpenAI-compatible endpoint works with `CIWARDEN_MODEL=compat:<name>` plus `CIWARDEN_API_BASE` and `CIWARDEN_API_KEY` in the environment. `--model offline` runs with no model (deterministic layer only). Replay mode reuses recorded outputs. Status of real-model runs: see README "Results".

AI coding tools were used to write this project. The author can explain each module.
