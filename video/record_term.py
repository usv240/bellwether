"""The terminal camera: real commands, real output, rendered.

    python record_term.py capture      # run the commands for real, keep their output
    python record_term.py render       # type them out in a terminal frame and record it

Two steps on purpose. `capture` runs each command against the operator's
own Bee and saves exactly what came back, with the time it took. It can
only be run where the Bee is signed in, and it refuses to run if the
household is not set up, because the point is a real day. `render` opens
a terminal-styled page in the same 4K browser recorder the web beats
use, types each command at a human pace, prints its saved output, and
writes `build/tv.mp4` and `build/tv-timings.json`, the same contract the
assembler already reads for its second camera. The frame carries the
words "a real run, rendered" so nobody mistakes the typing for a live
session. Nothing is invented and nothing is sped up: the output is the
output, and the pauses are the pauses.

Why not screen-record a real terminal: a Windows console is a GDI window
at whatever size and font it has, and a capture of it in a 4K frame is
either tiny or blurry. A rendering of the same bytes at the right size
is more honest to the viewer's eye, and the capture step is what keeps
it honest to the facts.
"""

from __future__ import annotations

import html
import json
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

from beats import BEATS
from record import CLAP_MS, HEIGHT, WIDTH, find_clap

HERE = Path(__file__).parent
OUT = HERE / "build"
CAPTURE = OUT / "term-capture.json"

# The beats and the commands each shows. Output is captured once and
# rendered as many times as the cut needs.
BW = HERE.parent
MCP = "https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws/mcp"
SHOTS = {
    "term-mine": [
        ["bellwether-ingest", "mine", "--days", "2"],
    ],
    "term-agent": [
        ["python", "apps/agent/speech_check_in.py", "--profile", "alex-drift"],
    ],
    # The hosted check-in, for real: the host speaks through the speaker,
    # the wearer answers, the Bee records, the day is counted and the
    # coaching note read back. Run on the evening of the take; the answer
    # window is shortened so the capture stays under two minutes.
    "term-host": [
        ["python", "apps/agent/check_in_host.py", "--profile", "me", "--count", "--answer-seconds", "25"],
    ],
}
# What each command actually runs with. Shown on screen as a comment line,
# so the frame never hides where a command pointed.
RUN = {
    "bellwether-ingest": [str(BW / ".venv" / "Scripts" / "bellwether-ingest.exe")],
    "python": [r"C:\Users\ujwal\anaconda3\python.exe"],
}
NOTES = {
    "term-mine": "# the builder's own Bee, signed in on this machine",
    "term-agent": "# BELLWETHER_MCP is the deployed server, " + MCP,
    "term-host": "# the assistant asks, the Bee on my wrist listens; deployed MCP server, Polly for the voice",
}


def capture() -> int:
    import os

    OUT.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "BELLWETHER_MCP": MCP, "PYTHONIOENCODING": "utf-8"}
    record: dict = {"captured": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "shots": {}}
    for key, commands in SHOTS.items():
        record["shots"][key] = []
        for argv in commands:
            real = RUN[argv[0]] + argv[1:]
            t0 = time.perf_counter()
            proc = subprocess.run(real, cwd=BW, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=300, env=env)
            out = (proc.stdout + proc.stderr).rstrip()
            record["shots"][key].append({"argv": argv, "output": out, "seconds": round(time.perf_counter() - t0, 2),
                                         "code": proc.returncode, "note": NOTES.get(key, "")})
            print(f"  {' '.join(argv)}: {proc.returncode}, {len(out.splitlines())} lines, {time.perf_counter() - t0:.1f}s")
            if proc.returncode != 0:
                print(out[-800:], file=sys.stderr)
                return 1
    CAPTURE.write_text(json.dumps(record, indent=1), encoding="utf8")
    print(f"wrote {CAPTURE}")
    return 0


PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;background:#12151b;color:#e8e6e1;font:{fs}px/1.5 'Cascadia Mono','Consolas',monospace;height:100%}}
.frame{{position:absolute;inset:{pad}px;background:#191d25;border:1px solid #2a303b;border-radius:{r}px;box-shadow:0 20px 60px rgba(0,0,0,.4);overflow:hidden}}
.bar{{height:{bar}px;background:#222732;border-bottom:1px solid #2a303b;display:flex;align-items:center;padding:0 {pad2}px;color:#aeb3bd;font-size:{fs2}px}}
.bar span{{margin-left:auto;color:#7c828d}}
pre{{margin:0;padding:{pad2}px;white-space:pre-wrap;word-break:break-word}}
.p{{color:#7aa2ff}}.k{{color:#f3f1ec}}.d{{color:#aeb3bd}}.c{{color:#7c828d}}
</style></head><body><div class="frame"><div class="bar">bellwether, a real run<span>rendered from its captured output</span></div><pre id="t"></pre></div></body></html>"""


def render() -> int:
    if not CAPTURE.exists():
        print("no capture: run record_term.py capture on the machine with the Bee", file=sys.stderr)
        return 2
    rec = json.loads(CAPTURE.read_text(encoding="utf8"))
    narration = {n["key"]: n["seconds"] for n in json.loads((OUT / "narration.json").read_text(encoding="utf8"))}
    scale = WIDTH / 1920
    page_html = PAGE.format(fs=int(30 * scale), fs2=int(22 * scale), pad=int(80 * scale), pad2=int(28 * scale), r=int(16 * scale), bar=int(56 * scale))
    (OUT / "term.html").write_text(page_html, encoding="utf8")
    raw_dir = OUT / "raw-term"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for stale in raw_dir.glob("*.webm"):
        stale.unlink()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")
        ctx = browser.new_context(viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=1,
                                  record_video_dir=str(raw_dir), record_video_size={"width": WIDTH, "height": HEIGHT})
        page = ctx.new_page()
        page.goto((OUT / "term.html").as_uri())
        page.wait_for_timeout(800)
        page.evaluate("var k=document.createElement('div');k.id='__clap';k.style.cssText='position:fixed;left:0;top:0;width:160px;height:160px;z-index:9;background:#000';document.body.appendChild(k)")
        clap_at = time.monotonic()
        page.wait_for_timeout(CLAP_MS)
        page.evaluate("document.getElementById('__clap').remove()")
        page.wait_for_timeout(400)
        start = time.monotonic()
        clap_clock = clap_at - start
        marks: list[dict] = []

        def append(text: str, cls: str) -> None:
            page.evaluate("([t, c]) => { const el = document.getElementById('t'); const s = document.createElement('span'); s.className = c; s.textContent = t; el.appendChild(s); el.scrollTop = el.scrollHeight; }", [text, cls])

        def type_out(text: str) -> None:
            for ch in text:
                append(ch, "k")
                page.wait_for_timeout(45)

        for beat in [b for b in BEATS if b.is_terminal]:
            shots = rec["shots"].get(beat.key, [])
            marks.append({"key": beat.key, "at": round(time.monotonic() - start, 3)})
            budget = max(beat.pause_before + narration.get(beat.key, beat.speak_seconds), beat.min_hold)
            deadline = time.monotonic() + budget
            for shot in shots:
                if shot.get("note"):
                    append(shot["note"] + "\n", "c")
                append("$ ", "p")
                type_out(" ".join(shot["argv"]))
                append("\n", "k")
                page.wait_for_timeout(int(min(1.5, shot["seconds"]) * 1000))
                for line in shot["output"].splitlines():
                    append(line + "\n", "d")
                    page.wait_for_timeout(70)
                append(f"[this run took {shot['seconds']:.0f} seconds]\n", "c")
                page.wait_for_timeout(600)
            remaining = deadline - time.monotonic()
            if remaining > 0:
                page.wait_for_timeout(int(remaining * 1000))
            page.evaluate("document.getElementById('t').textContent=''")
            page.wait_for_timeout(300)
        page.wait_for_timeout(1000)
        total = time.monotonic() - start
        video = page.video
        ctx.close()
        src = Path(video.path())
        browser.close()

    dest = OUT / "tv.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-r", "25", "-fps_mode", "cfr", "-c:v", "libx264", "-crf", "18",
                    "-preset", "medium", "-pix_fmt", "yuv420p", "-an", str(dest)], check=True)
    offset = find_clap(dest) - clap_clock
    for m in marks:
        m["at"] = round(m["at"] + offset, 3)
    length = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(dest)],
                                  check=True, capture_output=True, text=True).stdout.strip())
    (OUT / "tv-timings.json").write_text(json.dumps({"video": round(length, 3), "width": WIDTH, "height": HEIGHT,
                                                      "device": "a terminal, a real run rendered", "captured": rec["captured"],
                                                      "clockOffset": round(offset, 3), "beats": marks}, indent=1), encoding="utf8")
    print(f"wrote {dest.name} and tv-timings.json: {len(marks)} beats over {total:.1f}s")
    return 0


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("capture", "render"):
        print(__doc__)
        return 2
    return capture() if sys.argv[1] == "capture" else render()


if __name__ == "__main__":
    raise SystemExit(main())
