"""Bellwether on two presidents' own press conferences.

    python harness/presidents/run.py            # fetch (cached), measure, write results.json

Why this exists
---------------
The Supreme Court harness shows the engine staying quiet on real speech
nobody here wrote. What it cannot show is the other half: the engine
moving when a real person's speech really changed, on data nobody here
authored. Every positive result before this was a simulated person.

There is a published case. Berisha, Wang, LaCross and Liss (Journal of
Alzheimer's Disease, 2015) compared the presidential press conferences of
Ronald Reagan, diagnosed with Alzheimer's disease in 1994, with those of
George H. W. Bush, who had no such diagnosis, and found Reagan's
vocabulary narrowing and his fillers and non-specific words rising across
his presidency, with no such change in Bush's. The transcripts are public
record on the American Presidency Project at UC Santa Barbara, and each
one labels the president's own words separately from the reporters'
questions, so this is one known speaker's own speech over years: exactly
what the Bee cannot yet give, and exactly what Bellwether is for.

What it does
------------
Fetches every "The President's News Conference" document for each term
(cached under data/, which is not committed), keeps only the paragraphs
spoken by THE PRESIDENT, removes stage directions such as [Laughter],
reduces each conference to the same nine features the product uses, and
runs the same engine with the same defaults. Each conference is one
"day", in date order, which is the same device the Supreme Court harness
uses for sessions.

Two readings are reported for each president, because they answer two
different questions:

  1. The engine, unchanged: what the product would have shown, conference
     by conference, against his own first conferences.
  2. The trend: each feature's least-squares slope per year, and whether
     it moved in the direction the literature associates with decline.
     The engine compares each day with a slowly moving baseline, so a
     change spread over eight years can be absorbed rather than flagged;
     the trend says what happened regardless.

What it is not
--------------
Not a diagnosis, of anyone, and not evidence about dementia in general.
One man's public speaking, in a setting that also changed (staff,
preparation, fewer conferences in later years). It is offered because it
is the best-known real case there is, it is a replication of a published
finding rather than a new claim, and it is the first test of the engine
on a real person whose speech is documented to have changed.
"""

from __future__ import annotations

import html
import json
import re
import statistics
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

from bellwether_engine.baseline import DEFAULT_CONFIG, DIRECTION, assess
from speech_vitals import FEATURE_NAMES, Utterance, aggregate_day

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DATA = HERE / "data"
BASE = "https://www.presidency.ucsb.edu"
UA = {"User-Agent": "Mozilla/5.0 (Bellwether research harness; github.com/usv240/bellwether)"}

TERMS = {
    "reagan": ("Ronald Reagan", date(1981, 1, 20), date(1989, 1, 19)),
    "bush": ("George H. W. Bush", date(1989, 1, 20), date(1993, 1, 19)),
}


