# cs50-translate-uzbek

CS50 ma'ruza videolarini oʻzbekcha ovozli (dublyaj) videoga aylantiruvchi buyruq satri dasturi. Video yuklanadi, nutq va fon ajratiladi, inglizcha matn olinadi, tarjima qilinadi, oʻzbekcha ovoz yaratiladi va asl fon bilan birlashtirib videoga biriktiriladi.

> Loyiha CS50x Lecture 0 (2 soat) misolida ishlab chiqilgan va sinalgan. Tarjima va ovoz sun'iy intellekt yordamida yaratiladi, shuning uchun nashrdan oldin odam tekshirib chiqishi kerak.

## Imkoniyatlar

- Oltita bosqichli pipeline: `download` → `separate` → `transcribe` → `translate` → `tts` → `mix`.
- Har bosqich natijasini saqlaydi: uzilsa, qolgan joyidan davom etadi.
- Fon (musiqa, xona shovqini) saqlanadi, dublyaj paytida u avtomatik pasayadi.
- Ovoz dvigatelini tanlash mumkin: Edge TTS, Meta MMS, Chatterbox, OmniVoice.
- Inglizcha texnik terminlar uchun glossariy (`glossary.json`): tarjimada inglizcha qoladi, ovozda esa belgilangan talaffuz bilan aytiladi.
- Subtitr (`.srt`) yoziladi, ovoz segmentga sigʻmasa tezlashtiriladi.
- Tarjima uchun API kalit kerak emas: matn fayl orqali beriladi va tayyor tarjima fayldan olinadi.

## Qanday ishlaydi

| # | Bosqich | Nima qiladi | Vosita |
| --- | --- | --- | --- |
| 1 | `download` | Video, subtitr va audioni yuklaydi | yt-dlp, ffmpeg |
| 2 | `separate` | Nutq va fonni ajratadi | demucs |
| 3 | `transcribe` | Inglizcha matnni segmentlarga boʻladi | YouTube subtitri yoki faster-whisper |
| 4 | `translate` | Matnni eksport qiladi va tayyor tarjimani import qiladi | siz, Claude yoki boshqa tarjimon |
| 5 | `tts` | Har segment uchun oʻzbekcha ovoz yaratadi | edge-tts, MMS, Chatterbox, OmniVoice |
| 6 | `mix` | Fon bilan ovozni aralashtirib, videoga biriktiradi | numpy, ffmpeg |

## Oʻrnatish

macOS (Apple Silicon) da sinalgan. Python 3.12 va Homebrew kerak.

```bash
git clone https://github.com/professor-muhamadxon/cs50-translate-uzbek.git
cd cs50-translate-uzbek
./setup.sh
./dub check
```

`setup.sh` `.venv` muhitini yaratadi, `ffmpeg` va `yt-dlp` ni (Homebrew orqali) oʻrnatadi. `./dub check` hamma asbob oʻrnatilganini koʻrsatadi.

## Tez boshlash

```bash
# 1. yuklash, fonni ajratish, matn olish (tarjimada oʻzi toʻxtaydi)
./dub run "https://youtu.be/VIDEO_ID" --quality 480

# 2. claude_docs/<ID>.md ni tarjima qilib, claude_docs/<ID>.uz.json ga yozing

# 3. 5 daqiqalik sinov
./dub tts --id <ID> --ss 125 --dur 300
./dub mix --id <ID> --ss 125 --dur 300 --out-name sinov --subs

# 4. yaxshi boʻlsa, butun video
./dub run --id <ID> --from translate --out-name CS50X-0 --subs

# istalgan payt holatni koʻrish
./dub status
```

YouTube "bot emasligingizni tasdiqlang" desa, `--cookies-from-browser chrome` (yoki `safari`, `firefox`) qoʻshing. Video oʻzingizda boʻlsa: `./dub run --input fayl.mp4 --id nom --source whisper`.

Barcha parametrlar: `./dub run --help`.

## Tarjima bosqichi

1. `./dub translate --id <ID>` buyrugʻi `claude_docs/<ID>.md` faylini yaratadi: video haqida maʼlumot, tarjima qoidalari va har segment `[id] (vaqt, max=belgi) matn` koʻrinishida.
2. Tarjimani `claude_docs/<ID>.uz.json` fayliga yozing:

```json
{
  "0": "Salom, bu CS50.",
  "1": "Bugun nolinchi hafta."
}
```

3. `./dub run --id <ID> --from translate` tarjimani import qiladi va ovoz hamda videoga oʻtadi.

Tarjimani Claude, boshqa AI yoki inson qilishi mumkin. `max=` chegarasiga yaqin turing: matn uzun boʻlsa, ovoz segmentdan oshadi. Imloda `oʻ`, `gʻ` va `ʼ` belgilarini ishlating.

## Ovoz dvigatellari

