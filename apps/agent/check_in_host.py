"""The Check-in Host: a voice assistant runs the two-minute check-in.

    python apps/agent/check_in_host.py --profile me            # speak tonight's script
    python apps/agent/check_in_host.py --profile me --count    # then wait for the Bee and count the day
    python apps/agent/check_in_host.py --dry-run               # print what would be said

What happens, in order, across three devices and one service:

  1. The host asks Bellwether's MCP server for tonight's script with the
     ``start_check_in`` tool: an opener that declares the session a
     check-in, three standard elicitation prompts, and a closing. The same
     tool Alexa+ would call.
  2. It speaks each line through the speaker (Amazon Polly) and waits for
     the wearer to answer. The Bee on the wearer's wrist records the whole
     exchange as one session, host and wearer alike.
  3. With ``--count`` it waits for the Bee to write the session down, then
     runs ``bellwether-ingest mine --days 1`` on this computer, which
     anchors the session on the host's opener, removes every line the
     host spoke, reduces the wearer's answers to nine numbers and sends
     only those.
  4. It asks the ``coaching_note`` tool where the person stands, and says
     it: day three of seven, or the last day fell under the floor and why,
     or what moved and the one thing to do about it.

Why a stand-in for Alexa+: the Alexa+ MCP connection is not open to
developers to drive from a script, so this host reads the tool output
aloud itself, through Polly, using exactly the tools an Alexa+ agent gets.
Nothing here reads a transcript. The host never sees a word the wearer
said; it only hears the count come back.

Every line spoken is appended to ``.bellwether-host.json`` next to the
wearer's key, so the ingest can strip anything a host said beyond the
day's standard script. The standard script itself needs no file: both
sides derive it from the date.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
import urllib.request
import wave
from datetime import date, datetime
from pathlib import Path

DEFAULT_MCP_URL = os.environ.get("BELLWETHER_MCP", "https://bppni6dpuntpbynfydk52gexue0xulzh.lambda-url.us-east-1.on.aws/mcp")
HOST_FILE = ".bellwether-host.json"
HOST_NAME = "check-in-host"
MCP_PROTOCOL_VERSION = "2025-11-25"
NUMBER_WORDS = ["zero", "one", "two", "three"]


# ---- the MCP client: initialize, then tools/call, nothing else -------------


class McpHttp:
    """The smallest Streamable HTTP client that can hold a session."""

    def __init__(self, url: str):
        self.url = url
        self.session_id: str | None = None
        self._id = 0

    def _post(self, body: dict) -> tuple[dict, dict]:
        headers = {"content-type": "application/json", "mcp-protocol-version": MCP_PROTOCOL_VERSION}
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        req = urllib.request.Request(self.url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=60) as res:
            return json.loads(res.read() or b"{}"), {k.lower(): v for k, v in res.headers.items()}

    def _rpc(self, method: str, params: dict | None = None) -> dict:
        self._id += 1
        body, headers = self._post({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}})
        if "mcp-session-id" in headers:
            self.session_id = headers["mcp-session-id"]
        if "error" in body:
            raise RuntimeError(f"{method}: {body['error'].get('message')}")
        return body.get("result", {})

    def initialize(self) -> dict:
        return self._rpc("initialize", {"protocolVersion": MCP_PROTOCOL_VERSION, "capabilities": {},
                                        "clientInfo": {"name": HOST_NAME, "version": "0.1.0"}})

    def call(self, name: str, args: dict | None = None) -> dict:
        res = self._rpc("tools/call", {"name": name, "arguments": args or {}})
        return json.loads(res["content"][0]["text"])


# ---- the speaker -----------------------------------------------------------


class PollySpeaker:
    """Amazon Polly to PCM, then the platform's own player. No ffmpeg."""

    def __init__(self, voice: str = "Joanna", out_dir: Path | None = None):
        import boto3  # lazy: the dry run and the tests need no AWS

        self.polly = boto3.client("polly", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        self.voice = voice
        self.out = out_dir or Path(os.environ.get("TEMP", "/tmp")) / "bellwether-host"
        self.out.mkdir(parents=True, exist_ok=True)
        self._n = 0

    def say(self, text: str) -> tuple[float, float]:
        """Speak one line. Returns when playback began and ended, by this
        computer's clock, so the ingest can drop what the band heard from
        the speaker however it transcribed it."""
        # Printed as well as spoken, so a recording of the terminal shows
        # what the room heard.
        print(f"  host: {text}", flush=True)
        self._n += 1
        res = self.polly.synthesize_speech(Text=text, OutputFormat="pcm", SampleRate="16000",
                                           VoiceId=self.voice, Engine="neural")
        pcm = res["AudioStream"].read()
        path = self.out / f"line-{self._n:02d}.wav"
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(pcm)
        began = time.time()
        _play(path)
        return began, began + len(pcm) / 32000


def _play(path: Path) -> None:
    system = platform.system()
    if system == "Windows":
        import winsound

        winsound.PlaySound(str(path), winsound.SND_FILENAME)
    elif system == "Darwin":
        subprocess.run(["afplay", str(path)], check=False)
    else:
        subprocess.run(["aplay", "-q", str(path)], check=False)


class PrintSpeaker:
    """The dry run: the lines, and nothing through the speaker."""

    def say(self, text: str) -> tuple[float, float]:
        print(f"  host: {text}")
        now = time.time()
        return now, now


# ---- the host file ---------------------------------------------------------


def record_spoken(path: str, day: str, lines: list) -> None:
    """Append what the host said. Each entry is a line, or a dict with the
    line and when it played ({"text", "start", "end"}, epoch seconds)."""
    data: dict = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh) or {}
        except (OSError, ValueError):
            data = {}
    data.setdefault(day, [])
    for line in lines:
        if line not in data[day]:
            data[day].append(line)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1)


