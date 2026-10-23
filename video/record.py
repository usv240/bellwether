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
        # Inside the sentence, by word position: a cue on its ninth word of
        # twenty-five fires a third of the way through, so two cues in one
        # sentence land on their own words instead of both at its start.
        sentence = parts[idx]
        before = sentence.lower()[: sentence.lower().index(text.lower())]
        frac = len(before.split()) / max(1, len(sentence.split()))
        s0, s1 = spans[idx]
        target = began + next(b.pause_before for b in BEATS if b.key == key) + s0 + frac * (s1 - s0)
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
YOUR_OWN = "pre:has-text('--profile <your-name>')"
WHOSE = "nav[aria-label='Whose data']"
CONFOUNDERS = "text=What else could explain this"
RIGHT_NOW = "div:has(> p:text-is('Right now'))"
NOTABLE = "section:has(> h2:has-text('Notable changes'))"
ALEXA = "#alexa"
START = "#alexa button:has-text('Start a session')"



# Full-frame cards drawn inside the zoomed document: sizes are divided by
# the zoom, as the end card's are, so a 15px line is 15px on a 1080p frame.
def _card_js(inner_html: str, card_id: str) -> str:
    return """
(() => {
  const S = __SCALE__;
  const old = document.getElementById('__ID__'); if (old) old.remove();
  const card = document.createElement('div');
  card.id = '__ID__';
  card.style.cssText = ['position:fixed','left:0','right:0','bottom:0','top:' + (56 * S) + 'px',
    'z-index:2147483645','background:#10201d','color:#f2f4f8','display:flex','flex-direction:column',
    'align-items:center','justify-content:center','gap:' + (18 * S) + 'px','font-family:Inter,system-ui,sans-serif',
    'opacity:0','transition:opacity 500ms ease-out'].join(';');
  card.innerHTML = __HTML__;
  document.documentElement.appendChild(card);
  const cur = document.getElementById('__cursor'); if (cur) cur.style.opacity = '0';
  requestAnimationFrame(() => { card.style.opacity = '1'; });
})();
""".replace("__SCALE__", str(SCALE / PAGE_ZOOM)).replace("__ID__", card_id).replace("__HTML__", json.dumps(inner_html.replace("__S__", str(SCALE / PAGE_ZOOM))))


def _fade_card(r: "Recorder", card_id: str) -> None:
    r.page.evaluate(f"(() => {{ const c = document.getElementById('{card_id}'); if (!c) return; c.style.opacity = '0'; setTimeout(() => c.remove(), 520); const cur = document.getElementById('__cursor'); if (cur) cur.style.opacity = '1'; }})()")
    r.page.wait_for_timeout(560)


def _tile(title: str, body: str, accent: str = "#e0b25a") -> str:
    S = "__S__"
    return (f'<div style="flex:1;min-width:0;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);'
            f'border-radius:calc(14px * {S});padding:calc(26px * {S}) calc(28px * {S})">'
            f'<div style="color:{accent};font-weight:700;font-size:calc(30px * {S});line-height:1.15">{title}</div>'
            f'<div style="margin-top:calc(12px * {S});font-size:calc(20px * {S});line-height:1.4;color:#d7dde6">{body}</div></div>')


HOOK_HTML = (
    '<div style="font-weight:700;font-size:calc(54px * __S__);margin-bottom:calc(10px * __S__)">Bellwether</div>'
    '<div style="display:flex;gap:calc(22px * __S__);width:calc(1180px * __S__);align-items:stretch">'
    + _tile("Bee", "captures your speech, on the band you already wear")
    + '<div style="align-self:center;font-size:calc(40px * __S__);color:#7c8a86">&rarr;</div>'
    + _tile("Bellwether", "finds changes in how you speak, against your own past")
    + '<div style="align-self:center;font-size:calc(40px * __S__);color:#7c8a86">&rarr;</div>'
    + _tile("Doctor report", "supports a better conversation with a clinician")
    + '</div>'
    '<div style="margin-top:calc(14px * __S__);font-size:calc(20px * __S__);color:#9aa7a3">Nine numbers a day. Never your words. Not a diagnosis.</div>'
)

