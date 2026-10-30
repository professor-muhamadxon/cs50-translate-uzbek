"""Chatterbox (UAzimov oʻzbek LoRA) bilan klip-klip sintez.

.venv-cbx ichida ishlaydi (asosiy .venv da emas). dubber `--engine cbx` uni shu yerdan chaqiradi.
Ishlatish: .venv-cbx/bin/python scripts/cbx_tts.py items.json   # [[matn, chiqish.mp3], ...]
"""
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")  # MPS da yoʻq amallar CPU ga tushadi
DEVICE = os.environ.get("CBX_DEVICE", "cpu")  # cpu | mps
ROOT = Path(__file__).resolve().parents[1]
TK = ROOT / "apps/vendor/chatterbox-finetuning"
ADAPTER = ROOT / "apps/vendor/uz-adapter"
sys.path.insert(0, str(TK))
sys.path.insert(0, str(ADAPTER / "scripts"))
os.chdir(TK)  # toolkit konfigi nisbiy yoʻllardan foydalanadi

import soundfile as sf  # noqa: E402
import torch  # noqa: E402
from peft import PeftModel  # noqa: E402
from uz_normalize import normalize_uz  # noqa: E402

from src.chatterbox_.models.t3.t3 import T3  # noqa: E402
from src.chatterbox_.tts import ChatterboxTTS  # noqa: E402
from src.config import TrainConfig  # noqa: E402
from src.model import resize_and_load_t3_weights  # noqa: E402

PARAMS = dict(temperature=0.8, exaggeration=0.5, cfg_weight=0.5, repetition_penalty=2.0)
TRIM_MS = 200  # README: klip boshidagi shovqinni kesish


def load_engine(device=DEVICE):
    cfg = TrainConfig()
    tmp = ChatterboxTTS.from_local(cfg.model_dir, device="cpu")
    hp = tmp.t3.hp
    hp.text_tokens_dict_size = cfg.new_vocab_size
    if hasattr(hp, "use_cache"):
        hp.use_cache = False
    new_t3 = resize_and_load_t3_weights(T3(hp=hp), tmp.t3.state_dict())
    del tmp
    eng = ChatterboxTTS.from_local(cfg.model_dir, device="cpu")
    eng.t3 = new_t3
    eng.t3 = PeftModel.from_pretrained(eng.t3, str(ADAPTER), is_trainable=False)
    eng.t3.to(device).eval()
    eng.s3gen.to(device).eval()
    eng.ve.to(device).eval()
    eng.device = device
    if getattr(eng, "conds", None) is not None:
        eng.conds = eng.conds.to(device)
    return eng


def synth(eng, text):
    text = normalize_uz(text)  # ASCII apostrof + sonlarni soʻzga aylantirish
    parts = [p.strip() for p in re.split(r"(?<=[.!?:;])\s+", text) if p.strip()]
    pieces = []
    for p in parts:
        wav = eng.generate(p, **PARAMS).squeeze(0).cpu().numpy()
        pieces.append(wav[int(eng.sr * TRIM_MS / 1000):])
        pieces.append(torch.zeros(int(eng.sr * 0.12)).numpy())
    return torch.cat([torch.from_numpy(x) for x in pieces]).numpy() if pieces else None


def main():
    items = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    torch.set_num_threads(os.cpu_count() or 4)
    t0 = time.time()
    eng = load_engine()
    print(f"[cbx] model yuklandi ({time.time() - t0:.0f}s), qurilma={DEVICE}, {len(items)} klip", flush=True)
    audio_s = 0.0
    start = time.time()
    for i, (text, out) in enumerate(items, 1):
        t1 = time.time()
        wav = synth(eng, text)
        if wav is None:
            continue
        tmp = Path(out).with_suffix(".wav")
        sf.write(tmp, wav, eng.sr)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp),
                        "-codec:a", "libmp3lame", "-q:a", "4", str(out)], check=True)
        tmp.unlink()
        dur = len(wav) / eng.sr
        audio_s += dur
        el = time.time() - start
        print(f"[cbx] {i}/{len(items)}  {dur:.1f}s audio / {time.time() - t1:.1f}s  "
              f"(jami {audio_s:.0f}s audio, {el:.0f}s, x{el / max(audio_s, 1):.1f} sekin)", flush=True)


if __name__ == "__main__":
    main()
