# motion-mvp · 动态图文短视频流水线

一句需求 → 分镜 → 配图（本地 SDXL-Turbo）→ 配音（edge-tts）→ 字幕 → 竖屏 MP4。

## 用法

```sh
python3 pipeline.py "便利店开业宣传，30 秒，亲切口语" my-video
# 产物：out/my-video/final.mp4，720x1280，含配音与烧录字幕
```

## 流程

1. **分镜**：千问4Max 生成 JSON（每镜头：字幕文本 + 英文出图提示词）。
2. **配图**：本地 SDXL-Turbo（ROCm，CPU offload）优先；失败回退 Pollinations。
3. **配音**：edge-tts `zh-CN-XiaoxiaoNeural`，逐镜头生成后拼接。
4. **合成**：每镜头做 Ken Burns 缓慢推近 + 淡入淡出 + 底部字幕，最后由 ffmpeg 拼接并混入配音。

## 环境

- Python 3.12，`torch 2.9.1+rocm6.3`、`diffusers`、`edge-tts`、`ffmpeg`
- 模型：`/home/haosuguo/models/sdxl-turbo`（SDXL-Turbo fp16，约 6.9GB）
- 显存：SDXL 需约 10GB；本地 qwen 服务与它同时跑会 OOM，出片前先 `systemctl --user stop qwen-local`
- 千问 key：`~/.openclaw/credentials/qwen.key`

## 已知限制

- 无背景音乐、无转场特效（只有硬切 + 淡入淡出）；
- 字幕按 11 字/行硬换行，长句会占 3 行；
- 每镜头约 6–8 秒，节奏偏慢；出片速度约 3–5 分钟/条（本地 SDXL + 5 镜头）；
- 图与字幕的一致性依赖提示词，复杂品牌要求需人工替换素材。