COMPARE_HTML = (
    '<div style="font-size:calc(18px * __S__);letter-spacing:0.08em;text-transform:uppercase;color:#e0b25a;font-weight:700">Two simulated people, labelled SIMULATED on every screen</div>'
    '<div style="display:flex;gap:calc(26px * __S__);width:calc(1180px * __S__);align-items:stretch">'
    + _tile("Stable speech", "Fifty-four assessed days. Every measure inside their own normal range. Forty-seven stable days in a row. <b style=\"color:#8fd3b6\">Nothing flagged.</b>", "#8fd3b6")
    + _tile("Changing speech", "Fifty-four assessed days. Nine measures drifted together and stayed there: shorter sentences, more fillers, fewer rare words. <b style=\"color:#f0a36a\">Persistent change since September 3.</b>", "#f0a36a")
    + '</div>'
    '<div style="margin-top:calc(10px * __S__);font-size:calc(18px * __S__);color:#9aa7a3">Read from fixtures/personas/alex-stable and alex-drift, the committed synthetic personas</div>'
)

AWS_HTML = (
    '<div style="font-size:calc(18px * __S__);letter-spacing:0.08em;text-transform:uppercase;color:#e0b25a;font-weight:700">Where the data goes</div>'
    '<div style="display:flex;gap:calc(16px * __S__);width:calc(1260px * __S__);align-items:stretch">'
    + _tile("Bee", "records the day; the transcript stays in your Bee account")
    + '<div style="align-self:center;font-size:calc(36px * __S__);color:#7c8a86">&rarr;</div>'
    + _tile("Your computer", "speech-vitals turns a day into nine numbers; the words are dropped here")
    + '<div style="align-self:center;font-size:calc(36px * __S__);color:#7c8a86">&rarr;</div>'
    + _tile("AWS", "AWS Lambda and Amazon DynamoDB keep the nine numbers; Claude on Amazon Bedrock phrases the note; the agent runs on Amazon Bedrock AgentCore")
    + '<div style="align-self:center;font-size:calc(36px * __S__);color:#7c8a86">&rarr;</div>'
    + _tile("Dashboard and report", "the trend, the weekly note, the page for your clinician; the MCP server for Alexa+")
    + '</div>'
    '<div style="margin-top:calc(10px * __S__);font-size:calc(18px * __S__);color:#9aa7a3">apps/ingest and packages/speech-vitals on your computer; apps/server, apps/agent and infra on AWS</div>'
)



def _zoom(r: "Recorder", selector: str, factor: float = 1.25) -> None:
    """Enlarge one block in place so a judge reads the result, not the page."""
    r.page.locator(selector).first.evaluate("(d, f) => { d.style.transition = 'transform 400ms ease'; d.style.transformOrigin = '0 0'; d.style.transform = 'scale(' + f + ')'; d.style.position = 'relative'; d.style.zIndex = '5'; d.style.background = 'var(--surface, #fff)'; d.style.boxShadow = '0 12px 40px rgba(0,0,0,0.12)'; d.style.borderRadius = '12px'; d.style.padding = '8px 12px'; }", factor)
    r.page.wait_for_timeout(450)


def _unzoom(r: "Recorder", selector: str) -> None:
    r.page.locator(selector).first.evaluate("d => { d.style.transform = ''; d.style.boxShadow = ''; d.style.padding = ''; d.style.zIndex = ''; }")
    r.page.wait_for_timeout(300)


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
    print(f"preflight: {voice['eligible_days']} check-in days, conversations {room['tier']}")


def goto(r: Recorder, path: str, ready: str) -> None:
    r.page.goto(SITE + path, wait_until="networkidle", timeout=90_000)
    r.page.wait_for_selector(ready, timeout=60_000)
    r.page.wait_for_timeout(1200)


def hero(r: Recorder):
    r.page.evaluate(_card_js(HOOK_HTML, "__hook"))
    yield
    r.on_phrase("Nine numbers a day")
    _fade_card(r, "__hook")
    r.point(HERO, dy=0)
    r.hold_beat()


VOICES = "h3:has-text('What people say they want')"


