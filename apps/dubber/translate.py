import json

from .util import DOCS, Pause, load_glossary, log, read_json, write_json

RULES = """\
## Tarjima qoidalari
- Inglizchadan oʻzbekchaga (lotin), ovoz chiqarib oʻqiladigan tabiiy ogʻzaki nutq.
- oʻ, gʻ — modifier harf ʻ (U+02BB); tutuq belgisi ʼ (U+02BC).
- Texnik terminlar va kod nomlari (funksiya, buyruq, fayl nomi) inglizcha qoladi: {keep}.
- Raqam va belgilarni TTS toʻgʻri oʻqishi uchun soʻz bilan yozing.
- Har segment `max` belgidan oshmasin (nutq vaqtiga sigʻishi uchun), maʼnoni saqlab qisqartiring.

## Natija
`claude_docs/{id}.uz.json` fayliga: {{"<segment id>": "oʻzbekcha matn", ...}}
Keyin: `./dub translate --id {id}`
"""


def _info(job):
    f = job / "video.info.json"
    if not f.exists():
        return {}
    d = read_json(f)
    return {k: d.get(k) for k in ("title", "uploader", "webpage_url", "description", "duration")}


def export(args, job, segs):
    gl = load_glossary(args.glossary)
    info = _info(job)
    DOCS.mkdir(exist_ok=True)
    out = DOCS / f"{job.name}.md"
    lines = [f"# {info.get('title') or job.name}", "",
             f"- id: `{job.name}`",
             f"- manba: {info.get('webpage_url', '-')}",
             f"- kanal: {info.get('uploader', '-')}",
             f"- davomiyligi: {info.get('duration', '-')} s",
             "", "## Video tavsifi", "", (info.get("description") or "-")[:1500], "",
             RULES.format(keep=", ".join(gl.get("keep_english", [])), id=job.name),
             "## Segmentlar", "", "Format: `[id] (boshlanish–tugash s, max=belgi) matn`", ""]
    for s in segs:
        mx = max(20, int((s["end"] - s["start"]) * args.chars_per_sec))
        lines.append(f"[{s['id']}] ({s['start']}–{s['end']}, max={mx}) {s['en']}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def translate(args, job):
    src = job / "segments.src.json"
    if not src.exists():
        raise RuntimeError("avval transcribe bosqichini bajaring")
    segs = read_json(src)
    res = DOCS / f"{job.name}.uz.json"
    if not res.exists():
        doc = export(args, job, segs)
        raise Pause(f"eksport qilindi: {doc}\nTarjimani {res.name} ga yozing, "
                    f"soʻng qayta ishga tushiring.")
    uz = {str(k): v for k, v in json.loads(res.read_text(encoding="utf-8")).items()}
    missing = [s["id"] for s in segs if not uz.get(str(s["id"]), "").strip()]
    for s in segs:
        s["uz"] = uz.get(str(s["id"]), "").strip()
    write_json(job / "segments.uz.json", segs)
    log(f"import: {len(segs) - len(missing)}/{len(segs)} segment"
        + (f", yetishmayotgan idlar: {missing[:20]}" if missing else ""))
