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
- **Muallifning ovozi.** Namuna ovoz yozuvi repoga kiritilmagan. Muallifning ovozi, uning namuna yozuvi va shu ovoz bilan yaratilgan sintez audio klonlash, taqlid qilish yoki ovoz/AI modelini oʻqitish uchun ishlatilishi mumkin emas. MIT litsenziyasi faqat kodga tegishli, ovoz yozuvlarini qamramaydi.

## Nashr qilish (YouTube va boshqa kanallar)

CS50 materiallari CC BY-NC-SA 4.0 ostida, OmniVoice modeli esa CC-BY-NC. Shu sababli dublyaj qilingan videolarni nashr qilganda:

- **Daromadsiz boʻlsin:** monetizatsiya, reklama, homiylik va pullik kursga bogʻlamang. Asosiy kanalingiz monetizatsiya qilingan boʻlsa, dublyajlar uchun alohida kanal ochish xavfsizroq (YouTube ning "reused content" qoidasi kanal darajasida ishlaydi).
- **Manbani koʻrsating:** asl CS50 videosiga havola va "CC BY-NC-SA 4.0" yozuvi. Hosila asar xuddi shu litsenziyada tarqatiladi (ShareAlike). YouTube ning "Creative Commons" tanlovi CC BY ni beradi, bu mos kelmasligi mumkin, shuning uchun uni tanlamasdan, litsenziyani tavsifda yozing.
- **AI ekanini yashirmang:** tarjima va ovoz sunʼiy intellekt bilan yaratilgan. Oʻz ovozingiz bilan dublyaj qilish YouTube ning sunʼiy kontent yorligʻini odatda talab qilmaydi, lekin tavsifda baribir yozing.
- **Harvard yoki CS50 tasdiqlamagan:** buni aniq yozing. Imkon boʻlsa, nashrdan oldin CS50 jamoasidan ruxsat soʻrang.
- **OmniVoice shartlari:** modelni manba sifatida koʻrsating; chiqqan audio bilan boshqa AI modelini oʻqitmang; tokenizer litsenziyasidagi (`audio_tokenizer/LICENSE`) "Built with Higgs Materials" talabi va 100 000 yillik foydalanuvchi chegarasi sizga tegishlimi, mualliflardan soʻrang.

Video tavsifi uchun shablon:

```text
Bu video CS50x (Harvard University) ma'ruzasining oʻzbekcha dublyaj qilingan nusxasi.
Asl video: <havola>
CS50 materiallari CC BY-NC-SA 4.0 litsenziyasi ostida; bu dublyaj ham shu litsenziya ostida va tijoriy maqsadda ishlatilmaydi.
Tarjima sunʼiy intellekt yordamida qilingan [va muallif tomonidan tekshirilgan].
Ovoz: muallifning ovozi asosida OmniVoice (k2-fsa) modeli bilan sintez qilingan.
Ovoz haqida: bu ovozni klonlash, taqlid qilish yoki ovoz/AI modelini oʻqitish uchun ishlatish mumkin emas. Shaxsiy huquqlar saqlanadi va CC litsenziyasiga kirmaydi.
Bu video Harvard yoki CS50 tomonidan tasdiqlanmagan.
```

## Tijoriy foydalanish va fine-tuning

Bu boʻlim huquqiy maslahat emas. Model va maʼlumot litsenziyalarini oʻzingiz tekshiring.

Dublyaj dasturini SaaS yoki daromadli xizmat sifatida ishlatmoqchi boʻlsangiz, ovoz dvigateli shunga ruxsat berishi kerak:

| Dvigatel | Daromadli foydalanish |
| --- | --- |
| `edge` | Tavsiya etilmaydi: `edge-tts` Microsoft ning rasmiy API sini emas, brauzer xizmatini ishlatadi. Tijorat uchun rasmiy yoʻl Azure AI Speech (pullik, shartlarini tekshiring) |
| `mms` | Yoʻq: model CC-BY-NC |
| `cbx` (Chatterbox) | Ehtimol mumkin: Chatterbox va oʻzbek adapteri MIT (model kartalariga koʻra). Asos modelni, oʻqitish maʼlumotlari litsenziyalarini tekshiring; chiqishga suv belgisi (watermark) qoʻyiladi |
| `omni` (OmniVoice) | Yoʻq: model ogʻirliklari CC-BY-NC. Tokenizer litsenziyasida (`audio_tokenizer/LICENSE`) qoʻshimcha shartlar bor: yozuv, 100 000 yillik foydalanuvchi chegarasi, chiqqan audio bilan boshqa modelni oʻqitmaslik |

### OmniVoice ni fine-tuning qilish

OmniVoice repozitoriysida toʻliq fine-tuning (`docs/training.md`) va LoRA (`docs/lora_finetuning.md`) yoʻriqnomalari bor. LoRA parametrlarning taxminan 3% ini oʻqitadi (19,3 mln / 631,9 mln) va boshlangʻich model sifatida `k2-fsa/OmniVoice` ni oladi. Biz buni sinab koʻrmaganmiz.

- **Fine-tuning litsenziyani oʻzgartirmaydi.** Natija CC-BY-NC modelning hosilasi, shuning uchun u ham tijoriy emas. Tokenizer litsenziyasiga koʻra, Higgs materiallari bilan yaratilgan modelni tarqatsangiz, uning nomi "Higgs Audio 2" bilan boshlanishi va litsenziya hamda yozuvlar qoʻshilishi kerak.
- **Foydasi:** oʻzbekcha sifatni yaxshilash mumkin (bu faraz, tekshirilmagan), lekin faqat tadqiqot va tijoriy boʻlmagan maqsadda.
- **Tijorat uchun yoʻllar:** mualliflardan tijorat litsenziyasi soʻrash, yoki Apache-2.0 kod bilan ruxsat berilgan ochiq maʼlumotda (masalan, Uzbek Speech Corpus CC-BY-4.0, Common Voice CC0) noldan oʻqitish va tokenizer shartlarini ham hal qilish.
- **Apparat:** standart oʻqitish `flex_attention` ni ishlatadi (PyTorch ≥ 2.5 va Ampere yoki yangiroq NVIDIA GPU tavsiya etiladi). Eskiroq GPU da `attn_implementation: "sdpa"` ishlating. Xotira va vaqt talabi bizda oʻlchanmagan.

## Litsenziya

Bu repodagi kod [MIT litsenziyasi](LICENSE) bilan tarqatiladi. Litsenziya faqat shu kodga tegishli: CS50 materiallari va ovoz modellarining oʻz litsenziyalari bor (yuqoridagi "Huquq va axloq" boʻlimiga qarang).

## Minnatdorchilik

[CS50](https://cs50.harvard.edu), [yt-dlp](https://github.com/yt-dlp/yt-dlp), [demucs](https://github.com/adefossez/demucs), [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [edge-tts](https://github.com/rany2/edge-tts), [Meta MMS](https://huggingface.co/facebook/mms-tts-uzb-script_cyrillic), [Chatterbox](https://huggingface.co/ResembleAI/chatterbox) va [UAzimov oʻzbek adapteri](https://huggingface.co/UAzimov/Uzbek-tts-chatterbox), [OmniVoice](https://huggingface.co/k2-fsa/OmniVoice).