def stats(r: Recorder):
    r.scroll_to(f"{PROBLEM} h2", rest=URL_BAR_HEIGHT + 60 * SCALE)
    yield
    r.on_phrase("three and a half years")
    r.point(f"{PROBLEM} .grid > div:nth-child(1)")
    r.on_phrase("nearly four in five")
    r.scroll_to(VOICES, rest=URL_BAR_HEIGHT + 120 * SCALE)
    r.point(f"{VOICES} + div > div:nth-child(1)")
    r.hold_beat()


def how(r: Recorder):
    r.scroll_to(f"{HOW} h2", rest=URL_BAR_HEIGHT + 60 * SCALE)
    yield
    r.on_phrase("Everyone speaks differently")
    r.point(f"{HOW} ol > li:nth-child(3)")
    r.hold_beat()


DAYS_ASSESSED = "dt:has-text('Days assessed')"


def checkins(r: Recorder):
    # During the warmup the page shows the first-week card; once seven days
    # are counted it shows the summary with the days assessed instead.
    goto(r, "/app/?profile=me-voice", WHOSE)
    r.page.wait_for_selector(f"{FIRST_WEEK}, {DAYS_ASSESSED}", timeout=60_000)
    r.scroll_to(WHOSE, rest=URL_BAR_HEIGHT + 120 * SCALE)
    yield
    r.point("text=Real Bee: check-ins")
    r.on_phrase("Seven days counted")
    if r.page.locator(FIRST_WEEK).count():
        r.scroll_to(FIRST_WEEK, rest=URL_BAR_HEIGHT + 60 * SCALE)
        r.point(f"ol[aria-label='Counted days']")
    else:
        r.scroll_to(DAYS_ASSESSED, rest=URL_BAR_HEIGHT + 260 * SCALE)
        r.point(DAYS_ASSESSED, dx=260 * SCALE)
    r.on_phrase("Anyone with a Bee")
    # The one command sits behind the "How this works" disclosure at the
    # end of the page; open it on camera, then point at the line.
    how = "details summary:has-text('How this works')"
    r.scroll_to(how, rest=URL_BAR_HEIGHT + 300 * SCALE)
    r.click(how)
    r.page.wait_for_timeout(500)
    r.scroll_to(YOUR_OWN, rest=URL_BAR_HEIGHT + 200 * SCALE)
    r.point(YOUR_OWN)
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
    r.on_phrase("the room, not just me")
    r.point("text=Real Bee: conversations")
    r.hold_beat()


REPLAY = "#first-week-replay"
NEXT_EVENING = "#first-week-replay button[aria-label='Next evening']"


def replay(r: Recorder):
    goto(r, "/app/?profile=sam-first-week", REPLAY)
    r.scroll_to(REPLAY, rest=URL_BAR_HEIGHT + 40 * SCALE)
    yield
    r.point("text=Simulated first week, one evening at a time")
    # One evening a beat, by the real button, to the short third day.
    for _ in range(2):
        r.click(NEXT_EVENING)
        r.page.wait_for_timeout(700)
    r.on_phrase("A short day")
    r.point(f"{REPLAY} ol li:nth-child(3)")
    r.on_phrase("On day nine")
    for _ in range(6):
        r.click(NEXT_EVENING)
        r.page.wait_for_timeout(450)
    r.page.wait_for_selector(f"{REPLAY} span:text-is('Stable')", timeout=30_000)
    r.point(f"{REPLAY} ol li:nth-child(9)")
    r.on_phrase("reads the note aloud")
    r.point(f"{REPLAY} p:has-text('host says')")
    r.hold_beat()