# ---- the check-in itself ---------------------------------------------------


def run_check_in(mcp, speaker, profile: str, day: str, wait, answer_seconds: int | None = None,
                 host_file: str = HOST_FILE, log=print) -> dict:
    """Speak tonight's script and wait for the answers. Returns the start
    payload with the lines actually spoken under ``spoken``. Pure of
    devices: ``mcp`` has ``call``, ``speaker`` has ``say``, ``wait`` takes
    seconds; the tests pass fakes."""
    start = mcp.call("start_check_in", {"profile_id": profile, "host": HOST_NAME, "date": day})
    seconds = answer_seconds or int(start.get("answer_seconds") or 45)
    spoken: list[str] = []

    def say(line: str) -> None:
        when = speaker.say(line)
        spoken.append(line)
        if isinstance(when, tuple) and len(when) == 2:
            record_spoken(host_file, day, [{"text": line, "start": round(when[0], 3), "end": round(when[1], 3)}])
        else:
            record_spoken(host_file, day, [line])

    log(f"Day {start.get('eligible_days', 0)} of {start.get('warmup_days', 7)} counted before tonight.")
    if start.get("already_started_today"):
        at = start["already_started_today"].get("at", "")
        log(f"A check-in was already started today at {at}; this one adds to the day.")
        say("You already checked in today. Here is another one, and it counts too.")

    say(start["opener"])
    for i, prompt in enumerate(start["prompts"], start=1):
        say(f"Question {NUMBER_WORDS[i]}.")
        say(prompt["text"])
        log(f"  you answer, {seconds} seconds; the Bee on your wrist is recording")
        wait(seconds)
    say(start["closing"])
    return {**start, "spoken": spoken}


def wait_for_the_bee(started_at: float, poll=None, every: int = 60, limit: int = 30 * 60, clock=time.time, sleep=time.sleep,
                     log=print) -> dict | None:
    """The Bee writes a session down minutes after it ends. Watch the
    conversation list for a session that began around the check-in and
    whose utterance count has stopped growing. Counts only; no text is
    read here."""
    poll = poll or _bee_recent
    seen: dict[str, int] = {}
    announced = False
    deadline = clock() + limit
    while clock() < deadline:
        for conv in poll():
            start_ms = conv.get("start_time")
            if not isinstance(start_ms, (int, float)):
                continue
            if started_at - 180 <= start_ms / 1000 <= started_at + 420:
                cid, n = str(conv.get("id")), int(conv.get("utterances_count") or 0)
                # A session the device is still capturing is not done, however
                # still its count looks: on 2026-10-19 the wearer went on
                # talking after the closing and the session stayed open.
                done = str(conv.get("state") or "COMPLETED").upper() != "CAPTURING"
                if n >= 4 and done and seen.get(cid) == n:
                    log(f"The Bee recorded the check-in: {n} utterances. Counting it now, on this computer.")
                    return conv
                seen[cid] = n
        if not announced:
            log("Waiting for the Bee to finish writing the session down.")
            announced = True
        sleep(every)
    if seen:
        log(f"A session began but was still growing at {max(seen.values())} utterances after the wait.")
    else:
        log("No session began on the Bee around the check-in. Is the band on, and close enough to hear the speaker and you?")
    return None


