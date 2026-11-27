"""Live view of a ciwarden trace: one line per event, what it saw and decided.
Usage: python3 -m ciwarden.monitor TRACE.jsonl [--follow | --replay]  (--replay paces a recorded trace at its real gaps, capped at 2s)"""
import json, os, sys, time
from . import trace as tr

def line(rec, t0):
    d = rec["data"]; e = rec["event"]
    if e == "start": s = f"case={d.get('case')} cmd={d.get('command')}"
    elif e == "repro_run": s = f"run {d.get('i')}: rc={d.get('rc')} timed_out={d.get('timed_out')}"
    elif e == "scan": s = "untrusted-input scan: " + (", ".join(sorted({f['rule'] for f in d.get('findings', [])})) or "no findings")
    elif e == "model_classify":
        try: j = json.loads(d.get("text", "")); s = f"MODEL {d.get('model')} ({d.get('tokens')} tok, tool calls attempted: {d.get('tool_calls_attempted')}): class={j.get('class')} conf={j.get('confidence')} :: {str(j.get('root_cause'))[:70]}"
        except Exception: s = "MODEL answer: " + str(d.get("text"))[:120]
    elif e == "model_fix":
        try: j = json.loads(d.get("text", "")); s = f"MODEL proposed patch to {[f['path'] for f in j.get('files', [])]}: {str(j.get('explanation'))[:70]}"
        except Exception: s = "MODEL answer: " + str(d.get("text"))[:120]
    elif e == "verify_run": s = f"patch verification run {d.get('n')}: rc={d.get('rc')} (0 = CI command passes) changed_lines={d.get('changed_lines', '-')}"
    elif e == "outcome": s = f"DECISION {d.get('action')} | {d.get('reason')} | model_calls={d.get('model_calls')}"
    elif e == "kill": s = "KILL SWITCH engaged, run stopped"
    else: s = json.dumps(d, default=str)[:140]
    return f"+{rec['t']-t0:6.2f}s  {e:12} {s}"

def main(argv=None):
    a = argv or sys.argv[1:]
    path, follow, replay = a[0], "--follow" in a, "--replay" in a
    pos, t0, idle, last = 0, None, 0, None
    while True:
        if os.path.exists(path):
            with open(path) as f:
                f.seek(pos)
                for ln in f:
                    if not ln.endswith("\n"): break
                    rec = json.loads(ln); t0 = t0 or rec["t"]
                    if replay and last is not None: time.sleep(min(2.0, max(0.0, rec["t"] - last)))
                    last = rec["t"]; print(line(rec, t0), flush=True); pos += len(ln); idle = 0
        if not follow: break
        time.sleep(0.2); idle += 1
        if idle > 100: break
    if os.path.exists(path):
        ok, n = tr.verify(path); print(f"-- {n} records, hash chain {'valid' if ok else 'BROKEN'}")

if __name__ == "__main__":
    main()