def compare(r: Recorder):
    r.scroll_to(WHOSE, rest=URL_BAR_HEIGHT + 120 * SCALE)
    r.click(f"{WHOSE} a:has-text('Simulated person')")
    r.page.wait_for_selector("text=Simulated person", timeout=60_000)
    r.page.wait_for_selector(CONFOUNDERS, timeout=60_000)
    r.page.wait_for_timeout(1200)
    r.scroll_to(".recharts-wrapper", rest=URL_BAR_HEIGHT + 150 * SCALE)
    r.page.evaluate(_card_js(COMPARE_HTML, "__compare"))
    yield
    r.on_phrase("The other changes")
    _fade_card(r, "__compare")
    # Ring the late days: the right third of the chart, where the line leaves the band.
    box = r.page.locator(".recharts-wrapper").first.bounding_box()
    z = PAGE_ZOOM
    left, top = (box["x"] + box["width"] * 0.62) / z, (box["y"] + box["height"] * 0.05) / z
    w, h = box["width"] * 0.36 / z, box["height"] * 0.72 / z
    r.page.evaluate("([l, t, w, h]) => { const k = document.createElement('div'); k.id = '__ring'; k.style.cssText = 'position:fixed;left:' + l + 'px;top:' + t + 'px;width:' + w + 'px;height:' + h + 'px;border:4px solid #f0a36a;border-radius:14px;box-shadow:0 0 0 6px rgba(240,163,106,0.18);z-index:2147483644;opacity:0;transition:opacity 400ms ease'; document.documentElement.appendChild(k); requestAnimationFrame(() => { k.style.opacity = '1'; }); }", [left, top, w, h])
    r.page.mouse.move(box["x"] + box["width"] * 0.35, box["y"] + box["height"] * 0.7, steps=24)
    r.page.mouse.move(box["x"] + box["width"] * 0.9, box["y"] + box["height"] * 0.25, steps=60)
    r.on_phrase("which measures moved")
    r.page.evaluate("const k = document.getElementById('__ring'); if (k) k.remove();")
    r.scroll_to(WHOSE, rest=URL_BAR_HEIGHT + 30 * SCALE)
    _zoom(r, RIGHT_NOW, 1.3)
    r.point("span:text-is('Discuss')", dx=0)
    r.on_phrase("It offers everyday explanations")
    _unzoom(r, RIGHT_NOW)
    r.scroll_to(CONFOUNDERS, rest=URL_BAR_HEIGHT + 60 * SCALE)
    r.point("text=Not sleeping well")
    r.hold_beat()


def aws(r: Recorder):
    r.page.evaluate(_card_js(AWS_HTML, "__aws"))
    yield
    r.hold_beat()
    _fade_card(r, "__aws")


def close(r: Recorder):
    goto(r, "/app/", ".recharts-wrapper")
    r.scroll_to(".recharts-wrapper", rest=URL_BAR_HEIGHT + 150 * SCALE)
    yield
    r.on_phrase("For someone noticing")
    goto(r, "/report/", "text=Bellwether speech report")
    r.scroll_to("text=Tier over the period", rest=URL_BAR_HEIGHT + 120 * SCALE)
    r.on_phrase("It does not diagnose")
    r.page.evaluate(END_CARD_JS)
    r.hold_beat()


def simulated(r: Recorder):
    r.scroll_to(WHOSE, rest=URL_BAR_HEIGHT + 120 * SCALE)
    r.click(f"{WHOSE} a:has-text('Simulated person')")
    r.page.wait_for_selector("text=Simulated person", timeout=60_000)
    r.page.wait_for_selector(CONFOUNDERS, timeout=60_000)
    r.page.wait_for_timeout(1500)
    r.scroll_to(WHOSE, rest=URL_BAR_HEIGHT + 120 * SCALE)
    yield
    r.point("span:text-is('Simulated person')")
    r.on_phrase("Bellwether shows when")
    # The chart is the strongest picture in the video: the band, the
    # days inside it, and the days that leave it. Rest on it, then trace
    # the late days along the line.
    r.scroll_to(".recharts-wrapper", rest=URL_BAR_HEIGHT + 150 * SCALE)
    box = r.page.locator(".recharts-wrapper").first.bounding_box()
    r.page.mouse.move(box["x"] + box["width"] * 0.35, box["y"] + box["height"] * 0.7, steps=24)
    r.page.wait_for_timeout(900)
    r.page.mouse.move(box["x"] + box["width"] * 0.9, box["y"] + box["height"] * 0.25, steps=60)
    r.on_phrase("how far")
    r.scroll_to(WHOSE, rest=URL_BAR_HEIGHT + 30 * SCALE)
    r.point("li:has-text('lower than your baseline since')")
    r.on_phrase("poor sleep")
    r.scroll_to(CONFOUNDERS, rest=URL_BAR_HEIGHT + 60 * SCALE)
    r.point("text=Not sleeping well")
    r.hold_beat()