def get(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                return res.read().decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            time.sleep(2 + attempt * 3)
    raise SystemExit(f"could not fetch {url}")


def list_conferences(start: date, end: date) -> list[str]:
    """Every news-conference document path in the date range."""
    found: list[str] = []
    for page in range(0, 40):
        q = {
            "field-keywords": "news conference",
            "from[date]": start.strftime("%m-%d-%Y"),
            "to[date]": end.strftime("%m-%d-%Y"),
            "items_per_page": "100",
            "page": str(page),
        }
        body = get(f"{BASE}/advanced-search?" + urllib.parse.urlencode(q))
        links = re.findall(r'href="(/documents/the-presidents-news-conference[^"#?]*)"', body)
        fresh = [l for l in dict.fromkeys(links) if l not in found]
        if not fresh:
            break
        found.extend(fresh)
        time.sleep(0.5)
    return found


# Speaker labels as the transcripts print them: "The President." (or
# "THE PRESIDENT." on older pages), "Q." for a reporter, and the
# occasional named official ("Mr. Speakes.").
LABEL = re.compile(r"^(Q\.|The President\.|THE PRESIDENT\.|(?:Mr|Mrs|Ms|Dr|Secretary|General|Ambassador)\.? [A-Z][A-Za-z'\-]+\.)\s*")
PRESIDENT = {"The President.", "THE PRESIDENT."}


def is_heading(p: str) -> bool:
    """Editors' topic headings ("The National Economy") sit between the
    president's paragraphs. They are short and carry no sentence ending."""
    return len(p.split()) <= 8 and not p.rstrip().endswith((".", "?", "!", '"', "'"))


def parse(doc: str) -> tuple[str | None, str, str]:
    """(iso date, title, the president's own words)."""
    title = html.unescape(re.search(r"<title>(.*?)</title>", doc, re.S).group(1)).split("|")[0].strip()
    m = re.search(r'class="date-display-single"[^>]*content="(\d{4}-\d{2}-\d{2})', doc)
    day = m.group(1) if m else None
    if day is None:
        m = re.search(r'class="date-display-single"[^>]*>([^<]+)<', doc)
        if m:
            try:
                day = datetime.strptime(m.group(1).strip(), "%B %d, %Y").date().isoformat()
            except ValueError:
                day = None
    body = re.search(r'field-docs-content">(.*?)</div>', doc, re.S)
    if not body:
        return day, title, ""
    paras = [html.unescape(re.sub(r"<[^>]+>", " ", p)).strip()
             for p in re.split(r"</p>|<br\s*/?>", body.group(1))]
    speaker = None
    own: list[str] = []
    for p in paras:
        p = re.sub(r"\s+", " ", p).strip()
        if not p:
            continue
        m = LABEL.match(p)
        if m:
            speaker = m.group(1)
            p = p[m.end():]
        p = re.sub(r"\[[^\]]*\]", " ", p).strip()
        if speaker in PRESIDENT and p and not is_heading(p):
            own.append(p)
    return day, title, "\n".join(own)


def fetch(key: str) -> list[dict]:
    name, start, end = TERMS[key]
    DATA.mkdir(parents=True, exist_ok=True)
    listing = DATA / f"{key}-list.json"
    if listing.exists():
        paths = json.loads(listing.read_text(encoding="utf-8"))
    else:
        paths = list_conferences(start, end)
        listing.write_text(json.dumps(paths), encoding="utf-8")
    print(f"{name}: {len(paths)} documents listed")
    raw = DATA / "raw"
    raw.mkdir(exist_ok=True)
    out = []
    for path in paths:
        page = raw / (path.rsplit("/", 1)[-1] + ".html")
        if not page.exists():
            page.write_text(get(BASE + path), encoding="utf-8")
            time.sleep(0.4)
        day, title, text = parse(page.read_text(encoding="utf-8"))
        if not day or not (start.isoformat() <= day <= end.isoformat()):
            continue
        if "news conference" not in title.lower():
            continue
        out.append({"date": day, "title": title, "url": BASE + path, "words": len(text.split()), "text": text})
    out.sort(key=lambda r: r["date"])
    return out


def features(confs: list[dict]):
    rows = []
    for c in confs:
        pieces = [line for line in c["text"].split("\n") if line.strip()]
        utts = [Utterance(ts=f"{c['date']}T12:00:00Z", text=p, speaker="president") for p in pieces]
        rows.append(aggregate_day(utts, date=c["date"]))
    return rows


def slope_per_year(dates: list[str], values: list[float]) -> float:
    xs = [date.fromisoformat(d).toordinal() / 365.25 for d in dates]
    mx, my = statistics.mean(xs), statistics.mean(values)
    den = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, values)) / den if den else 0.0


