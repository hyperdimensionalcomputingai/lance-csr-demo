# Portrait source

- **Created:** 2026-11-08; selective refresh 2026-11-09 (America/Toronto).
- **Generator:** OpenAI's built-in image generation tool in Codex. The tool did not expose its model name/version, seed, or step count.
- **Inputs:** The shared studio style and person lines in [PROMPTS.md](PROMPTS.md). The 2026-11-09 refresh replaced portraits 02, 05, 09, 10, 15, 18, 19, 21, 22, 23 and 26 with more distinct faces and plausible name-based heritage cues, as requested by the user. The other 15 numbered portraits were kept after visual review. Four portraits (Farah, Kenneth, William and Zoe) depict Black fictional people. These cues are visual art directions, not verified ancestry or dataset fields.
- **Processing:** All generated images were resized to square 256 × 256 RGB PNGs. The numbered files match `person_id` in `data/raw/people.csv`.
- **Use:** These are synthetic images, not photos of real people. OpenAI's [Terms of Use](https://openai.com/policies/terms-of-use/) and [Services Agreement](https://openai.com/policies/services-agreement/) state that, as between the user/customer and OpenAI and to the extent permitted by law, the user/customer owns output. Use remains subject to the applicable terms and policies. OpenAI does not supply a separate stock-photo licence for these files.

The images are illustrative demo assets. Hair and eye colours were checked visually at contact-sheet size; exact colour or identity consistency is not guaranteed by the generator.

## Refresh directions

The refreshed images used the shared style in `PROMPTS.md` plus these individual visual cues:

| ID | Direction |
|---|---|
| 02 Boris | Eastern European, fair skin, short receding black hair, broad face and heavy brows |
| 05 Elliott | White Canadian, fair skin, side-parted dark brown hair, long narrow face |
| 09 Ines | Iberian, olive skin, short chestnut bob, oval face and high cheekbones |
| 10 Jonas | Northern European, fair skin, cropped blond hair, long angular face |
| 15 Omar | Middle Eastern, olive skin, straight brown hair, lean long face |
| 18 Rafael | Latino, tan skin, brushed-back grey hair, broad face and grey moustache |
| 19 Sherry | Irish-Canadian, fair freckled skin, vivid copper-red pixie cut, round face |
| 21 Uma | South Asian, medium-brown skin, black hair in a low bun, heart-shaped face |
| 22 Valentina | Italian, light olive skin, straight shoulder-length blond hair, angular cheekbones |
| 23 William | Black Canadian, deep-brown skin, dark brown locs, narrow face |
| 26 Zoe | Black British, dark-brown skin, short natural black curls, rounded face |
