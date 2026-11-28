#!/bin/bash
# LIVE unattended run against the real failed GitHub Actions run 46054303024, after the free-tier daily reset.
# Real model (gemini-4-hydrogen, free tier), real GitHub API, real bwrap sandbox. Dry-run: nothing is posted.
# Secrets come from vault-written files and are never printed.
cd "$(dirname "$0")/.."
export PYTHONPATH=. CIWARDEN_MAX_RPM=4 CIWARDEN_MAX_RPD=18
export CIWARDEN_API_BASE=https://generativelanguage.googleapis.com/v1beta/openai/
export CIWARDEN_API_KEY="$(cat "$GEMINI_KEY_FILE")"
export GITHUB_TOKEN="$(cat "$GITHUB_TOKEN_FILE")"
say() { printf '\n\033[1m== %s\033[0m\n' "$1"; sleep 1.2; }
say "LIVE RUN: ciwarden watch vanshwadhwa24/ciwarden --once --dry-run --model compat:gemini-4-hydrogen"
echo "target: real failed GitHub Actions run 46054303024 (demo/paginate-bug, off-by-one in page())"
echo "dry-run: reads the real run, verifies a fix in the sandbox, saves the planned PR to planned.json, posts nothing"
rm -rf watch-out
( python3 -m ciwarden.cli watch vanshwadhwa24/ciwarden --once --dry-run --model compat:gemini-4-hydrogen > /tmp/live-watch-result.json 2>/tmp/live-watch-err.txt; echo "ciwarden exited rc=$?" ) &
WP=$!
T=""
for i in $(seq 1 600); do
  T=$(ls watch-out/*/trace.jsonl 2>/dev/null | head -1)
  [ -n "$T" ] && break
  sleep 0.5
done
if [ -n "$T" ]; then python3 -m ciwarden.monitor "$T" --follow & MP=$!; fi
wait $WP
sleep 1.5; kill $MP 2>/dev/null; wait 2>/dev/null
say "RESULT (real output of the run)"
python3 -c 'import json; print(json.dumps(json.load(open("/tmp/live-watch-result.json")), indent=2)[:1200])' 2>/dev/null || tail -5 /tmp/live-watch-err.txt
say "PLANNED WRITE (saved by dry-run, never posted)"
python3 - <<'PY'
import glob, json
p = glob.glob("watch-out/*/planned.json")
if p:
    d = json.load(open(p[0]))
    print(json.dumps(d, indent=2)[:900])
else:
    print("no planned write (agent escalated or opened an issue instead)")
PY
