# demo/paginate-bug

A deliberately broken mini project for the ciwarden demo (branch `demo/paginate-bug` only; `main` is the real project).
`page()` in `src/mod.py` has an off-by-one bug, so CI fails on purpose. ciwarden reads that failed run.