def _bee_recent() -> list[dict]:
    proc = subprocess.run("bee conversations list --limit 5 --json", shell=True, capture_output=True)
    try:
        data = json.loads(proc.stdout.decode("utf-8", "replace"))
    except ValueError:
        return []
    rows = data.get("conversations") if isinstance(data, dict) else data
    return [r for r in rows or [] if isinstance(r, dict)]


def count_the_day(profile_base: str, log=print) -> int:
    """``bellwether-ingest mine --days 1``: the words are reduced to numbers
    on this computer; its output is counts and a link, never speech."""
    cmd = [*_ingest_command(), "mine", "--days", "1", "--profile", profile_base]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    for line in (proc.stdout + proc.stderr).splitlines():
        log(f"  {line}")
    return proc.returncode


def _ingest_command() -> list[str]:
    """The project's own ``bellwether-ingest`` when it is installed in the
    repository's virtual environment, then one on PATH, then this Python.
    The host may run under a different interpreter from the ingest."""
    import shutil

    repo = Path(__file__).resolve().parents[2]
    for venv in (repo / ".venv" / "Scripts" / "bellwether-ingest.exe", repo / ".venv" / "bin" / "bellwether-ingest"):
        if venv.exists():
            return [str(venv)]
    found = shutil.which("bellwether-ingest")
    return [found] if found else [sys.executable, "-m", "bellwether_ingest.cli"]


def speak_coaching(mcp, speaker, profile: str, log=print) -> dict:
    note = mcp.call("coaching_note", {"profile_id": profile})
    text = " ".join([note.get("text", "")] + list(note.get("actions") or []))
    log(f"Coaching note: {text}")
    speaker.say(text)
    return note


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="A voice assistant hosts the Bellwether check-in")
    parser.add_argument("--url", default=DEFAULT_MCP_URL, help="Bellwether MCP endpoint")
    parser.add_argument("--profile", default=os.environ.get("BELLWETHER_PROFILE", "me"),
                        help="your profile name; check-ins go to <name>-voice, as `mine` does")
    parser.add_argument("--voice", default="Joanna", help="Polly voice for the host")
    parser.add_argument("--answer-seconds", type=int, default=None, help="how long to listen after each prompt")
    parser.add_argument("--count", action="store_true", help="wait for the Bee, then count the day and read the coaching note")
    parser.add_argument("--dry-run", action="store_true", help="print the lines instead of speaking them")
    parser.add_argument("--host-file", default=HOST_FILE)
    args = parser.parse_args(argv)

    voice_profile = f"{args.profile}-voice"
    day = date.today().isoformat()
    speaker = PrintSpeaker() if args.dry_run else PollySpeaker(args.voice)
    mcp = McpHttp(args.url)
    mcp.initialize()
    print(f"Connected to {args.url} as {HOST_NAME}; {datetime.now():%H:%M} on {day}; profile {voice_profile}")

    started_at = time.time()
    wait = (lambda s: None) if args.dry_run else _countdown
    run_check_in(mcp, speaker, voice_profile, day, wait, args.answer_seconds, host_file=args.host_file)

    if not args.count:
        print("Said. When the Bee has written it down, run: bellwether-ingest mine --days 1")
        return 0
    if args.dry_run:
        print("Dry run: not waiting for the Bee.")
        return 0
    if wait_for_the_bee(started_at) is None:
        print("The Bee had not written the session down after thirty minutes. Run: bellwether-ingest mine --days 1 later.")
        return 2
    rc = count_the_day(args.profile)
    if rc != 0:
        print(f"mine returned {rc}; the coaching note reflects what is on the service.")
    speak_coaching(mcp, speaker, voice_profile)
    return 0


def _countdown(seconds: int) -> None:
    """A live countdown on a terminal; a single line when the output is
    captured, so a recording of this run reads cleanly."""
    if not sys.stdout.isatty():
        time.sleep(seconds)
        return
    for left in range(seconds, 0, -1):
        print(f"\r  listening {left:3d}s ", end="", flush=True)
        time.sleep(1)
    print("\r" + " " * 24 + "\r", end="", flush=True)


if __name__ == "__main__":
    sys.exit(main())
