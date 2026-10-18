"""Drive the deployed site through every web beat and record it at 4K.

    python record.py

Reads build/narration.json for how long each line actually takes, then
holds each shot for exactly that long. Writes build/web.mp4 and
build/web-timings.json, which say where every beat landed so the
assembler can cut the narration to the picture rather than the other
way round.

4K
--
The frame is 3840x2160 and the viewport is set to exactly that, because
Playwright records the viewport and pads a larger record_video_size with
grey rather than upscaling. The page is zoomed so that type is the same
apparent size as it would be on a 1080p take at PAGE_ZOOM 1.35, which is
to say a third larger than the site at a desk. Every overlay drawn on the
page derives from SCALE so the cursor, the address bar and the lock icon
are not four times too small.

The take is not upscaled 1080p. It is rendered at 2160 lines by the
browser, so text is sharp at 4K and stays sharp when YouTube serves it
at 1080p to most people.

Sync
----
Beat actions point the cursor at things. A pointer that arrives while
the words are still describing something else is worse than no pointer,
so moves are scheduled against the sentence that mentions them rather
than a guessed offset. `on_phrase` waits for that sentence.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

from beats import BEATS, sentence_spans, sentences

HERE = Path(__file__).parent
OUT = HERE / "build"
SITE = os.environ.get("BELLWETHER_SITE", "https://d1xfuyog8wiuvf.cloudfront.net")
SITE_HOST = SITE.split("://", 1)[-1]

# The frame. Must equal the viewport.
WIDTH, HEIGHT = 3840, 2160
SCALE = 2

# The site, enlarged for a video rather than a desk. 1.35 at 1080p was a
# third larger than the desk; doubling the frame doubles it again so the
# apparent size on screen is unchanged.
PAGE_ZOOM = 1.35 * SCALE
URL_BAR_HEIGHT = 56 * SCALE
REST_Y = URL_BAR_HEIGHT + 150 * SCALE

ZOOM_JS = f"document.documentElement.style.zoom = '{PAGE_ZOOM}';"

# The site's own smooth scrolling fights the recorder's scroll_to, so it
# is turned off for the take. Nothing a viewer sees depends on it.
NATIVE_SCROLL_OFF_JS = (
    "var s=document.createElement('style');"
    "s.textContent='html{scroll-behavior:auto !important}';"
    "document.head.appendChild(s);"
)

# A visible cursor, because a headless browser draws none and a demo with
# no pointer reads as a screensaver.
#
# The root is zoomed, so every CSS pixel of this ring, including its
# left and top, is multiplied by PAGE_ZOOM when drawn, while the mouse
# reports plain viewport pixels. Take 4 was recorded with the ring set
# straight from clientX: it sat at 2.7 times the pointer, off the frame
# on every beat but one, and on that one it was a blue circle in the
# margin. Sizes below are in zoomed pixels for the same reason.
CURSOR_JS = f"""
var Z={PAGE_ZOOM};
var c=document.createElement('div');
c.id='__cursor';
c.style.cssText=['position:fixed','z-index:2147483647','pointer-events:none',
  'width:24px','height:24px','border-radius:50%',
  'border:2px solid #1f4fd8','background:rgba(31,79,216,0.18)',
  'box-shadow:0 0 0 1px rgba(255,255,255,0.9)',
  'left:-100px','top:-100px',
  'transform:translate(-50%,-50%)','transition:transform 80ms,opacity 300ms'].join(';');
document.body.appendChild(c);
document.addEventListener('mousemove',function(e){{c.style.left=(e.clientX/Z)+'px';c.style.top=(e.clientY/Z)+'px';}});
document.addEventListener('mousedown',function(){{c.style.transform='translate(-50%,-50%) scale(0.75)';}});
document.addEventListener('mouseup',function(){{c.style.transform='translate(-50%,-50%) scale(1)';}});
"""

# A faux address bar, so the frame reads as a real site at a real URL
# rather than a screenshot of a page with no context.
URL_BAR_JS = f"""
var H={URL_BAR_HEIGHT};
document.documentElement.style.setProperty('--__bar', H+'px');
var b=document.createElement('div');
b.style.cssText=['position:fixed','top:0','left:0','right:0','height:'+H+'px',
  'z-index:2147483646','background:#f3f1ec','border-bottom:1px solid #d9d3c7',
  'display:flex','align-items:center','padding:0 {18*SCALE}px','gap:{10*SCALE}px',
  'font:{14*SCALE}px/1 Inter,system-ui,sans-serif','color:#1c1a17'].join(';');
