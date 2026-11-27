# SAFETY.md: what is enforced in code (and what is not)

Each line names the file and the test that checks it.

Enforced:
- The model has no tools. It gets text and returns text. It runs in an empty temp dir with bash/edit/webfetch permission denied and without secret-like env vars (`ciwarden/llm.py`). Code executes only a schema-checked action.
- A patch may touch at most 3 files, 60 changed lines, only allowed source file types, never tests, CI config (`.github/`), lockfiles, scripts, env or secret-like files, and never a path outside the repo (`policy.py`; `tests/test_policy.py`, `tests/test_agent.py`).
- Writes go only to branches named `ciwarden/*`, never the default branch (`policy.check_branch`, `tests/test_github.py`).
- A fix becomes a PR only if the CI command fails 3 of 3 before and passes 2 of 2 after, in fresh copies, and the change is small (`agent.py`; `test_wrong_fix_not_verified`).
- Flaky or non-reproducible failures are never patched. Evidence from running the code beats the model's opinion (`test_flaky_never_patched`).
- Kill switch: a `KILL` file or `CIWARDEN_KILL=1` stops the agent before every tool and model call, and before every GitHub write (`test_kill_switch_stops_everything`, `test_kill_switch_blocks_writes`).
- Step, time, model-call and token budgets (`policy.Budget`).
- Every step is appended to a hash-chained JSONL trace; tampering is detected (`trace.py`, `test_chain_verifies_and_detects_tamper`).
- CI commands run with a scrubbed environment (no tokens) and a timeout (`runner.py`).
- The GitHub token is read from `GITHUB_TOKEN` and is never passed to the model process.

Not enforced / known limits:
- The instruction-like-text tripwire (`sanitize.py`) is a keyword heuristic. It misses paraphrased injections. The real limits are the policy checks and test verification above; a malicious but test-passing patch to allowed source files is not detected.
- The model could still choose a wrong class (for example call an environment problem a code bug). Verification limits the damage but does not remove it.
- Flakiness in the benchmark is simulated with a counter file.
- Results depend on the free hosted model quota. See README.
