import argparse
import shutil
import sys
from pathlib import Path

from . import __version__
from .util import STAGES, VIDEOS, Pause, find_video, job_dir, log, read_json


def build_parser():
    p = argparse.ArgumentParser(prog="dubber",
                                description="CS50 videolarini oʻzbekcha dublyaj qilish")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--id", help="ish papkasi nomi (videos/<id>); URL dan avtomatik olinadi")
    common.add_argument("--force", action="store_true", help="mavjud natijalarni qayta yaratish")
    common.add_argument("--glossary", type=Path,
                        help="inglizcha soʻzlar glossariysi (default: glossary.json)")
    common.add_argument("--engine", choices=["edge", "mms", "cbx", "omni"], default="edge",
                        help="TTS dvigateli (har biri alohida clips papkasiga yozadi)")
    common.add_argument("--ref-audio", type=Path, help="omni: namuna ovoz fayli (default: videos/ref/OmniVoice.m4a)")
    common.add_argument("--ref-text", help="omni: namuna ovozda aytilgan matn (default: videos/ref/ref_text.txt)")
    common.add_argument("--ss", type=float, default=0, metavar="SEC",
                        help="sinov: shu soniyadan boshlab (tts/mix)")
    common.add_argument("--dur", type=float, metavar="SEC",
                        help="sinov: shuncha soniyalik qism (tts/mix)")
    common.add_argument("--limit", type=int, metavar="N",
                        help="faqat birinchi N segment (tts/mix sinovi uchun)")
    common.add_argument("--src-lang", default="en", help="asl til (default: en)")

    def add_download(x):
        x.add_argument("url", nargs="?", help="YouTube URL")
        x.add_argument("--input", type=Path, help="URL oʻrniga lokal video fayl")
        x.add_argument("--cookies-from-browser", metavar="BROWSER",
                       help="YouTube 'bot emasligingizni tasdiqlang' desa: chrome, safari, firefox...")
        x.add_argument("--cookies", type=Path, help="cookies.txt fayli (yt-dlp uchun)")
        x.add_argument("--quality", type=int, default=720, help="maks. balandlik (default: 720)")

    def add_separate(x):
        x.add_argument("--no-separate", action="store_true", help="demucs ni oʻtkazib yuborish")
        x.add_argument("--demucs-model", default="htdemucs")

    def add_transcribe(x):
        x.add_argument("--source", choices=["auto", "subs", "whisper"], default="auto",
                       help="auto: subtitr bor boʻlsa shuni, yoʻq boʻlsa whisper")
        x.add_argument("--whisper-model", default="small")
        x.add_argument("--max-seg-sec", type=float, default=12.0)
        x.add_argument("--max-seg-chars", type=int, default=260)

    def add_translate(x):
        x.add_argument("--chars-per-sec", type=float, default=14.0,
                       help="oʻzbekcha nutq tezligi, tarjima uzunligi chegarasi")

    def add_tts(x):
        x.add_argument("--gender", choices=["male", "female"], default="male")
        x.add_argument("--script", choices=["auto", "latin", "cyrillic"], default="auto",
                       help="TTS ga beriladigan yozuv (auto: mms kirill, qolganlari lotin)")
        x.add_argument("--voice", help="aniq ovoz nomi (edge), masalan uz-UZ-MadinaNeural")
        x.add_argument("--rate", default="+0%", help="edge tezligi, masalan +10%%")

    def add_mix(x):
        x.add_argument("--max-speed", type=float, default=1.35, help="klipni maks. tezlatish")
        x.add_argument("--duck", type=float, default=-12, help="dublyaj paytida fon dB")
        x.add_argument("--bg-gain", type=float, default=0, help="fon umumiy dB")
        x.add_argument("--voice-gain", type=float, default=0, help="dublyaj ovozi dB")
        x.add_argument("--orig-gain", type=float, default=-20,
                       help="demucs yoʻq boʻlsa asl audio dB")
        x.add_argument("--keep-original", action="store_true", help="asl audio 2-trek sifatida")
        x.add_argument("--subs", action="store_true", help=".srt ham yozish")
        x.add_argument("--out-name", help="outputs/ dagi fayl nomi (.mp4 siz), masalan CS50X-0")

    for name, adders, hlp in [
        ("download", [add_download], "video + subtitr yuklash, audio ajratish"),
        ("separate", [add_separate], "vokal va fonni ajratish (demucs)"),
        ("transcribe", [add_transcribe], "segmentlar (subtitr yoki whisper)"),
        ("translate", [add_translate], "claude_docs/<id>.md ga eksport / .uz.json dan import"),
        ("tts", [add_tts], "oʻzbekcha ovoz klip-klip"),
        ("mix", [add_mix], "aralashtirish va videoga biriktirish"),
    ]:
        x = sub.add_parser(name, parents=[common], help=hlp)
        for a in adders:
            a(x)

    r = sub.add_parser("run", parents=[common], help="butun pipeline")
    for a in (add_download, add_separate, add_transcribe, add_translate, add_tts, add_mix):
        a(r)
    r.add_argument("--from", dest="from_stage", choices=STAGES, default=STAGES[0])
    r.add_argument("--to", dest="to_stage", choices=STAGES, default=STAGES[-1])

    sub.add_parser("status", help="barcha ishlar holati")
    sub.add_parser("voices", help="mavjud oʻzbek edge ovozlari")
    sub.add_parser("check", help="kerakli dasturlarni tekshirish")
    return p