var lock=document.createElement('span');
lock.textContent='\\u{{1F512}}';
lock.style.cssText='font-size:{14*SCALE}px;line-height:1;opacity:0.85';
var url=document.createElement('span');
url.textContent=(location.host+location.pathname+location.search).replace(/\\/$/,'');
url.style.cssText=['background:#fff','border:1px solid #d9d3c7','border-radius:{10*SCALE}px',
  'padding:{8*SCALE}px {14*SCALE}px','flex:1','max-width:{560*SCALE}px'].join(';');
b.appendChild(lock);b.appendChild(url);
document.body.appendChild(b);
document.body.style.paddingTop=H+'px';
"""


# The clapperboard. Playwright's picture starts some fraction of a second
# before the recorder's clock does, and the fraction is not knowable from
# the clock: measured with a flashing square it was a constant 1.82s
# across a take, with no drift, and a different day gives a different
# constant. Before that was measured, every cut began about two seconds
# before its own scroll had finished, and the last beat of take six was a
# blank page. So the take claps: a black square in the corner for a
# moment before the first beat, found again in the finished file, and
# every mark shifted by the difference.
# Long enough that a 4K screencast, which can skip a short flash entirely,
# still catches it: the first Bellwether take missed a 400 ms clap.
CLAP_MS = 1500
CLAP_JS = (
    "var k=document.createElement('div');k.id='__clap';"
    "k.style.cssText='position:fixed;left:0;top:0;width:160px;height:160px;"
    "z-index:2147483647;background:#000';document.body.appendChild(k);"
)


def find_clap(path: Path) -> float:
    """The second at which the corner first goes black in the file."""
    rate = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True).stdout.strip()
    num, den = (int(x) for x in rate.split("/"))
    fps = num / den
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-t", "40", "-i", str(path),
         "-vf", "crop=200:200:0:0,scale=1:1", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        check=True, capture_output=True).stdout
    for k, level in enumerate(raw):
        if level < 60:
            return k / fps
    raise SystemExit("no clapperboard in the first twelve seconds of the take; the marks cannot be aligned")


def run(args: list[str]) -> None:
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"{args[0]} failed:\n{proc.stderr[-1200:]}")


class Recorder:
    """The browser, plus the clock every beat is timed against."""

    def __init__(self, page: Page, start: float, narration: dict[str, float]):
        self.page = page
        self.start = start
        self.narration = narration
        self.marks: list[dict] = []
        self.current: str | None = None

    def mark(self, beat) -> None:
        at = time.monotonic() - self.start
        self.current = beat.key
        self.marks.append({"key": beat.key, "at": round(at, 3)})
        print(f"  {at:6.1f}s  {beat.key:10} {beat.action}")

    def spoken(self, key: str) -> float:
        beat = next(b for b in BEATS if b.key == key)
        return self.narration.get(key, beat.speak_seconds)

    def budget(self, key: str) -> float:
        beat = next(b for b in BEATS if b.key == key)
        return max(beat.pause_before + self.spoken(key), beat.min_hold)

    def hold_beat(self) -> None:
        assert self.current is not None
        began = next(m["at"] for m in self.marks if m["key"] == self.current)
        remaining = began + self.budget(self.current) - (time.monotonic() - self.start)
        if remaining > 0:
            self.page.wait_for_timeout(remaining * 1000)

    def on_phrase(self, text: str) -> None:
        assert self.current is not None
        key = self.current
        line = next(b.say for b in BEATS if b.key == key)
        spans = sentence_spans(line, self.spoken(key))
        parts = sentences(line)
        idx = next((i for i, s in enumerate(parts) if text.lower() in s.lower()), None)
        if idx is None:
            raise SystemExit(
                f"beat {key!r} has no sentence containing {text!r}; "
                "the narration changed and this action did not"
            )
        began = next(m["at"] for m in self.marks if m["key"] == key)
        target = began + next(b.pause_before for b in BEATS if b.key == key) + spans[idx][0]
        remaining = target - (time.monotonic() - self.start)
        if remaining > 0:
            self.page.wait_for_timeout(remaining * 1000)

    def park(self) -> None:
        """Rest the pointer in the right margin, off every word.

        A fixed ring keeps its place on the screen while the page moves
        under it, so without this the pointer sat on whatever the
        previous beat had put there: a stat tile's sentence, the address
        bar, a card it had no business on. Each gesture now starts from
        the same empty place.
        """
        self.page.mouse.move(WIDTH - 100 * SCALE, HEIGHT * 0.55, steps=12)

    def scroll_to(self, selector: str, rest: int = REST_Y) -> None:
        page = self.page
        page.wait_for_selector(selector, timeout=30_000)
        for _ in range(8):
            box = page.locator(selector).first.bounding_box()
            if box is None:
                raise SystemExit(f"{selector!r} is not on the page")
            delta = box["y"] - rest
            if abs(delta) < 12 * SCALE:
                break
            page.mouse.wheel(0, delta)
            page.wait_for_timeout(240)
        self.park()

    def point(self, selector: str, dx: int = 0, dy: int = 0) -> None:
        box = self.page.locator(selector).first.bounding_box()
        if box is None:
            raise SystemExit(f"cannot point at {selector!r}: not on the page")
        self.page.mouse.move(box["x"] + box["width"] / 2 + dx, box["y"] + box["height"] / 2 + dy, steps=22)
        self.page.wait_for_timeout(120)

    def click(self, selector: str) -> None:
        self.point(selector)
        self.page.mouse.down()
        self.page.wait_for_timeout(90)
        self.page.mouse.up()


# --------------------------------------------------------------------------
# Beat actions. Each yields once when the shot is composed; the driver marks
# the beat at that yield so narration starts against a settled screen.
# --------------------------------------------------------------------------

API = os.environ.get("BELLWETHER_API", "https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws")
HERO = "h1"
PROBLEM = "#problem"
HOW = "#how"
FIRST_WEEK = "#first-week"
WHOSE = "nav[aria-label='Whose data']"
CONFOUNDERS = "text=What else could explain this"
ALEXA = "#alexa"
START = "#alexa button:has-text('Start a session')"


def preflight() -> None:
    """The narration states facts about the live service. Check them before a frame is shot."""
    import urllib.request

    from beats import CHECKIN_DAYS

    def summary(profile: str) -> dict:
        with urllib.request.urlopen(f"{API}/v1/profiles/{profile}/summary", timeout=30) as res:
            return json.loads(res.read())

    voice, room = summary("me-voice"), summary("me")
    if voice["eligible_days"] != CHECKIN_DAYS:
        raise SystemExit(
            f"beats.py says {CHECKIN_DAYS} check-in days; the service holds {voice['eligible_days']}. "
            "Set CHECKIN_DAYS and narrate again."
        )
    if room["tier"] != "stable":
        raise SystemExit(f"the narration calls the conversation stream stable; the service says {room['tier']}")
    print(f"preflight: {voice['eligible_days']} check-in days, conversations {room['tier']}")


def goto(r: Recorder, path: str, ready: str) -> None:
    r.page.goto(SITE + path, wait_until="networkidle", timeout=90_000)
    r.page.wait_for_selector(ready, timeout=60_000)
    r.page.wait_for_timeout(1200)


def hero(r: Recorder):
    yield
    r.on_phrase("speech usually shows it first")
    r.point("figure", dy=0)
    r.hold_beat()


def stats(r: Recorder):
    r.scroll_to(f"{PROBLEM} h2", rest=URL_BAR_HEIGHT + 60 * SCALE)
    yield
    r.point(f"{PROBLEM} .grid > div:nth-child(1)")
    r.on_phrase("newest treatments")
    r.point(f"{PROBLEM} .grid > div:nth-child(2)")
    r.hold_beat()


def how(r: Recorder):
    r.scroll_to(f"{HOW} h2", rest=URL_BAR_HEIGHT + 60 * SCALE)
    yield
    r.on_phrase("learns how one person")
    r.point(f"{HOW} ol > li:nth-child(3)")
    r.hold_beat()


def checkins(r: Recorder):
    goto(r, "/app/?profile=me-voice", FIRST_WEEK)
    r.scroll_to(WHOSE, rest=URL_BAR_HEIGHT + 120 * SCALE)
    yield
    r.point("text=Real Bee: check-ins")
    r.on_phrase("Seven days teach it")
    r.scroll_to(FIRST_WEEK, rest=URL_BAR_HEIGHT + 60 * SCALE)
    r.point(f"ol[aria-label='Counted days']")
    r.hold_beat()


def conversations(r: Recorder):
    r.scroll_to(WHOSE, rest=URL_BAR_HEIGHT + 120 * SCALE)
    r.click(f"{WHOSE} a:has-text('My conversations')")
    r.page.wait_for_selector("text=Real Bee: conversations", timeout=60_000)
    r.page.wait_for_timeout(1500)
    # Low enough that the note above the switcher, which says what this
    # stream is, is in frame and readable.
    r.scroll_to(WHOSE, rest=URL_BAR_HEIGHT + 230 * SCALE)
    yield
    r.point("text=Bee does not yet tell speakers apart")
    r.on_phrase("also stable")
    r.point("text=Stable")
    r.hold_beat()


def simulated(r: Recorder):
    r.click(f"{WHOSE} a:has-text('Simulated person')")
    r.page.wait_for_selector("text=Simulated person", timeout=60_000)
    r.page.wait_for_selector(CONFOUNDERS, timeout=60_000)
    r.page.wait_for_timeout(1500)
    r.scroll_to(WHOSE, rest=URL_BAR_HEIGHT + 120 * SCALE)
    yield
    r.point("span:text-is('Simulated person')")
    r.on_phrase("Before the chart")
    r.scroll_to(CONFOUNDERS, rest=URL_BAR_HEIGHT + 60 * SCALE)
    r.point("text=Not sleeping well")
    r.hold_beat()


def chart(r: Recorder):
    # The summary's own lines are the answer to the narration: which
    # measure, which direction, since when. ("text=Eight weeks" matched
    # the badge note "Alex, eight weeks" on the first take.)
    r.scroll_to(WHOSE, rest=URL_BAR_HEIGHT + 30 * SCALE)
    yield
    r.point("li:has-text('lower than your baseline since')")
    r.on_phrase("which measures moved")
    r.page.mouse.move(*_box_right(r, "li:has-text('higher than your baseline since')"), steps=30)
    r.hold_beat()


def _box_right(r: Recorder, selector: str) -> tuple[float, float]:
    box = r.page.locator(selector).first.bounding_box()
    return box["x"] + box["width"] * 0.85, box["y"] + box["height"] * 0.35


def alexa(r: Recorder):
    goto(r, "/", HERO)
    r.scroll_to(f"{ALEXA} h2", rest=URL_BAR_HEIGHT + 40 * SCALE)
    yield
    r.click(START)
    r.page.locator("#mcp-steps > li").nth(2).wait_for(state="visible", timeout=60_000)
    r.on_phrase("Seven tools")
    r.scroll_to("#mcp-steps", rest=URL_BAR_HEIGHT + 60 * SCALE)
    r.point("#mcp-steps > li:nth-child(3)")
    r.hold_beat()


def report(r: Recorder):
    goto(r, "/report/", "text=Bellwether speech report")
    r.scroll_to("text=Bellwether speech report", rest=URL_BAR_HEIGHT + 60 * SCALE)
    yield
    r.on_phrase("what changed")
    r.point("text=Current status")
    r.on_phrase("Open source")
    r.page.evaluate(END_CARD_JS)
    r.hold_beat()


# The links, for a judge who wants to check, under the address bar.
END_CARD_JS = """
(() => {
  const S = __SCALE__;
  const card = document.createElement('div');
  card.style.cssText = ['position:fixed','left:0','right:0','bottom:0','top:' + (56 * S) + 'px',
    'z-index:2147483645','background:#10201d','color:#f2f4f8','display:flex','flex-direction:column',
    'align-items:center','justify-content:center','gap:' + (22 * S) + 'px','font-family:Inter,system-ui,sans-serif',
    'opacity:0','transition:opacity 600ms ease-out'].join(';');
  const h = document.createElement('div');
  h.textContent = 'Bellwether';
  h.style.cssText = 'font-weight:700;font-size:' + (64 * S) + 'px;margin-bottom:' + (18 * S) + 'px';
  card.appendChild(h);
  [['Live', 'd1xfuyog8wiuvf.cloudfront.net'], ['Code', 'github.com/usv240/bellwether'],
   ['Open source', 'pypi.org/project/speech-vitals'], ['Not a diagnosis', 'a record of change, for a clinician you trust']].forEach(([k, v]) => {
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:' + (18 * S) + 'px;align-items:baseline;font-size:' + (30 * S) + 'px';
    const a = document.createElement('span'); a.textContent = k;
    a.style.cssText = 'color:#e0b25a;font-weight:600;min-width:' + (260 * S) + 'px;text-align:right';
    const b = document.createElement('span'); b.textContent = v;
    b.style.cssText = 'font-family:ui-monospace,Consolas,monospace';
    row.appendChild(a); row.appendChild(b); card.appendChild(row);
  });
  document.documentElement.appendChild(card);
  const cur = document.getElementById('__cursor'); if (cur) cur.style.opacity = '0';
  requestAnimationFrame(() => { card.style.opacity = '1'; });
})();
""".replace("__SCALE__", str(SCALE / PAGE_ZOOM))
# The root element is zoomed by PAGE_ZOOM, and the card is appended to it,
# so its sizes are divided by the zoom: the first take drew the links at
# 2.7 times their size and ran them off the right edge.


ACTIONS = {f.__name__: f for f in (hero, stats, how, checkins, conversations, simulated, chart, alexa, report)}


def assert_full_frame(path: Path) -> None:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    w, h = (int(x) for x in out.split(",")[:2])
    if (w, h) != (WIDTH, HEIGHT):
        raise SystemExit(f"recorded {w}x{h} but the frame is {WIDTH}x{HEIGHT}; Playwright padded rather than filled")


def main() -> int:
    manifest = OUT / "narration.json"
    if not manifest.exists():
        raise SystemExit("no narration.json: run narrate.py first")
    narration = {n["key"]: n["seconds"] for n in json.loads(manifest.read_text(encoding="utf8"))}

    preflight()
    web = [b for b in BEATS if not b.is_tv]
    video_dir = OUT / "raw"
    video_dir.mkdir(parents=True, exist_ok=True)
    for stale in video_dir.glob("*.webm"):
        stale.unlink()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", args=["--force-color-profile=srgb", "--autoplay-policy=no-user-gesture-required"])
        context = browser.new_context(
            viewport={"width": WIDTH, "height": HEIGHT},
            device_scale_factor=1,
            color_scheme="light",
            record_video_dir=str(video_dir),
            record_video_size={"width": WIDTH, "height": HEIGHT},
        )
        context.add_init_script("try { localStorage.setItem('bw-theme','light'); } catch (e) {}")
        page = context.new_page()
        page.add_init_script(
            "document.addEventListener('DOMContentLoaded', () => {" + ZOOM_JS + NATIVE_SCROLL_OFF_JS + CURSOR_JS + URL_BAR_JS + "});"
        )
        print(f"{WIDTH}x{HEIGHT} against {SITE}")
        page.goto(SITE, wait_until="networkidle", timeout=90_000)
        page.wait_for_selector(HERO, timeout=60_000)
        page.wait_for_timeout(1200)
        page.evaluate(CLAP_JS)
        clap_at = time.monotonic()
        page.wait_for_timeout(CLAP_MS)
        page.evaluate("document.getElementById('__clap').remove()")
        page.wait_for_timeout(400)
        r = Recorder(page, time.monotonic(), narration)
        clap_clock = clap_at - r.start  # before the clock began, so negative
        r.park()
        for beat in web:
            steps = ACTIONS[beat.action](r)
            next(steps, None)
            r.mark(beat)
            for _ in steps:
                pass

        total = time.monotonic() - r.start
        video = page.video
        context.close()
        src = Path(video.path())
        browser.close()

    dest = OUT / "web.mp4"
    run(["ffmpeg", "-y", "-i", str(src), "-c:v", "libx264", "-crf", "18", "-preset", "medium",
         "-tune", "stillimage", "-pix_fmt", "yuv420p", "-an", str(dest)])
    assert_full_frame(dest)

    # Marks were taken on the clock; the file runs on its own time. The
    # clap is the one event seen by both.
    try:
        offset = find_clap(dest) - clap_clock
    except SystemExit:
        # No clap seen. The file ends when the context closes, which is
        # when the clock stopped, so align from the end instead.
        length_now = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(dest)],
            check=True, capture_output=True, text=True).stdout.strip())
        offset = length_now - total
        print(f"no clap found; aligned from the end of the file ({offset:.2f}s)")
    if not 0.0 <= offset <= 30.0:
        raise SystemExit(f"the picture is offset {offset:.2f}s from the clock, which is not credible")
    for m in r.marks:
        m["at"] = round(m["at"] + offset, 3)
    length = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(dest)],
        check=True, capture_output=True, text=True).stdout.strip())

    (OUT / "web-timings.json").write_text(
        json.dumps({"video": round(length, 3), "width": WIDTH, "height": HEIGHT,
                    "clockOffset": round(offset, 3), "beats": r.marks}, indent=1),
        encoding="utf8",
    )
    print(f"\nwrote {dest.name} and web-timings.json")
    print(f"{len(r.marks)} web beats over {total:.1f}s; picture runs {offset:.2f}s ahead of the clock")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
