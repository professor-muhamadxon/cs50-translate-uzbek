"""OmniVoice (k2-fsa) bilan klip-klip sintez. .venv-omni ichida ishlaydi.

dubber `--engine omni` uni shu yerdan chaqiradi. Ovoz doim bir xil boʻlishi uchun
namuna (ref) ovoz kerak: dubber unga Edge klipini beradi (sintetik ovoz, hech kimniki emas).

Ishlatish: .venv-omni/bin/python scripts/omni_tts.py job.json
job.json: {"ref_audio": "...", "ref_text": "...", "items": [["matn", "chiqish.mp3"], ...]}
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import soundfile as sf
import torch
from omnivoice import OmniVoice

DEVICE = os.environ.get("OMNI_DEVICE", "mps")  # mps | cpu
DTYPE = {"fp16": torch.float16, "fp32": torch.float32}[os.environ.get("OMNI_DTYPE", "fp16")]
LANG = os.environ.get("OMNI_LANG", "uz")
STEPS = int(os.environ.get("OMNI_STEPS", "32"))  # 16 = tezroq, sifat biroz pastroq
SR = 24000


def main():
    job = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    ref_wav = Path(job["ref_audio"]).with_suffix(".ref.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", job["ref_audio"],
                    "-ac", "1", "-ar", str(SR), str(ref_wav)], check=True)
    t0 = time.time()
    model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map=DEVICE, dtype=DTYPE)
    prompt = model.create_voice_clone_prompt(ref_audio=str(ref_wav), ref_text=job["ref_text"])
    items = job["items"]
    print(f"[omni] model yuklandi ({time.time() - t0:.0f}s), qurilma={DEVICE}, {len(items)} klip", flush=True)
    audio_s, start = 0.0, time.time()
    for i, (text, out) in enumerate(items, 1):
        t1 = time.time()
        wav = model.generate(text=text, language=LANG, voice_clone_prompt=prompt,
                             num_step=STEPS)[0]
        tmp = Path(out).with_suffix(".wav")
        sf.write(tmp, wav, SR)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp),
                        "-codec:a", "libmp3lame", "-q:a", "4", str(out)], check=True)
        tmp.unlink()
        dur = len(wav) / SR
        audio_s += dur
        el = time.time() - start
        print(f"[omni] {i}/{len(items)}  {dur:.1f}s audio / {time.time() - t1:.1f}s  "
              f"(jami {audio_s:.0f}s audio, {el:.0f}s, x{el / max(audio_s, 1):.2f})", flush=True)
    ref_wav.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