def resolve_job(args):
    vid = args.id
    if not vid and getattr(args, "url", None):
        from .download import resolve_id
        vid = resolve_id(args.url, args)
    if not vid and getattr(args, "input", None):
        vid = args.input.stem
    if not vid:
        sys.exit("xato: --id yoki URL/--input kerak")
    return job_dir(vid)


def stage_fn(name):
    if name == "download":
        from .download import download as f
    elif name == "separate":
        from .separate import separate as f
    elif name == "transcribe":
        from .transcribe import transcribe as f
    elif name == "translate":
        from .translate import translate as f
    elif name == "tts":
        from .tts import tts as f
    else:
        from .mix import mix as f
    return f


def fill_defaults(args):
    """run uchun boshqa subparserlarning default qiymatlari ham bor; yakka buyruqda yoʻq."""
    return args


def status():
    if not VIDEOS.exists():
        return
    for job in sorted(p for p in VIDEOS.iterdir() if p.is_dir()):
        marks = [
            ("video", find_video(job)), ("fon", (job / "no_vocals.wav").exists()),
            ("src", (job / "segments.src.json").exists()),
            ("uz", (job / "segments.uz.json").exists()),
            ("dub", (job / "dub.wav").exists()),
        ]
        extra = ""
        uz = job / "segments.uz.json"
        if uz.exists():
            segs = read_json(uz)
            extra = f"  tarjima {sum(1 for s in segs if s.get('uz'))}/{len(segs)}"
        clips = job / "clips"
        if clips.exists():
            extra += f"  klip {len(list(clips.glob('0*.mp3')))}"
        print(f"{job.name:16} " + " ".join(f"{n}{'✓' if v else '·'}" for n, v in marks) + extra)


def check():
    for tool in ["ffmpeg", "yt-dlp"]:
        print(f"{tool:10} {'OK' if shutil.which(tool) else 'YOʻQ'}")
    for mod in ["pydub", "anthropic", "edge_tts", "faster_whisper", "demucs", "gtts", "transformers"]:
        try:
            __import__(mod)
            ok = "OK"
        except Exception:
            ok = "YOʻQ"
        print(f"{mod:14} {ok}")


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.cmd == "status":
        return status()
    if args.cmd == "voices":
        from .tts import list_voices
        return list_voices()
    if args.cmd == "check":
        return check()
    job = resolve_job(args)
    log(f"ish papkasi: {job}")
    if args.cmd == "run":
        a, b = STAGES.index(args.from_stage), STAGES.index(args.to_stage)
        names = STAGES[a:b + 1]
    else:
        names = [args.cmd]
    for n in names:
        log(f"=== {n} ===")
        try:
            stage_fn(n)(args, job)
        except Pause as e:
            log(str(e))
            return 0
