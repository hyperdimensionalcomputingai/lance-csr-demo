# Portrait prompts

Instructions for generating the 26 synthetic Maker Night portraits with any image model. Each
person line uses the age, gender, hair and eye colour in `data/raw/people.csv`, so the portraits
match the dataset. Heritage cues are creative choices for these fictional faces, not facts about
people with those names.

## Prompt

Each prompt is the shared style block followed by one person line, for example:

> Head-and-shoulders portrait photo of a fictional adult, facing the camera, relaxed friendly
> expression, plain light-grey studio background, soft even lighting, casual everyday clothes,
> sharp focus on the eyes. No text, logos, props or hats. A 32-year-old man, black hair, brown
> eyes.

### Shared style block (every image)

> Head-and-shoulders portrait photo of a fictional adult, facing the camera, relaxed friendly
> expression, plain light-grey studio background, soft even lighting, casual everyday clothes,
> sharp focus on the eyes. No text, logos, props or hats.

### Person lines

| File | Name | Person line |
|---|---|---|
| 01.png | Abby | 31-year-old woman, black hair, green eyes |
| 02.png | Boris | 36-year-old man, black hair, brown eyes |
| 03.png | Carla | 28-year-old woman, brown hair, hazel eyes |
| 04.png | Dmitri | 45-year-old man, blond hair, blue eyes |
| 05.png | Elliott | 30-year-old man, dark brown hair, blue eyes |
| 06.png | Farah | 26-year-old woman, black hair, brown eyes |
| 07.png | Gabriel | 39-year-old man, brown hair, brown eyes |
| 08.png | Hannah | 33-year-old woman, black hair, brown eyes |
| 09.png | Ines | 29-year-old woman, brown hair, green eyes |
| 10.png | Jonas | 34-year-old man, blond hair, blue eyes |
| 11.png | Kenneth | 37-year-old man, black hair, brown eyes |
| 12.png | Leo | 35-year-old man, blond hair, brown eyes |
| 13.png | Maya | 34-year-old woman, brown hair, brown eyes |
| 14.png | Nina | 33-year-old woman, black hair, blue eyes |
| 15.png | Omar | 29-year-old man, brown hair, brown eyes |
| 16.png | Pedro | 32-year-old man, black hair, brown eyes |
| 17.png | Qian | 33-year-old Chinese woman, black hair, brown eyes |
| 18.png | Rafael | 58-year-old man, grey hair, brown eyes |
| 19.png | Sherry | 27-year-old woman, flaming red hair, blue eyes |
| 20.png | Tara | 27-year-old woman, red hair, hazel eyes |
| 21.png | Uma | 41-year-old woman, black hair, brown eyes |
| 22.png | Valentina | 30-year-old woman, blond hair, hazel eyes |
| 23.png | William | 31-year-old man, dark brown hair, brown eyes |
| 24.png | Xi | 45-year-old Chinese man, black hair, brown eyes |
| 25.png | Yusuf | 38-year-old man, dark brown hair, brown eyes |
| 26.png | Zoe | 32-year-old woman, black hair, brown eyes |

## Delivery

- **Format:** square PNG, 256×256. Generating at 512 or 1024 and downscaling gives better
  faces; larger files are fine too, and the loader can resize them.
- **Location:** this folder (`data/portraits/`), named by `person_id` as in the table
  (`16.png` is Pedro).
- **Check before saving:** hair and eye colour must visibly match the person line. Eye colour is
  easy to lose at 256 px, so keep the framing fairly close.
- **Same settings for all 26** (model, size, steps), so differences between images come from the
  people, not the settings.
- **Record where they came from** in `SOURCE.md` in this folder: model name and version, seeds if
  the tool shows them, the date, and the licence or usage terms.

## Optional

- **Varied faces:** the dataset has no ethnicity field. For this fictional cast, heritage cues
  were chosen as plausible readings of the names, with distinct facial shapes and hairstyles.
  Farah, Kenneth, William and Zoe have Black appearances. These are visual art directions, not
  ethnicity labels in the dataset or claims about real people with those names.
