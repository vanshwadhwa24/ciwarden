# fix: price() in src/mod.py treats pct as a decimal multiplier ins

branch: ciwarden/fix-bug-discount

Root cause: price() in src/mod.py treats pct as a decimal multiplier instead of a percentage (missing division by 100)

Explanation: Divide pct by 100 so percentage discounts are calculated properly.

Proof: `python3 -m unittest discover -s tests -v` failed 3/3 before the change and passed 2/2 after, in fresh copies. Changed lines: 2. Files: src/mod.py.
