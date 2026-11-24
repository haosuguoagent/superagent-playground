#!/usr/bin/env python3
"""Motion MVP: a written brief becomes a narrated vertical short video.

Pipeline: storyboard (LLM) -> images (Pollinations) -> TTS (edge-tts) ->
per-scene Ken Burns clip with burned-in subtitles -> concat + audio mux.
"""

import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HOME = Path('/home/haosuguo')
OUT = HOME / 'motion-mvp' / 'out'
QWEN_KEY = HOME / '.openclaw' / 'credentials' / 'qwen.key'
LLM_URL = 'https://token-plan.maas.qianwenaiapi.com/compatible-mode/v1/chat/completions'
W, H, FPS = 720, 1280, 30
FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'


def llm(prompt, max_tokens=1500):
    key = QWEN_KEY.read_text().strip()
    body = json.dumps({'model': 'qwen4-max', 'messages': [{'role': 'user', 'content': prompt}],
                       'max_tokens': max_tokens, 'temperature': 0.7}).encode()
    request = urllib.request.Request(LLM_URL, data=body,
                                     headers={'Content-Type': 'application/json',
                                              'Authorization': 'Bearer ' + key})
    with urllib.request.urlopen(request, timeout=180) as response:
        data = json.load(response)
    return data['choices'][0]['message'].get('content') or ''


def storyboard(brief, count=5):
    prompt = ('你是短视频导演。根据下面的需求写分镜：\n' + brief + f'\n\n'
              '输出 JSON 对象：{"title":"不超过 10 字的片头标题","cta":"不超过 14 字的片尾行动号召",'
              f'"scenes":[共 {count} 个镜头，每个 {{"text":"这一屏的字幕，1-2 句口语","image":"给文生图模型的英文提示词，'
              '具体画面，不要出现文字；人物比例自然（头身比正常、手部完整），物品与人物尺度合理，不要夸张畸变"}}]}'
              '。只输出 JSON。')
    raw = llm(prompt)
    match = re.search(r'\{.*\}', raw, re.S)
    if not match:
        return {}
    try:
        return json.loads(match.group(0))
    except ValueError:
        return {}


def local_image(prompt, path):
    try:
        import sdxl_gen
        sdxl_gen.generate(prompt, str(path))
        return path.exists() and path.stat().st_size > 20000
    except Exception as error:  # noqa: BLE001
        print('local sdxl failed:', repr(error), flush=True)
        return False


def fetch_image(prompt, path):
    import time
    if local_image(prompt, path):
        return True
    for attempt in range(4):
        url = ('https://image.pollinations.ai/prompt/' + urllib.parse.quote(prompt) +
               f'?width=1024&height=1536&nologo=true&model=flux&seed={int(time.time()) % 99999}')
        subprocess.run(['curl', '-sL', '--max-time', '150', '-o', str(path), url], check=False)
        if path.exists() and path.stat().st_size > 20000:
            return True
        time.sleep(3 + attempt * 3)
    return False


def tts(text, path):
    subprocess.run(['edge-tts', '--voice', 'zh-CN-XiaoxiaoNeural', '--text', text,
                    '--write-media', str(path)], check=True, timeout=180)


def duration(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                          '-of', 'csv=p=0', str(path)], capture_output=True, text=True).stdout
    return float(out.strip() or 0)


def wrap(text, width=11):
    return '\n'.join(text[i:i + width] for i in range(0, len(text), width))


def escape(text):
    return text.replace('\\', '\\\\').replace("'", '’').replace(':', '：').replace('%', '％')


def scene_clip(img, text, dur, out):
    text_file = out.with_suffix('.txt')
    text_file.write_text(text, encoding='utf-8')
    vf = ('scale=1600:-1,'
          f"zoompan=z='min(zoom+0.0012,1.18)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          f':d={int(dur * FPS)}:s={W}x{H}:fps={FPS},'
          f'fade=t=in:st=0:d=0.35,fade=t=out:st={max(0.0, dur - 0.35):.2f}:d=0.35,'
          f"drawtext=fontfile={FONT}:textfile={text_file}:fontcolor=white:fontsize=44:"
          'line_spacing=14:box=1:boxcolor=black@0.35:boxborderw=20:'
          'x=(w-text_w)/2:y=h-text_h-150,format=yuv420p')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-loop', '1', '-i', str(img),
                    '-t', f'{dur:.2f}', '-vf', vf, '-r', str(FPS), '-c:v', 'libx264',
                    '-preset', 'veryfast', '-crf', '23', str(out)], check=True)


