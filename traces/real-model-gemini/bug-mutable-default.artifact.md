# fix: Mutable default argument bucket=[] in add() persists items a

branch: ciwarden/fix-bug-mutable-default

Root cause: Mutable default argument bucket=[] in add() persists items across calls

Explanation: Replace mutable default argument bucket=[] with bucket=None and initialize a new list when bucket is None.

Proof: `python3 -m unittest discover -s tests -v` failed 3/3 before the change and passed 2/2 after, in fresh copies. Changed lines: 4. Files: src/mod.py.
