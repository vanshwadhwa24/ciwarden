# ciwarden

An unattended agent that reads a failed CI run and decides what to do: propose a small verified fix, label it flaky, call it an outage or environment problem, or escalate to a human. The point is not the fix. The point is that it knows when not to fix.

STATUS: work in progress. Benchmark results are not published yet (see "Results"). Nothing below claims a result that has not been measured.

## How it decides
1. Tripwire: instruction-like text in the log, commit message or repo files means ESCALATE before any model call (heuristic only).
2. Reproduce: run the CI command 3 times in fresh copies. Mixed results = flaky (no patch). 3/3 pass = not reproduced. 3/3 fail = go on.
3. The model sees the log as quoted data and returns one JSON action. It has no tools.
4. A patch must pass path/size policy, then fail-before / pass-after in fresh copies. Only then is a branch `ciwarden/*` plus a PR proposed. Never the default branch, tests, or workflows.
5. Every step is written to a hash-chained trace. A kill switch (`KILL` file or `CIWARDEN_KILL=1`) stops everything.

Isolation: untrusted repo code runs only inside a bubblewrap sandbox (new user/pid/net/ipc/uts/mount namespaces; read-only /usr; no home, gitconfig, tokens or env; no network; writes only to a throwaway copy and a tmpfs; CPU/file-size/process limits; copies exclude .git). If bubblewrap is unusable the agent REFUSES to run (fail closed). A separate, explicit `CIWARDEN_UNISOLATED_FIXTURE_MODE=1` exists for our own synthetic fixtures only, and `watch` refuses it. `.ciwarden.json` in a repo can only choose a runner name from a fixed list. Symlinks in patch paths are refused. `python3 -c 'from ciwarden import runner; print(runner.capability())'` prints what is active. See SAFETY.md.

## Run
    python3 -m unittest discover -s tests          # 28 tests, no network, no model
    python3 -m ciwarden.cli respond bench/cases/<case> --out out/ --replay <recorded.jsonl>
    GITHUB_TOKEN=... python3 -m ciwarden.cli watch owner/repo --once

`watch --dry-run` reads real failed runs and logs and writes NOTHING; it saves what it would post to `planned.json`. The branch `demo/paginate-bug` holds a deliberately failing mini project with a CI workflow; `main` is the real project.

Local mode writes branches and PR/issue text as files ("local-only": these are not GitHub PRs). `watch` uses the real GitHub API; it was tested against a local fake API server, and `watch --once --dry-run` was run against a real failed GitHub Actions run (read-only: fetched the run and log, reproduced locally in the sandbox, planned the action). No PR or issue has been posted to GitHub.

## Benchmark
26 generated cases (9 dev, 17 held): code bugs, environment, flaky (simulated with a counter file), outages, ambiguous, and injection (2 subtle). `bench/generate.py`, `bench/run_bench.py`.

## Results
Not yet measured end to end. Partial dev run: 7 of 9 cases ran; the 4 that needed no model call (flaky, outage, injection) were correct, and the 3 that needed the model hit the free hosted quota. One full model case (a pagination bug) produced a verified local-only PR branch. Replay mode reproduces recorded model outputs and is not a model benchmark.

### Offline floor (no model at all)
`python3 bench/run_bench.py --offline` makes every model call fail, so only the deterministic layer (sandbox reproduction, flaky detection, injection scan, policy) decides. Measured on all 26 cases: 16/26 correct action, 0 PRs opened, 0 unsafe executed actions. Flaky 4/4, outage 3/3, ambiguous 3/3, injection 6/6; code bugs 0/6 and environment 0/4 (these need a model). Caveat: 2 of the 6 injection cases (the subtle ones) escalate only because the model call failed, so they are not evidence of model robustness. This is a baseline for comparison, not a model result.

### Stub proof (not a model result)
A scripted stand-in model, not an LLM, was used once to show the repair pipeline on a real failed run: reproduce 3/3 fail, apply a 2-line patch, verify 2/2 pass, plan a PR (dry-run, never posted).

## Limits
See SAFETY.md. The model is a free hosted OpenCode model whose quota can run out; flakiness in the benchmark is simulated.
