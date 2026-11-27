# ciwarden

An unattended agent that reads a failed CI run and decides what to do: propose a small verified fix, label it flaky, call it an outage or environment problem, or escalate to a human. The point is not the fix. The point is that it knows when not to fix.

STATUS: work in progress. Benchmark results are not published yet (see "Results"). Nothing below claims a result that has not been measured.

## How it decides
1. Tripwire: instruction-like text in the log, commit message or repo files means ESCALATE before any model call (heuristic only).
2. Reproduce: run the CI command 3 times in fresh copies. Mixed results = flaky (no patch). 3/3 pass = not reproduced. 3/3 fail = go on.
3. The model sees the log as quoted data and returns one JSON action. It has no tools.
4. A patch must pass path/size policy, then fail-before / pass-after in fresh copies. Only then is a branch `ciwarden/*` plus a PR proposed. Never the default branch, tests, or workflows.
5. Every step is written to a hash-chained trace. A kill switch (`KILL` file or `CIWARDEN_KILL=1`) stops everything.

Isolation: CI commands run with a scrubbed environment, a timeout, in a throwaway copy, and in an empty network namespace where the kernel allows it (`runner.NETWORK_ISOLATED`). Symlinks in patch paths are refused. See SAFETY.md for what is enforced and what is not.

## Run
    python3 -m unittest discover -s tests          # 24 tests, no network, no model
    python3 -m ciwarden.cli respond bench/cases/<case> --out out/ --replay <recorded.jsonl>
    GITHUB_TOKEN=... python3 -m ciwarden.cli watch owner/repo --once

Local mode writes branches and PR/issue text as files ("local-only": these are not GitHub PRs). `watch` uses the real GitHub API; it has been tested only against a local fake API server so far.

## Benchmark
26 generated cases (9 dev, 17 held): code bugs, environment, flaky (simulated with a counter file), outages, ambiguous, and injection (2 subtle). `bench/generate.py`, `bench/run_bench.py`.

## Results
Not yet measured end to end. Partial dev run: 7 of 9 cases ran; the 4 that needed no model call (flaky, outage, injection) were correct, and the 3 that needed the model hit the free hosted quota. One full model case (a pagination bug) produced a verified local-only PR branch. Replay mode reproduces recorded model outputs and is not a model benchmark.

## Limits
See SAFETY.md. The model is a free hosted OpenCode model whose quota can run out; flakiness in the benchmark is simulated.
