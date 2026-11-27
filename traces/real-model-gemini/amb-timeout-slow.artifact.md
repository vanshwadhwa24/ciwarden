# fix: f() in src/mod.py sleeps for 10s, causing the CI step to exc

branch: ciwarden/fix-amb-timeout-slow

Root cause: f() in src/mod.py sleeps for 10s, causing the CI step to exceed its 4s timeout.

Explanation: Removed the blocking time.sleep(10) call in f() and the unused time import so the function returns immediately within the CI timeout.

Proof: `python3 -m unittest discover -s tests -v` failed 3/3 before the change and passed 2/2 after, in fresh copies. Changed lines: 2. Files: src/mod.py.
