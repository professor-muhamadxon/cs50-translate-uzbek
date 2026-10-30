import shutil
import subprocess

from .util import find_video, job_dir, log, run


def auth_args(args):
    if getattr(args, "cookies_from_browser", None):
        return ["--cookies-from-browser", args.cookies_from_browser]
    if getattr(args, "cookies", None):
        return ["--cookies", str(args.cookies)]
    return []


def resolve_id(url, args=None):
    out = subprocess.run(["yt-dlp", "--get-id", "--no-playlist", "--socket-timeout", "60",
                          "--extractor-retries", "5", *auth_args(args), url],
                         check=True, stdout=subprocess.PIPE, text=True)
    return out.stdout.strip().splitlines()[0]


def _ytdlp(args, job):
    h = args.quality
    run(["yt-dlp", "--no-playlist", "--socket-timeout", "60", "--retries", "5",
         "-f", f"bv*[height<={h}]+ba/b[height<={h}]",
         "--merge-output-format", "mp4",
         "-o", job / "video.%(ext)s",
         "--write-info-json", "--write-subs", "--write-auto-subs",
         "--sub-langs", args.src_lang, "--sub-format", "vtt",
         *auth_args(args),
         args.url])


def download(args, job):
    if find_video(job) and not args.force:
        log("video bor, o'tkazib yuborildi")
    elif args.input:
        shutil.copy(args.input, job / f"video{args.input.suffix}")
    else:
        try:
            _ytdlp(args, job)
        except subprocess.CalledProcessError:
            if not find_video(job):
                raise
            log("ogohlantirish: video yuklandi, lekin subtitr/boshqa qism xato berdi; davom etamiz")
    video = find_video(job)
    audio = job / "audio.wav"
    if not audio.exists() or args.force:
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-vn",
             "-ac", "2", "-ar", "44100", audio])
