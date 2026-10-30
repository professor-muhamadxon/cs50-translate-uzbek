import re

from .util import log, read_json, write_json

TS = re.compile(r"(\d+):(\d+):(\d+)[.,](\d+) --> (\d+):(\d+):(\d+)[.,](\d+)")


def _sec(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")[:3]) / 1000


def parse_vtt(path):
    cues, cur = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = TS.search(line)
        if m:
            g = m.groups()
            cur = {"start": _sec(*g[:4]), "end": _sec(*g[4:]), "text": ""}
            cues.append(cur)
        elif cur is not None and line.strip() and not line.startswith(("WEBVTT", "NOTE")):
            t = re.sub(r"<[^>]+>", "", line).strip()
            if t:
                cur["text"] = (cur["text"] + " " + t).strip()
    out = []
    for c in cues:  # YouTube auto-captions takrorlanadi
        if not c["text"]:
            continue
        if out and c["text"] == out[-1]["text"]:
            out[-1]["end"] = c["end"]
        elif out and c["text"].startswith(out[-1]["text"]):
            out[-1].update(text=c["text"], end=c["end"])
        else:
            out.append(c)
    return out


def merge(cues, max_dur, max_chars):
    segs, buf = [], None
    for c in cues:
        if buf is None:
            buf = dict(c)
        else:
            buf["text"] += " " + c["text"]
            buf["end"] = c["end"]
        done = (buf["text"].rstrip().endswith((".", "?", "!"))
                or buf["end"] - buf["start"] >= max_dur
                or len(buf["text"]) >= max_chars)
        if done:
            segs.append(buf)
            buf = None
    if buf:
        segs.append(buf)
    return [{"id": i, "start": round(s["start"], 2), "end": round(s["end"], 2),
             "en": s["text"].strip()} for i, s in enumerate(segs)]


def whisper_cues(args, job):
    from faster_whisper import WhisperModel
    model = WhisperModel(args.whisper_model, compute_type="int8")
    segs, _ = model.transcribe(str(job / "audio.wav"), language=args.src_lang,
                               vad_filter=True)
    return [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segs]


def transcribe(args, job):
    out = job / "segments.src.json"
    if out.exists() and not args.force:
        log("segments.src.json bor, o'tkazib yuborildi")
        return
    vtts = sorted(job.glob("video*.vtt"))
    if args.source == "subs" or (args.source == "auto" and vtts):
        if not vtts:
            raise RuntimeError("subtitr topilmadi; --source whisper ishlating")
        log(f"subtitr: {vtts[0].name}")
        cues = parse_vtt(vtts[0])
    else:
        log(f"whisper ({args.whisper_model}) ishlamoqda...")
        cues = whisper_cues(args, job)
    segs = merge(cues, args.max_seg_sec, args.max_seg_chars)
    write_json(out, segs)
    log(f"{len(segs)} segment")
