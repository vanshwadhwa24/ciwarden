"""Runs demo/run_demo.sh for real, timestamps every output line, and renders those lines to an mp4.
Nothing is typed or scripted into the frames: the text on screen is the captured program output at its real time."""
import os, re, subprocess, sys, time, shutil
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/demo-live-video"
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT + "/f")
cap = os.environ.get("LIVE_CAPTURE")
if cap:
    lines = []
    for raw in open(cap):
        m = re.match(r"\s*([0-9.]+) (.*)", raw.rstrip("\n"))
        if m:
            lines.append((float(m.group(1)), m.group(2)))
    total = lines[-1][0] + 2
else:
    p = subprocess.Popen(["bash", "demo/run_live_watch.sh"], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    lines, t0 = [], time.time()
    for ln in p.stdout:
        lines.append((time.time() - t0, re.sub(r"\x1b\[[0-9;]*m", "", ln.rstrip("\n"))))
    p.wait(); total = lines[-1][0] + 2
open(OUT + "/capture.txt", "w").write("\n".join(f"{t:7.2f} {l}" for t, l in lines))
F = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 18)
B = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 30)
W, H, FPS = 1280, 720, 10
def wrap(s, n=100): return [s[i:i+n] for i in range(0, len(s), n)] or [""]
def card(title, body):
    im = Image.new("RGB", (W, H), (14, 14, 18)); d = ImageDraw.Draw(im)
    d.text((60, 120), title, font=B, fill=(120, 255, 140))
    for i, b in enumerate(body): d.text((60, 220 + i * 34), b, font=F, fill=(225, 225, 225))
    return im
intro = card("ciwarden: LIVE unattended repair run", ["Real failed GitHub Actions run on a public repo, real model (gemini-4-hydrogen, free tier),", "real sandboxed reproduction. Dry-run: the planned PR is saved, nothing is posted.", "",
  "Client-side free-tier limiter active: max 4 requests/min, 18/day hard stop.", "",
  "Every line on screen is captured program output at its real time; nothing is typed in."])
outro = card("What this showed", ["A live, unattended run: fetch the real failure, classify with the real model, reproduce in bwrap,",
  "verify the proposed fix twice in fresh copies, then stop at a saved planned PR (dry-run).",
  "Nothing was posted to GitHub. The same pipeline posted PR #1 earlier (clearly labelled).",
  "Bench + limits: bench/results/POSTCHANGE.md. Trap Pack: tests/trap-pack/RESULTS.md."])
n = 0
def save(im):
    global n; im.save(f"{OUT}/f/{n:05d}.png"); n += 1
for _ in range(FPS * 7): save(intro)
for k in range(int(total * FPS)):
    t = k / FPS
    vis = []
    for lt, l in lines:
        if lt <= t: vis += wrap(l)
    vis = vis[-27:]
    im = Image.new("RGB", (W, H), (12, 12, 12)); d = ImageDraw.Draw(im)
    d.text((14, 8), f"$ bash demo/run_live_watch.sh      [t+{t:5.1f}s, captured output]", font=F, fill=(150, 150, 150))
    for i, l in enumerate(vis):
        col = (120, 255, 140) if l.startswith("==") else (255, 200, 80) if l.startswith(">>>") else (230, 230, 230)
        d.text((14, 40 + i * 24), l, font=F, fill=col)
    save(im)
for _ in range(FPS * 6): save(outro)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{OUT}/f/%05d.png", "-c:v", "libx264", "-pix_fmt", "yuv420p", f"{OUT}/demo-live.mp4"], check=True)
print(OUT + "/demo-live.mp4", round(n / FPS, 1), "s")
