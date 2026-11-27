#!/bin/bash
# Records the real terminal session used for the demo video. Every line printed is real program output.
# Model: none (offline). Nothing here is an LLM result. Usage: bash demo/run_demo.sh
cd "$(dirname "$0")/.."
export PYTHONPATH=.
OUT=$(mktemp -d); rm -f KILL
say() { printf '\n\033[1m== %s\033[0m\n' "$1"; sleep 1.2; }
say "1. TRIGGER: CI failed. The log contains a prompt injection (Agentware Trap Pack file 17)."
mkdir -p $OUT/c1 && cp -r bench/cases/bug-paginate/. $OUT/c1/
printf '\n' >> $OUT/c1/log.txt; cat tests/trap-pack/inputs/traps/developer-workflow/17-ci-build-log.txt >> $OUT/c1/log.txt
git -C $OUT init -q 2>/dev/null
( python3 -m ciwarden.cli respond $OUT/c1 --out $OUT/o1 --model offline > $OUT/r1.json ) &
sleep 0.2; python3 -m ciwarden.monitor $OUT/o1/trace.jsonl --follow & MP=$!
wait %1; sleep 1.5; kill $MP 2>/dev/null; wait 2>/dev/null
python3 - <<PY
import json;r=json.load(open("$OUT/r1.json"));print("DECISION:",r["action"],"|",r["reason"]);print("branches created:",[b for b in r.get("branches",[]) if b.strip()!="master"] or "none")
PY
grep -c "AGW-CANARY" -r $OUT/o1 --include='*.md' --include='*.json' 2>/dev/null | head -1 | sed 's/^/canary in anything written (0 = not leaked): /'
sleep 2
say "2. KILL SWITCH: a slow run is started, the kill file is created mid-run."
mkdir -p $OUT/c2 && cp -r bench/cases/amb-timeout-slow/. $OUT/c2/
( python3 -m ciwarden.cli respond $OUT/c2 --out $OUT/o2 --model offline > $OUT/r2.json 2>$OUT/e2.txt ) &
sleep 0.2; python3 -m ciwarden.monitor $OUT/o2/trace.jsonl --follow & MP=$!
sleep 2.5; echo ">>> touch KILL  (operator pulls the kill switch)"; touch KILL
wait %1; sleep 1; kill $MP 2>/dev/null; wait 2>/dev/null; rm -f KILL
python3 - <<PY
import json;r=json.load(open("$OUT/r2.json")) if open("$OUT/r2.json").read().strip() else {}
print("RESULT:",r.get("action"),"|",r.get("reason")) if r else print("RESULT: stopped, see stderr:", open("$OUT/e2.txt").read().strip().splitlines()[-1:] )
PY
sleep 2
say "3. AUDIT: hash-chained trace, then one byte is tampered."
cp $OUT/o1/trace.jsonl $OUT/t.jsonl
python3 -c "from ciwarden import trace; print('original:', trace.verify('$OUT/t.jsonl'))"
sed -i '0,/"tail"/s/"tail"/"taiI"/;0,/"findings"/s/"findings"/"findingz"/' $OUT/t.jsonl
python3 -c "from ciwarden import trace; print('after tamper:', trace.verify('$OUT/t.jsonl'))"
sleep 2
say "Honest limits: no model ran in this video. Real-model repair is NOT demonstrated here."
sleep 3
