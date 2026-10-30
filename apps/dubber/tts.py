import asyncio
import re

from .util import clips_dir, load_glossary, log, read_json, select

EDGE_VOICES = {"male": "uz-UZ-SardorNeural", "female": "uz-UZ-MadinaNeural"}

_DIGRAPH = [("sh", "ш"), ("ch", "ч"), ("oʻ", "ў"), ("gʻ", "ғ"), ("o'", "ў"), ("g'", "ғ"),
            ("yo", "ё"), ("yu", "ю"), ("ya", "я"), ("ye", "е")]
_SINGLE = dict(zip("abdefghijklmnopqrstuvxyz", "абдефгҳижклмнопқрстувхйз"))
_SINGLE.update({"q": "қ", "h": "ҳ", "c": "к", "w": "в"})


_WORD = re.compile(r"([A-Za-zʻʼ‘’'`]+)")


def _convert(word):
    t = re.sub(r"[ʻʼ‘’`]", "'", word.lower())
    for a, b in _DIGRAPH:
        t = t.replace(a, b)
    return "".join(_SINGLE.get(ch, ch) for ch in t)


def respell(text, say, key):
    """Glossariydagi inglizcha soʻzlarni ovozga mos yozuvga almashtiradi.
    Qaytaradi: (matn, say dan oʻtgan soʻzlar toʻplami)."""
    low = {k.lower(): v[key] for k, v in say.items() if key in v}
    parts = _WORD.split(text)
    for i in range(1, len(parts), 2):
        if parts[i].lower() in low:
            parts[i] = "\0" + low[parts[i].lower()] + "\0"
    return "".join(parts)


def latin_to_cyrillic(text, say=None):
    """MMS-TTS uchun taxminiy konvertor. say: glossariydagi inglizcha soʻzlar."""
    text = respell(text, say or {}, "cyr")
    out = []
    for i, chunk in enumerate(text.split("\0")):
        out.append(chunk if i % 2 else "".join(
            _convert(p) if _WORD.fullmatch(p) else p for p in _WORD.split(chunk)))
    return "".join(out)


def _edge(args, items):
    import edge_tts
    voice = args.voice or EDGE_VOICES[args.gender]

    async def go():
        sem = asyncio.Semaphore(4)

        async def one(text, path):
            async with sem:
                await edge_tts.Communicate(text, voice, rate=args.rate).save(str(path))
        await asyncio.gather(*(one(t, p) for t, p in items))
    asyncio.run(go())


def _gtts(args, items):
    from gtts import gTTS
    for text, path in items:
        gTTS(text, lang="uz").save(str(path))


def _mms(args, items):
    import scipy.io.wavfile as wav
    import torch
    from transformers import AutoTokenizer, VitsModel
    name = "facebook/mms-tts-uzb-script_cyrillic"
    tok, model = AutoTokenizer.from_pretrained(name), VitsModel.from_pretrained(name)
    for text, path in items:
        inp = tok(text, return_tensors="pt")
        with torch.no_grad():
            wavef = model(**inp).waveform[0].numpy()
        wav.write(str(path.with_suffix(".wav")), model.config.sampling_rate, wavef)
        path.with_suffix(".wav").replace(path)  # mix ffmpeg orqali format aniqlaydi


def _cbx(args, items):
    """Chatterbox oʻzbek LoRA: alohida .venv-cbx muhitida, scripts/cbx_tts.py orqali."""
    import json
    import subprocess
    from .util import ROOT
    tmp = ROOT / "videos" / "_cbx_items.json"
    tmp.write_text(json.dumps([[t, str(p)] for t, p in items], ensure_ascii=False), encoding="utf-8")
    subprocess.run([str(ROOT / ".venv-cbx/bin/python"), str(ROOT / "scripts/cbx_tts.py"), str(tmp)], check=True)


def _omni(args, items):
    """OmniVoice: namuna ovoz (--ref-audio) asosida, .venv-omni da, scripts/omni_tts.py orqali."""
    import json
    import subprocess
    from .util import ROOT
    ref = args.ref_audio or ROOT / "videos/ref/OmniVoice.m4a"
    txt = ROOT / "videos/ref/ref_text.txt"
    ref_text = args.ref_text or (txt.read_text(encoding="utf-8").strip() if txt.exists() else None)
    if not ref.exists() or not ref_text:
        raise RuntimeError("OmniVoice uchun --ref-audio va --ref-text (yoki videos/ref/ref_text.txt) kerak")
    tmp = ROOT / "videos" / "_omni_job.json"
    tmp.write_text(json.dumps({"ref_audio": str(ref), "ref_text": ref_text,
                               "items": [[t, str(p)] for t, p in items]}, ensure_ascii=False),
                   encoding="utf-8")
    subprocess.run([str(ROOT / ".venv-omni/bin/python"), str(ROOT / "scripts/omni_tts.py"), str(tmp)], check=True)


ENGINES = {"edge": _edge, "gtts": _gtts, "mms": _mms, "cbx": _cbx, "omni": _omni}


def prepare(text, args):
    """auto: mms kirill, qolganlari lotin."""
    script = args.script
    if script == "auto":
        script = "cyrillic" if args.engine == "mms" else "latin"
    if args.engine == "mms" and script == "latin":
        log("ogohlantirish: mms kirill yozuvini talab qiladi, kirillga oʻtkazildi")
        script = "cyrillic"
    say = load_glossary(args.glossary).get("say", {})
    if script == "cyrillic":
        return latin_to_cyrillic(text, say)
    return respell(text, say, "lat").replace("\0", "")


def list_voices():
    import edge_tts
    for v in asyncio.run(edge_tts.list_voices()):
        if v["Locale"].startswith("uz"):
            print(f"{v['ShortName']:24} {v['Gender']}")


def tts(args, job):
    segs = select(read_json(job / "segments.uz.json"), args)
    clips = clips_dir(job, args)
    clips.mkdir(exist_ok=True)
    ext = ".mp3"
    items = []
    for s in segs:
        p = clips / f"{s['id']:05d}{ext}"
        if s.get("uz") and (args.force or not p.exists()):
            items.append((prepare(s["uz"], args), p))
    _report_unmapped(segs, args)
    log(f"TTS ({args.engine}): {len(items)} klip")
    if items:
        ENGINES[args.engine](args, items)


def _report_unmapped(segs, args):
    gl = load_glossary(args.glossary)
    say = {k.lower() for k in gl.get("say", {})}
    text = " ".join(s.get("uz", "") for s in segs).lower()
    miss = [w for w in gl.get("keep_english", [])
            if w.lower() not in say and re.search(rf"\\b{re.escape(w.lower())}\\b", text)]
    if miss:
        log(f"glossary 'say' da talaffuzi yoʻq inglizcha soʻzlar: {', '.join(miss)}")