def proof(r: Recorder):
    # The chart stays in frame; what the software was checked against
    # appears beside it, so the claim and the picture are on one screen.
    r.scroll_to(".recharts-wrapper", rest=URL_BAR_HEIGHT + 150 * SCALE)
    yield
    r.page.evaluate(EVIDENCE_JS)
    r.on_phrase("three hundred automated tests")
    r.point(".recharts-wrapper")
    r.hold_beat()
    r.page.evaluate("document.getElementById('__evidence') && document.getElementById('__evidence').remove()")


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
    r.on_phrase("never your conversations")
    r.scroll_to("#mcp-steps", rest=URL_BAR_HEIGHT + 60 * SCALE)
    r.point("#mcp-steps > li:nth-child(3)")
    r.hold_beat()


def report(r: Recorder):
    goto(r, "/report/", "text=Bellwether speech report")
    r.scroll_to("text=Bellwether speech report", rest=URL_BAR_HEIGHT + 60 * SCALE)
    yield
    r.on_phrase("simple timeline")
    r.scroll_to(NOTABLE, rest=URL_BAR_HEIGHT + 160 * SCALE)
    _zoom(r, NOTABLE, 1.3)
    r.point(f"{NOTABLE} h2", dx=120 * SCALE)
    r.on_phrase("which questions to ask")
    _unzoom(r, NOTABLE)
    r.scroll_to("text=For the Annual Wellness Visit", rest=URL_BAR_HEIGHT + 120 * SCALE)
    r.point("text=Questions to bring")
    r.hold_beat()


# What the engineering was checked against, on screen and unspoken. Both
# numbers are in the repository; the label says what they are not.
EVIDENCE_JS = """
(() => {
  const S = __SCALE__;
  const box = document.createElement('div');
  box.id = '__evidence';
  box.style.cssText = ['position:fixed','right:' + (24 * S) + 'px','top:__TOP__px','z-index:2147483645',
    'background:rgba(16,32,29,0.94)','color:#f2f4f8','border-radius:' + (10 * S) + 'px',
    'padding:' + (14 * S) + 'px ' + (18 * S) + 'px','font-family:Inter,system-ui,sans-serif',
    'font-size:' + (17 * S) + 'px','line-height:1.5','max-width:' + (520 * S) + 'px',
    'opacity:0','transition:opacity 400ms ease-out'].join(';');
  box.innerHTML = '<div style="font-weight:700;color:#e0b25a;margin-bottom:' + (6 * S) + 'px">Checked, not claimed</div>'
    + '<div><b>Real Bee data:</b> seven counted days from my own band</div>'
    + '<div><b>Privacy:</b> the words never leave the computer; nine numbers a day are sent</div>'
    + '<div><b>Tested:</b> 300 automated tests; 349 Supreme Court sessions, zero false alarms</div>'
    + '<div style="opacity:0.7;margin-top:' + (6 * S) + 'px">Software behaviour, not medical accuracy</div>';
  document.documentElement.appendChild(box);
  requestAnimationFrame(() => { box.style.opacity = '1'; });
})();
""".replace("__SCALE__", str(SCALE / PAGE_ZOOM)).replace("__TOP__", str(URL_BAR_HEIGHT + 24))
# The address bar is URL_BAR_HEIGHT CSS pixels on the zoomed root, so the
# note starts below it; the first render hid its heading under the bar.


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
  h.style.cssText = 'font-weight:700;font-size:' + (64 * S) + 'px;margin-bottom:' + (6 * S) + 'px';
  card.appendChild(h);
  const t = document.createElement('div');
  t.textContent = 'Because sometimes the first step is simply noticing.';
  t.style.cssText = 'font-size:' + (28 * S) + 'px;color:#d7dde6;margin-bottom:' + (18 * S) + 'px';
  card.appendChild(t);
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


ACTIONS = {f.__name__: f for f in (hero, stats, how, checkins, conversations, replay, simulated, compare, proof, chart, alexa, report, aws, close)}


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
