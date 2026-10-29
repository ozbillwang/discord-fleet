---
name: image-gen
description: "Generate images (text-to-image) for BuilderX AI: posters, event visuals, social posts. Calls the local bx-llm-gw image route (127.0.0.1:18080), which only allows a few approved models and enforces a daily quota. Use when the owner or a topic needs a picture."
version: 1.0.0
author: builderxai-fleet
metadata:
  hermes:
    tags: [image, generation, poster, design]
---

# Image generation (BuilderX AI)

`python3 ${HERMES_SKILL_DIR}/scripts/imagine.py "<prompt>" <out.png> [--model M] [--size WxH] [--n N]`

- Goes through **`http://127.0.0.1:18080/v1/images/generations`** (bx-llm-gw) with your own client key (`BX_LLM_GW_KEY`, injected by the host). You never see the real upstream key.
- Models allowed for you (the gateway refuses everything else):

| model | when to use |
|---|---|
| `gpt-image-2` (**default**) | best quality, good typography; SFW only |
| `gpt-image-2.5` | newer GPT image model, try it for posters with lots of text |
| `grok-imagine-image-2.0` | fast (~10 s), more photographic |

- `--size` is `1024x1024` (default), `1024x1536`, `1536x1024` or `auto`, but **the upstream treats it only as a hint**. Tested 2026-10-25: asking for portrait or landscape both came back near-square (e.g. 1374×1145). If orientation matters, also say it in the prompt ("tall vertical poster, 3:4") and check the result. `--n` is 1–2.
- `grok-imagine-image-2.0` returns JPEG; the script saves it with the right extension automatically.
- Quota: shared daily cap per client (see gateway log `quota_left=`). Don't batch-generate variations.

## How to write the prompt
You own the prompt. Put everything the model needs in it: subject, setting, composition, style, colours, lighting, **exact text to render** (in quotes), aspect ratio. For BuilderX AI visuals: clean modern tech style, brand colours deep indigo `#4f46e5` → purple `#9333ea` with warm gold `#fbbf24` accents, dark background `#050505`. Avoid clutter.

## Rules
- SFW only. This is a public community brand.
- No real people's likeness unless they asked for it. No logos or trademarks of other companies.
- After generating, open the file to check it (vision) before you share it. If the text is garbled, regenerate once with shorter text, not repeatedly.
- Images are for BuilderX AI use: Discord posts, event pages, social media drafts.
