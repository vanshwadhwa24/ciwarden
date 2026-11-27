"""Append-only JSONL audit trace with a hash chain (tamper evident, not tamper proof)."""
import hashlib, json, time, os


class Trace:
    def __init__(self, path):
        self.path = path
        self.prev = "0" * 64
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        open(path, "a").close()

    def log(self, event, **data):
        rec = {"t": round(time.time(), 3), "event": event, "data": data, "prev": self.prev}
        raw = json.dumps(rec, sort_keys=True, default=str)
        rec["hash"] = hashlib.sha256(raw.encode()).hexdigest()
        self.prev = rec["hash"]
        with open(self.path, "a") as f:
            f.write(json.dumps(rec, sort_keys=True, default=str) + "\n")
        return rec


def verify(path):
    """Return (ok, n_records). Recomputes the chain."""
    prev = "0" * 64
    n = 0
    for line in open(path):
        rec = json.loads(line)
        h = rec.pop("hash")
        if rec["prev"] != prev:
            return False, n
        raw = json.dumps(rec, sort_keys=True, default=str)
        if hashlib.sha256(raw.encode()).hexdigest() != h:
            return False, n
        prev = h
        n += 1
    return True, n
