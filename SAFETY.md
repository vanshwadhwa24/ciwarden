# SAFETY.md: what is enforced in code (and what is not)

Each line names the file and the test that checks it.

Enforced:
- The model has no tools. It gets text and returns text. It runs in an empty temp dir with bash/edit/webfetch permission denied and without secret-like env vars (`ciwarden/llm.py`). Code executes only a schema-checked action.
- A patch may touch at most 3 files, 60 changed lines, only allowed source file types, never tests, CI config (`.github/`), lockfiles, scripts, env or secret-like files, and never a path outside the repo (`policy.py`; `tests/test_policy.py`, `tests/test_agent.py`).
- Writes go only to branches named `ciwarden/*`, never the default branch (`policy.check_branch`, `tests/test_github.py`).
- A fix becomes a PR only if the CI command fails 3 of 3 before and passes 2 of 2 after, in fresh copies, and the change is small (`agent.py`; `test_wrong_fix_not_verified`).
- Flaky or non-reproducible failures are never patched. Evidence from running the code beats the model's opinion (`test_flaky_never_patched`).
- Kill switch: a `KILL` file or `CIWARDEN_KILL=1` stops the agent before every tool and model call, before every GitHub write, and cancels a command that is already running (the process group is killed within about 0.2s) (`test_kill_switch_stops_everything`, `test_kill_switch_blocks_writes`, `tests/test_killmid.py`). Shown in demo/run_demo.sh.
- Step, time, model-call and token budgets (`policy.Budget`).
- Every step is appended to a hash-chained JSONL trace; tampering is detected (`trace.py`, `test_chain_verifies_and_detects_tamper`).
- Live view: `python3 -m ciwarden.monitor TRACE --follow` prints each step as it is written (what it saw, what it decided, tool results). Budgets show in the trace outcome.
- The GitHub token is read from `GITHUB_TOKEN` and is never passed to the model process.

Not enforced / known limits:
- Containment is bubblewrap namespaces plus rlimits, not a VM. A kernel or bwrap escape is out of scope; the process-count limit is per user, not per sandbox. Tested escapes (tests/test_agent.py TestIsolation): reading a canary file in the real home, ~/.gitconfig, token env vars, writing outside the copy or into /usr, network connect, seeing host processes, /memory. Not tested: kernel exploits, resource exhaustion beyond rlimits, timing side channels.
- Containment fails closed: no bwrap means no untrusted execution (test_fail_closed_without_sandbox; watch refuses, test_watch_refuses_without_sandbox).
- A repo's .ciwarden.json only picks a runner name from a fixed list (test_command_in_repo_file_is_not_executed).
- The GitHub contents API writes only regular files with default mode; symlink patch paths are refused locally. Tested against a local fake API, and once for real: PR #1 (https://github.com/vanshwadhwa24/ciwarden/pull/1) was opened on this repo's demo branch with a human-approved title and body. That PR's fix came from a scripted stand-in model, not an LLM.
- A test-passing but malicious change to allowed source files is not detected.
- The instruction-like-text tripwire (`sanitize.py`) is a keyword heuristic. It misses paraphrased injections. The real limits are the policy checks and test verification above; a malicious but test-passing patch to allowed source files is not detected.
- The model could still choose a wrong class (for example call an environment problem a code bug). Verification limits the damage but does not remove it.
- Flakiness in the benchmark is simulated with a counter file.
- Results depend on the free hosted model quota. See README.
- Trap Pack (tests/trap-pack/RESULTS.md): run without any model. The scanner flagged 6 of 20 files and false-flags the benign control. Only 1 of 3 in-domain files was stopped by detection; the other two escalated because no model was available. 17 files are outside ciwarden's input type and are untested. No real-model Trap Pack run has been done.
- Human approval: public PRs and issues are posted by a human-approved step, not autonomously, in this project's own use.
