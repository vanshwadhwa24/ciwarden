# Demo plan (3 minutes max, unattended)
Precondition: a model route works (otherwise no demo of model-needing cases; do not fake). Sandbox repo `ciwarden` with a deliberately failing workflow; token limited to that repo. Nothing is posted to any other repo.
0:00 One sentence: what it does and that nobody touches the keyboard.
0:15 Start `watch --once` on the repo with three failed runs queued: (a) real bug, (b) flaky, (c) a failure whose log contains instruction-like text.
0:45 Show terminal: reproduction 3x, model call, sandboxed verify, PR on a ciwarden/* branch (real GitHub page), issue for flaky, escalation for the injection with 0 model calls.
2:00 Show trace chain verify, SAFETY.md enforced-vs-not list, escape test output.
2:30 Show benchmark table with the honest label of what was measured. Stop.
If the quota is out at recording time, the video shows only the code-only paths and says so.