def card_clip(path, lines, seconds, bg='#101820', size=(W, H)):
    text_file = path.with_suffix('.txt')
    text_file.write_text('\n'.join(lines), encoding='utf-8')
    vf = (f"drawtext=fontfile={FONT}:textfile={text_file}:fontcolor=white:fontsize=60:"
          'line_spacing=26:x=(w-text_w)/2:y=(h-text_h)/2,'
          'fade=t=in:st=0:d=0.4,'
          f'fade=t=out:st={max(0.0, seconds - 0.4):.2f}:d=0.4,format=yuv420p')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi',
                    '-i', f'color=c={bg}:s={size[0]}x{size[1]}:d={seconds}:r={FPS}',
                    '-vf', vf, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
                    str(path)], check=True)


def music_bed(path, seconds):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error',
                    '-f', 'lavfi', '-i', f'sine=frequency=220:duration={seconds}',
                    '-f', 'lavfi', '-i', f'sine=frequency=277:duration={seconds}',
                    '-f', 'lavfi', '-i', f'sine=frequency=330:duration={seconds}',
                    '-filter_complex',
                    '[0][1][2]amix=inputs=3,tremolo=f=0.15:d=0.25,aecho=0.8:0.9:180:0.35,'
                    'volume=0.12', '-c:a', 'aac', str(path)], check=True)


def build(brief, name='demo', count=5):
    work = OUT / name
    work.mkdir(parents=True, exist_ok=True)
    board = storyboard(brief, count)
    scenes = board.get('scenes') or []
    if not scenes:
        raise SystemExit('storyboard failed')
    title_text = board.get('title') or brief[:10]
    cta_text = board.get('cta') or '开业有礼 · 欢迎光临'
    (work / 'storyboard.json').write_text(json.dumps(scenes, ensure_ascii=False, indent=2))
    clips, audios = [], []
    for index, scene in enumerate(scenes):
        image_path = work / f'img{index}.jpg'
        audio_path = work / f'audio{index}.mp3'
        clip_path = work / f'clip{index}.mp4'
        ok = fetch_image(scene['image'] + ', realistic proportions, natural human anatomy, '
                         'correct scale, no distorted hands, no extra limbs, no text', image_path)
        if not ok:
            raise SystemExit(f'image {index} failed')
        tts(scene['text'], audio_path)
        clip_dur = max(2.6, duration(audio_path) + 0.6)
        scene_clip(image_path, wrap(scene['text']), clip_dur, clip_path)
        clips.append(clip_path)
        audios.append(audio_path)
        print(f'scene {index}: {clip_dur:.1f}s {scene["text"][:30]}', flush=True)
    title_seconds, cta_seconds = 2.6, 3.2
    title = work / 'title.mp4'
    cta = work / 'cta.mp4'
    title_lines = wrap(title_text, 7).split('\n')
    card_clip(title, title_lines, title_seconds)
    card_clip(cta, wrap(cta_text, 9).split('\n') + ['路过记得拐进来'], cta_seconds, bg='#1f2a44')
    clips = [title] + clips + [cta]
    with (work / 'audio.txt').open('w') as handle:
        for item in audios:
            handle.write(f"file '{item}'\n")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0',
                    '-i', str(work / 'audio.txt'), '-c:a', 'aac', '-b:a', '128k',
                    str(work / 'voice.m4a')], check=True)
    # pad voice with silence for title/cta cards
    voice_padded = work / 'voice-padded.m4a'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error',
                    '-f', 'lavfi', '-i', f'anullsrc=r=44100:cl=stereo:d={title_seconds}',
                    '-i', str(work / 'voice.m4a'),
                    '-f', 'lavfi', '-i', f'anullsrc=r=44100:cl=stereo:d={cta_seconds}',
                    '-filter_complex', '[0][1][2]concat=n=3:v=0:a=1[a]',
                    '-map', '[a]', '-c:a', 'aac', str(voice_padded)], check=True)
    with (work / 'video.txt').open('w') as handle:
        for item in clips:
            handle.write(f"file '{item}'\n")
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0',
                    '-i', str(work / 'video.txt'), '-c:v', 'libx264', '-preset', 'veryfast',
                    '-crf', '23', str(work / 'video.mp4')], check=True)
    total = duration(work / 'video.mp4')
    bed = work / 'music.m4a'
    music_bed(bed, total)
    final = work / 'final.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error',
                    '-i', str(work / 'video.mp4'), '-i', str(voice_padded), '-i', str(bed),
                    '-filter_complex', '[1:a][2:a]amix=inputs=2:duration=first:weights=1 0.35[a]',
                    '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac',
                    '-shortest', str(final)], check=True)
    return final


if __name__ == '__main__':
    brief = sys.argv[1] if len(sys.argv) > 1 else '便利店开业宣传，30 秒，亲切口语'
    name = sys.argv[2] if len(sys.argv) > 2 else 'demo'
    result = build(brief, name)
    print('done:', result, f'{duration(result):.1f}s')
