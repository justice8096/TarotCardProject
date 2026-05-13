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