def analyse(key: str, confs: list[dict]) -> dict:
    name = TERMS[key][0]
    rows = features(confs)
    assessments = assess(rows, DEFAULT_CONFIG)
    scored = [a for a in assessments if a.composite is not None]
    flagged = [a for a in scored if a.tier in ("watch", "discuss")]
    first_flag = flagged[0].date if flagged else None

    eligible = [r for r in rows if r.token_count_day >= DEFAULT_CONFIG.min_tokens]
    trend = {}
    concerning = 0
    for f in FEATURE_NAMES:
        vals = [getattr(r, f) for r in eligible]
        s = slope_per_year([r.date for r in eligible], vals)
        sd = statistics.pstdev(vals) or 1.0
        worse = (s < 0) if DIRECTION[f] == "lower_is_concerning" else (s > 0)
        concerning += worse
        trend[f] = {"slopePerYear": round(s, 4), "slopeInSdPerYear": round(s / sd, 3),
                    "direction": DIRECTION[f], "movedTheConcerningWay": worse}

    half = len(eligible) // 2
    halves = {}
    for f in FEATURE_NAMES:
        a = statistics.mean(getattr(r, f) for r in eligible[:half])
        b = statistics.mean(getattr(r, f) for r in eligible[half:])
        halves[f] = {"firstHalf": round(a, 4), "secondHalf": round(b, 4)}

    # The published study's own measure, pre-specified by them, not chosen
    # here after looking: non-specific nouns per 100 of the president's words.
    nonspec = re.compile(r"(?<![A-Za-z])(thing|things|something|anything|everything|nothing|stuff)(?![A-Za-z])", re.I)
    by_year: dict[str, list[float]] = {}
    for c in confs:
        words = len(c["text"].split())
        if words >= DEFAULT_CONFIG.min_tokens:
            by_year.setdefault(c["date"][:4], []).append(100 * len(nonspec.findall(c["text"])) / words)

    return {
        "publishedMeasureNonSpecificPer100ByYear": {y: round(statistics.mean(v), 2) for y, v in sorted(by_year.items())},
        "publishedMeasureConferencesPerYear": {y: len(v) for y, v in sorted(by_year.items())},
        "speaker": name,
        "conferences": len(confs),
        "assessed": len(scored),
        "excludedLowExposure": sum(1 for a in assessments if not a.eligible),
        "flaggedDays": len(flagged),
        "firstFlag": first_flag,
        "tiers": [{"date": a.date, "tier": a.tier,
                   "composite": None if a.composite is None else round(a.composite, 3),
                   "contributors": list(a.contributors)} for a in assessments],
        "featuresMovingTheConcerningWay": concerning,
        "trend": trend,
        "halves": halves,
        "wordsPerConference": round(statistics.mean(c["words"] for c in confs), 1) if confs else 0,
    }


def main() -> int:
    results = {}
    for key in TERMS:
        confs = [c for c in fetch(key) if c["words"] > 0]
        results[key] = analyse(key, confs)
        r = results[key]
        print(f"\n{r['speaker']}: {r['conferences']} conferences, {r['assessed']} assessed, "
              f"{r['flaggedDays']} flagged, first flag {r['firstFlag']}, "
              f"{r['featuresMovingTheConcerningWay']} of 9 features trending the concerning way")
        for f, t in r["trend"].items():
            print(f"   {f:20} {t['slopeInSdPerYear']:+.3f} sd/yr  {'concerning' if t['movedTheConcerningWay'] else ''}")
    out = {
        "source": "The American Presidency Project, UC Santa Barbara (presidency.ucsb.edu); public record",
        "replicates": "Berisha V, Wang S, LaCross A, Liss J. Tracking discourse complexity preceding Alzheimer's disease diagnosis: a case study comparing the press conferences of Presidents Ronald Reagan and George Herbert Walker Bush. J Alzheimers Dis. 2015;45(3):959-963.",
        "engine": "DEFAULT_CONFIG, unchanged; one conference is one day, in date order",
        "notADiagnosis": "A replication of a published finding about public speech, not a diagnosis of anyone.",
        "results": results,
    }
    (HERE / "results.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {HERE / 'results.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
