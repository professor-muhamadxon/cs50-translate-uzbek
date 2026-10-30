import shutil
import sys

from .util import log, run


def separate(args, job):
    out = job / "no_vocals.wav"
    if out.exists() and not args.force:
        log("no_vocals.wav bor, o'tkazib yuborildi")
        return
    if args.no_separate:
        log("--no-separate: fon ajratilmaydi, asl audio past ovozda qoladi")
        return
    run([sys.executable, "-m", "demucs", "--two-stems=vocals", "-n", args.demucs_model,
         "-o", job / "demucs", job / "audio.wav"])
    found = list((job / "demucs").rglob("no_vocals.wav"))
    if not found:
        raise RuntimeError("demucs natijasi topilmadi")
    shutil.move(found[0], out)
    shutil.rmtree(job / "demucs", ignore_errors=True)