Sinov: CS50x Lecture 0, 125-soniyadan 5 daqiqa (67 segment), Apple M4. "Vaqtdan oshgan" ustuni ovoz oʻz segmentiga sigʻmaganini bildiradi. Bu sigʻishni oʻlchaydi, ovoz sifatini emas.

| Dvigatel (`--engine`) | Qayerda ishlaydi | Vaqtdan oshgan | Tezlik | Eslatma |
| --- | --- | --- | --- | --- |
| `edge` | internet (Microsoft) | 11 / 67 | eng tez | Standart. Butun videoni yaratgan yagona dvigatel |
| `mms` | kompyuterda | 30 / 67 | oʻrtacha | Faqat kirill yozuvi, lotindan avtomatik oʻtkaziladi. Litsenziya CC-BY-NC |
| `cbx` (Chatterbox) | kompyuterda (Apple GPU) | 5 / 67 | real vaqtdan ~4,9 baravar sekin | Qoʻshimcha oʻrnatish va ~4–5 GB fayl kerak |
| `omni` (OmniVoice) | kompyuterda (Apple GPU) | 11 / 67 | real vaqtdan ~6,5 baravar sekin, har klipga ~25–30 s | Namuna ovoz kerak, model litsenziyasi CC-BY-NC |

- gTTS oʻzbek tilini qoʻllamaydi.
- Ovoz tabiiyligi, ravonligi va inglizcha soʻzlar talaffuzi bu hujjatda eshitib baholanmagan. Tanlashdan oldin 5 daqiqalik sinov qilib, quloq bilan solishtiring.
- `cbx` va `omni` alohida muhit talab qiladi (`.venv-cbx`, `.venv-omni`) va uchinchi tomon kodini/modelini yuklaydi. Ularni oʻrnatish `setup.sh` ga kirmaydi; `scripts/cbx_tts.py` va `scripts/omni_tts.py` fayllarining boshidagi izohlarga qarang.
- OmniVoice va Chatterbox namuna ovoz bilan klonlay oladi. **Faqat oʻz ovozingiz yoki rozilik bergan odamning ovozi bilan foydalaning.**

## Papka tuzilmasi

```text
cs50-translate-uzbek/
  dub                # ishga tushirish
  setup.sh           # bir martalik oʻrnatish
  glossary.json      # inglizcha qoladigan terminlar va talaffuzi
  apps/dubber/       # dastur kodi (download, separate, transcribe, translate, tts, mix)
  scripts/           # Chatterbox va OmniVoice uchun yordamchi skriptlar
  claude_docs/       # tarjima fayllari (repoga kirmaydi)
  videos/            # oraliq fayllar (repoga kirmaydi)
  outputs/           # tayyor videolar (repoga kirmaydi)
```

## Cheklovlar

- Faqat macOS (Apple Silicon) da sinalgan.
- Tarjima sifati va vaqtga sigʻishi qoʻlda yaxshilanadi: Lecture 0 da Edge bilan 1645 segmentdan 573 tasi vaqtdan oshdi.
- Ovoz mimikaga (lab harakatiga) toʻliq tushmaydi, chunki oʻzbekcha jumlalar inglizchadan uzun.
- Subtitr vaqtlari asl inglizcha segmentlarga bogʻlangan.

## Huquq va axloq

- CS50 materiallari Harvard universitetiga tegishli va odatda Creative Commons (BY-NC-SA) litsenziyasi bilan tarqatiladi. Aniq shartlarni nashrdan oldin [CS50 rasmiy saytidan](https://cs50.harvard.edu) tekshiring. Bu repoda ma'ruza videosi, matni va tarjimasi yoʻq.
- Dublyaj qilingan videoda manbani koʻrsating va tarjima/ovoz sun'iy intellekt bilan yaratilganini yashirmang.
- Har bir ovoz modelining oʻz litsenziyasi bor (MMS va OmniVoice: CC-BY-NC; Chatterbox adapteri: MIT; Edge: Microsoft shartlari). Ularni ishlatishdan oldin oʻqing.
- Boshqa odamning ovozini roziligisiz klonlamang.

## Litsenziya

Kod litsenziyasi hali tanlanmagan: litsenziya fayli qoʻshilmaguncha barcha huquqlar muallifda qoladi.

## Minnatdorchilik

[CS50](https://cs50.harvard.edu), [yt-dlp](https://github.com/yt-dlp/yt-dlp), [demucs](https://github.com/adefossez/demucs), [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [edge-tts](https://github.com/rany2/edge-tts), [Meta MMS](https://huggingface.co/facebook/mms-tts-uzb-script_cyrillic), [Chatterbox](https://huggingface.co/ResembleAI/chatterbox) va [UAzimov oʻzbek adapteri](https://huggingface.co/UAzimov/Uzbek-tts-chatterbox), [OmniVoice](https://huggingface.co/k2-fsa/OmniVoice).
