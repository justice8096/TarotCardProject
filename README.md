<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->

# Tarot Card Project

A tarot card layout, spread and reader system. Differs from Rider-Waite by having more cards, and compatible with both the I-Ching balance model and the Tarot action model.

## Licensing

| What | License |
|------|---------|
| **Source code** (workflows, scripts, configs) | [GNU AGPL v3](LICENSE) — free to use and modify; all derivatives must also be open source |
| **Generated assets** (card images, animations) | [CC BY 4.0](LICENSE-ASSETS) — free to use, sell, or build on; attribution required |

## Tools & Services

- [n8n](https://n8n.io) — orchestration and automation
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) — image and video generation
- [Perplexity](https://www.perplexity.ai) — research
- [Claude](https://claude.ai) — code co-generation
- [Hugging Face](https://huggingface.co) — repository of AI models and associated tools
- [Ollama](https://ollama.com) — local small language model serving and repository
- [FFmpeg](https://ffmpeg.org) — video/audio encoding and concatenation
- TypeScript

## AI Models

### Diffusion Models (Image & Video Generation)

| Model | Type | Notes |
|-------|------|-------|
| [DreamShaper 8](https://civitai.com/models/4384/dreamshaper) | Checkpoint | Keyframe image generation |
| [Wan 2.2 I2V 14B](https://huggingface.co/Wan-AI) (high noise, fp8) | Diffusion UNet | Image-to-video interpolation |
| [Wan 2.2 I2V 14B](https://huggingface.co/Wan-AI) (low noise, fp8) | Diffusion UNet | Image-to-video interpolation (alt) |
| [HiDream I1 Full](https://huggingface.co/HiDream-ai) (fp8) | Checkpoint | Full image generation |
| [Qwen Image Edit 2509](https://huggingface.co/Qwen) (fp8) | Checkpoint | Image editing |
| Image Turbo (bf16) | Checkpoint | Fast image generation |

### Text Encoders & CLIP

| Model | Used By |
|-------|---------|
| umt5_xxl (fp8) | Wan 2.2 I2V |
| CLIP-L | Wan, HiDream |
| CLIP-G | HiDream |
| T5 XXL (fp8) | HiDream |
| [Llama 3.1 8B Instruct](https://huggingface.co/meta-llama) (fp8) | HiDream |
| [Qwen 2.5 VL 7B](https://huggingface.co/Qwen) (fp8) | Qwen Image Edit |

### VAEs

| Model | Used By |
|-------|---------|
| Wan 2.1 VAE | Wan I2V interpolation |
| ae.safetensors | HiDream |
| Qwen Image VAE | Qwen Image Edit |

### LoRAs

| Model | Notes |
|-------|-------|
| [LightX2V](https://huggingface.co/lightx2v) 4-step (high noise) | Enables 4-step Wan 2.2 generation |
| Qwen Image Edit Lightning 4-step (bf16) | Fast Qwen image editing |

### Language Models

| Model | Type | Notes |
|-------|------|-------|
| [Gemma 3N](https://huggingface.co/google/gemma-3n-e4b-it) | LLM (via Ollama) | Local text generation |
| [Mistral](https://huggingface.co/mistralai) | LLM (via Ollama) | Local text generation |
| [Qwen 3 4B](https://huggingface.co/Qwen) | LLM | Local text generation |

### Music Generation

| Model | Type | Notes |
|-------|------|-------|
| [Stable Audio Open 1.0](https://huggingface.co/stabilityai/stable-audio-open-1.0) | Checkpoint | Music generation |
| t5-base | Text Encoder | Used by Stable Audio |

### Speech & Audio

| Model | Notes |
|-------|-------|
| [Orpheus 3B](https://huggingface.co/canopylabs/orpheus-tts-0.1-finetune-prod) (Q6_K_XL GGUF) | Speech generation via llama.cpp + SNAC |

### 3D Generation

| Model | Notes |
|-------|-------|
| [Stable Zero123](https://huggingface.co/stabilityai/stable-zero123) | Multi-view image generation |
| [Hunyuan 3D v2.1](https://huggingface.co/tencent/Hunyuan3D-2) | 3D model generation |
| [RealESRGAN x4plus](https://github.com/xinntao/Real-ESRGAN) | Image upscaling |

### Other

| Model | Notes |
|-------|-------|
| [RMBG 2.0](https://huggingface.co/briaai/RMBG-2.0) | Background removal |

## Workflow Data Flow

Each n8n workflow reads from or writes to the deck and card JSON files. The table below shows which workflows populate which fields.

### Deck.json

`Deck.json` is the master configuration file for a deck. It stores deck-level settings (models, samplers, prompts, geometry) and a `Cards[]` array referencing each card's JSON file.

| Field | Written By | Description |
|-------|-----------|-------------|
| `Name`, `Version` | Generate Deck Structure, Normalize Deck Structure | Deck identity |
| `Assets.*` | Generate Deck Structure, Normalize Deck Structure | Output paths for deck-level media (animations, images) |
| `Geometries.*` | Generate Deck Structure, Normalize Deck Structure | Layout dimensions, frame rates |
| `Prompts.{Cut,Fan,Merge,Rotate}` | Generate Deck Structure | Dealer animation prompts (keyframes + negative) |
| `Prompts.{BackImage,FrontImage,Music,Narration}` | Normalize Deck Structure | Deck-wide generation prompts |
| `Models.*` | Manual / Normalize Deck Structure | Model file selections (defaults built in) |
| `Samplers.*` | Manual / Normalize Deck Structure | Inference parameters (defaults built in) |
| `Cards[]` | Generate Deck Structure | Array of `{ Card, File }` references to card JSONs |

### Card JSONs (`Cards/{CardName}.json`)

Each card JSON has metadata at `data.Cards` (card-level) and a `records[]` array with one entry per orientation (upright, reversed, between).

#### Card-level fields (`data.Cards`)

| Field | Written By | Description |
|-------|-----------|-------------|
| `Card` | Generate Deck Structure | Card name |
| `Directory` | Generate Deck Structure | Card directory path |
| `Assets.UprightImage` | Generate Deck Structure | Upright card image filename |
| `Assets.ReversedImage` | Generate Deck Structure | Reversed card image filename |
| `Prompts.UprightImage` | Generate Deck Structure | Image generation prompts for upright |
| `Prompts.ReversedImage` | Generate Deck Structure | Image generation prompts for reversed |

#### Per-orientation fields (`records[]`)

Each card has 3 records: upright, reversed, and between.

| Field | Written By | Description |
|-------|-----------|-------------|
| `Orientation` | Generate Deck Structure | "upright", "reversed", or "between" |
| `Description` | Add Meanings (via Ollama) | Card meaning description |
| `Keywords` | Add Meanings (via Ollama) | Comma-delimited keywords |
| `Advice` | Add Meanings (via Ollama) | Practical guidance text |
| `Affirmation` | Add Meanings (via Ollama) | Affirmation statement |
| `Category` | Generate Deck Structure (empty) | Category tags |
| `Prompts.CharacterImage.*` | Update Card JSONs from Spreadsheet | `CharacterName`, `Positive`, `Negative` prompts |
| `Prompts.Narration.*` | Generate Narration Styles (via Ollama) | `Voice`, `Tone`, `Pace`, `Emphasis`, `De-emphasis` |
| `Prompts.Image.*` | Generate Deck Structure | `Positive`, `Negative` prompts |
| `Assets.Image` | Generate Deck Structure (filename) | Generated character image |
| `Assets.CardImage` | Generate Deck Structure (filename) | Processed card illustration |
| `Assets.Narration` | Generate Deck Structure (filename) | Narration MP3 |
| `Assets.Music` | Generate Deck Structure (filename) | Background music MP3 |
| `Assets.Movie` | Generate Deck Structure (filename) | Animation video |
| `Assets.PalletImage` | Generate Deck Structure (filename) | Palette reference image |
| `Assets.Object` | Generate Deck Structure (filename) | 3D model OBJ |
| `Assets.FocusUpright` | Generate Focus Upright Stills | Array of 6 focus frame filenames |
| `Assets.FocusUprightT` | Generate FOCUST Upright Stills, Generate FOCUS Upright Blend Stills | Array of 14 focus frame filenames |
| `Assets.FocusReversedT` | Generate FOCUST Reversed Stills | Array of 14 focus frame filenames |

### Workflow Summary

| Workflow | Reads | Writes | Output |
|----------|-------|--------|--------|
| **Generate Deck Structure** | Spreadsheet (ODS) | Deck.json, Card JSONs | Creates initial deck + card files |
| **Update Card JSONs from Spreadsheet** | Spreadsheet (ODS), Card JSONs | Card JSONs | Updates `Prompts.CharacterImage` |
| **Normalize Deck Structure** | Deck.json | Deck_normalized.json | Ensures all sections/defaults exist |
| **Add Meanings** | Card JSONs | Card JSONs | Fills `Description`, `Keywords`, `Advice`, `Affirmation` via LLM |
| **Generate Narration Styles** | Card JSONs | Card JSONs | Fills `Prompts.Narration` fields via LLM |
| **Generate Focus Upright Stills** | Deck.json, Card JSONs | Card JSONs + PNG files | Writes `Assets.FocusUpright` array |
| **Generate FOCUST Upright Stills** | Deck.json, Card JSONs | Card JSONs + PNG files | Writes `Assets.FocusUprightT` array |
| **Generate FOCUS Upright Blend Stills** | Deck.json, Card JSONs | Card JSONs + PNG files | Merges into `Assets.FocusUprightT` array |
| **Generate FOCUST Reversed Stills** | Deck.json, Card JSONs | Card JSONs + PNG files | Writes `Assets.FocusReversedT` array |
| **Generate Card Tarot Images** | Deck.json, Card JSONs | PNG files only | Generates card images via ComfyUI |
| **Generate Full Tarot Images** | Deck.json, Card JSONs | PNG files only | Generates full card images via ComfyUI |
| **Generate Pallette Tarot Images** | Deck.json, Card JSONs | PNG files only | Generates palette-style images via ComfyUI |
| **Generate Card Faces** | Deck.json, Card JSONs | PNG files only | Renders card face layouts with text |
| **Generate Card Narrations** | Deck.json, Card JSONs | MP3 files only | Generates speech audio via Orpheus |
| **Generate Dealer Stop Motion** | Deck.json | PNG + MP4 files only | Generates dealer animations via ComfyUI + FFmpeg |
