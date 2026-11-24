#!/usr/bin/env python3
"""Local SDXL-Turbo image generation on the RX 6800 XT (ROCm)."""

import sys
from pathlib import Path

import torch
from diffusers import AutoPipelineForText2Image

MODEL = '/home/haosuguo/models/sdxl-turbo'
PIPE = None


def pipe():
    global PIPE
    if PIPE is None:
        PIPE = AutoPipelineForText2Image.from_pretrained(
            MODEL, torch_dtype=torch.float16, variant='fp16', use_safetensors=True)
        try:
            PIPE.enable_model_cpu_offload()
        except Exception:
            PIPE.to('cuda')
        PIPE.set_progress_bar_config(disable=True)
    return PIPE


def generate(prompt, path, width=768, height=1152, steps=2, seed=0):
    generator = torch.Generator(device='cuda').manual_seed(seed) if seed else None
    image = pipe()(prompt=prompt, num_inference_steps=steps, guidance_scale=0.0,
                   width=width, height=height, generator=generator).images[0]
    image.save(path)
    return path


if __name__ == '__main__':
    prompt = sys.argv[1] if len(sys.argv) > 1 else 'a cozy convenience store at night, warm light'
    out = sys.argv[2] if len(sys.argv) > 2 else '/tmp/sdxl-test.jpg'
    generate(prompt, out)
    print('saved', out, Path(out).stat().st_size)
