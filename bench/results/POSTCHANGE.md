# Post-change notes (do not merge into the attempt-1 numbers)

Attempt 1 (real model gemini-4-hydrogen, free tier): bench/results/gemini-dev and gemini-held. Unchanged.
In attempt 1, amb-timeout-slow (expected ESCALATE) produced a local PR.md for a patch that deletes
`time.sleep(10)`. It was only a local artifact in the bench sandbox repo; no GitHub write happened (no token existed).

Change after seeing that: agent.py now escalates, before any model call, when a reproduction run times out or
the CI log shows a timeout/cancelled step (TIMEOUT_SIGNS). Rationale: "too slow" is not "wrong"; a human decides.

postchange-amb-timeout-slow: that one case re-run with a model stub that fails if called. It escalates without a model.
This is NOT a new real-model result and is not counted in the attempt-1 score. It also tunes to a case we saw:
treat it as a fix for a seen failure, not as held-out evidence.
postchange-offline: the no-model baseline over all 26 cases after the change, to check for regressions.
