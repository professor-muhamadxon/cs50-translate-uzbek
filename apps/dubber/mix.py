import subprocess

import numpy as np

from .util import OUTPUTS, clips_dir, find_video, log, read_json, run, select

SR = 24000  # ishchi namuna chastotasi: 2 soatlik videoni xotiraga sigʻdirish uchun


def _clip(path, tempo=None):
    af = ["-filter:a", f"atempo={tempo:.3f}"] if tempo else []
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), *af,
                          "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(out, dtype=np.float32)


def mix(args, job):
    segs = [s for s in select(read_json(job / "segments.uz.json"), args) if s.get("uz")]
    ss = args.ss or 0
    partial = bool(args.limit or args.dur or ss)
    nov = job / "no_vocals.wav"
    src = nov if nov.exists() else job / "audio.wav"
    bg_db = args.bg_gain if nov.exists() else args.orig_gain
    end_s = None
    if args.dur:
        end_s = args.dur
    elif args.limit:
        end_s = segs[-1]["end"] + 2 - ss

    raw = job / "_bg.f32"
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    if ss:
        cmd += ["-ss", f"{ss:.2f}"]
    if end_s:
        cmd += ["-t", f"{end_s:.2f}"]
    run(cmd + ["-i", src, "-f", "f32le", "-ac", "2", "-ar", str(SR), raw])
    bg = np.fromfile(raw, dtype=np.float32).reshape(-1, 2)
    total = len(bg)
    bg *= 10 ** (bg_db / 20)

    env = np.ones(total, dtype=np.float32)   # fon balandligi (dublyaj paytida pasayadi)
    dub = np.zeros(total, dtype=np.float32)
    duck = 10 ** (args.duck / 20)
    ramp = int(0.15 * SR)
    clips = clips_dir(job, args)
    over = placed = 0
    for i, s in enumerate(segs):
        p = clips / f"{s['id']:05d}.mp3"
        start = int((s["start"] - ss) * SR)
        if not p.exists() or start >= total:
            continue
        clip = _clip(p)
        nxt = int((segs[i + 1]["start"] - ss) * SR) if i + 1 < len(segs) else total
        slot = max(nxt - start, 1)
        factor = len(clip) / slot
        if factor > 1.03:
            clip = _clip(p, min(factor, args.max_speed))
            if len(clip) > slot:
                over += 1
                log(f"segment {s['id']}: {(len(clip) - slot) * 1000 // SR} ms oshib ketdi")
        placed += 1
        n = min(len(clip), total - start)
        dub[start:start + n] += clip[:n]
        a, b = max(start - ramp, 0), min(start + n + ramp, total)
        e = np.full(b - a, duck, dtype=np.float32)
        r1, r2 = start - a, b - (start + n)
        if r1 > 0:
            e[:r1] = np.linspace(1, duck, r1, dtype=np.float32)
        if r2 > 0:
            e[-r2:] = np.linspace(duck, 1, r2, dtype=np.float32)
        np.minimum(env[a:b], e, out=env[a:b])
    if not placed:
        raise RuntimeError(f"{clips} ichida ovoz klipi yoʻq; avval `tts --engine {args.engine}` ni ishga tushiring")
    log(f"{len(segs)} segment, {over} tasi vaqtdan oshdi")

    bg *= env[:, None]
    dub *= 10 ** (args.voice_gain / 20)
    bg += dub[:, None]
    np.clip(bg, -1, 1, out=bg)
    mixed = job / "_mix.f32"
    bg.tofile(mixed)
    del bg, env, dub

    video = find_video(job)
    OUTPUTS.mkdir(exist_ok=True)
    tag = ".test" if partial else ""
    name = args.out_name or f"{job.name}.uz{tag}"
    target = OUTPUTS / f"{name}.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    if ss:
        cmd += ["-ss", f"{ss:.2f}"]
    if end_s:
        cmd += ["-t", f"{end_s:.2f}"]
    cmd += ["-i", video,
           "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", mixed,
           "-map", "0:v", "-map", "1:a"]
    if args.keep_original:
        cmd += ["-map", "0:a?"]
    vcodec = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23"] if partial else ["-c:v", "copy"]
    cmd += [*vcodec, "-c:a", "aac", "-b:a", "192k",
            "-metadata:s:a:0", "language=uzb", "-metadata:s:a:0", "title=Oʻzbekcha",
            "-shortest", target]
    run(cmd)
    raw.unlink(missing_ok=True)
    mixed.unlink(missing_ok=True)
    if args.subs:
        (OUTPUTS / f"{name}.srt").write_text(_srt(segs, ss), encoding="utf-8")
    log(f"tayyor: {target}")


def _ts(t):
    ms = int(t * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def _srt(segs, ss=0):
    return "\n".join(f"{i}\n{_ts(s['start'] - ss)} --> {_ts(s['end'] - ss)}\n{s['uz']}\n"
                     for i, s in enumerate(segs, 1))
