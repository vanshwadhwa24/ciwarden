"""Runs demo/run_demo.sh for real, timestamps every output line, and renders those lines to an mp4.
Nothing is typed or scripted into the frames: the text on screen is the captured program output at its real time."""
import os, re, subprocess, sys, time, shutil
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/demo-video"
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT + "/f")
p = subprocess.Popen(["bash", "demo/run_demo.sh"], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
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
intro = card("ciwarden: unattended CI-failure triage", ["Reproduces a failed build in a sandbox. Fixes only when a fix is verified.",
  "Escalates flaky, outage and suspicious cases instead of guessing.", "",
  "Part 0: a RECORDED trace of a real model run (gemini-4-hydrogen, free tier), replayed.",
  "Parts 1-3: live program output, NO model, real timing.",
  "Every line on screen is captured program output; nothing is typed in."])
outro = card("What this does and does not show", ["Real model repair: recorded in part 0 (bug verified fixed twice). Not a live run:",
  "the free quota (20 calls per day) was spent before this capture.",
  "Live in parts 1-3: injection scan, kill switch cancelling a running command, tamper-evident trace.",
  "Real-model bench (attempt 1, incl. one wrong local PR): bench/results/ and README Limits.",
  "Trap Pack: tests/trap-pack/RESULTS.md (scanner flagged 6/20; read the caveats)."])
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
    d.text((14, 8), f"$ bash demo/run_demo.sh      [t+{t:5.1f}s, captured output]", font=F, fill=(150, 150, 150))
    for i, l in enumerate(vis):
        col = (120, 255, 140) if l.startswith("==") else (255, 200, 80) if l.startswith(">>>") else (230, 230, 230)
        d.text((14, 40 + i * 24), l, font=F, fill=col)
    save(im)
for _ in range(FPS * 6): save(outro)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{OUT}/f/%05d.png", "-c:v", "libx264", "-pix_fmt", "yuv420p", f"{OUT}/demo.mp4"], check=True)
print(OUT + "/demo.mp4", round(n / FPS, 1), "s")
