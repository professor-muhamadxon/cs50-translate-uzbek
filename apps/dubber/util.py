import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VIDEOS = ROOT / "videos"
OUTPUTS = ROOT / "outputs"
GLOSSARY = ROOT / "glossary.json"
DOCS = ROOT / "claude_docs"

STAGES = ["download", "separate", "transcribe", "translate", "tts", "mix"]


def log(msg):
    print(f"[dubber] {msg}", file=sys.stderr, flush=True)


def run(cmd, **kw):
    log("$ " + " ".join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], check=True, **kw)


def job_dir(video_id):
    d = VIDEOS / video_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def find_video(job):
    for p in sorted(job.glob("video.*")):
        if p.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}:
            return p
    return None


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_glossary(path=None):
    p = Path(path) if path else GLOSSARY
    return read_json(p) if p.exists() else {}


def select(segs, args):
    """--limit, --ss, --dur boʻyicha segmentlar tanlovi (sinov qismlari uchun)."""
    segs = segs[:args.limit]
    ss, dur = args.ss or 0, args.dur
    return [s for s in segs if s["start"] >= ss and (dur is None or s["end"] <= ss + dur)]


def clips_dir(job, args):
    eng = getattr(args, "engine", "edge")
    return job / ("clips" if eng == "edge" else f"clips_{eng}")


class Pause(Exception):
    """Pipeline foydalanuvchi/Claude sessiyasini kutish uchun toʻxtaydi."""
