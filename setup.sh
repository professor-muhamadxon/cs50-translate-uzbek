#!/bin/zsh
# Bir martalik oʻrnatish: .venv (Python 3.12) + bogʻliqliklar + ffmpeg/yt-dlp
set -e
cd "$(dirname "$0")"
for t in ffmpeg yt-dlp; do
  command -v $t >/dev/null || brew install $t
done
[ -d .venv ] || /opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r apps/dubber/requirements.txt
echo "Tayyor. Tekshirish: ./dub check"
