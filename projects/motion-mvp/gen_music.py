#!/usr/bin/env python3
"""Procedural background beds: chord pad + arpeggio + light rhythm."""

import subprocess
import sys

STYLES = {
    'tech':   {'bpm': 96,  'chords': [(220, 277, 330), (196, 247, 294), (175, 220, 262), (196, 247, 294)],
               'arp': 440, 'kick': 0.6, 'air': 0.02},
    'ambient':{'bpm': 72,  'chords': [(220, 262, 330), (196, 247, 311), (175, 220, 277), (165, 208, 262)],
               'arp': 330, 'kick': 0.15, 'air': 0.05},
    'upbeat': {'bpm': 120, 'chords': [(262, 330, 392), (294, 349, 440), (330, 392, 494), (294, 349, 440)],
               'arp': 523, 'kick': 0.5, 'air': 0.015},
}


def build(style, seconds, out):
    cfg = STYLES[style]
    beat = 60.0 / cfg['bpm']
    parts, inputs = [], []
    for index, chord in enumerate(cfg['chords']):
        dur = max(1.0, seconds / len(cfg['chords']))
        for note in chord:
            inputs += ['-f', 'lavfi', '-i', f'sine=frequency={note}:duration={dur}']
            parts.append(f'[{len(parts)}]volume=0.10,aecho=0.8:0.6:120:0.25[c{len(parts)}]')
    # arpeggio
    inputs += ['-f', 'lavfi', '-i', f'sine=frequency={cfg["arp"]}:duration={seconds}']
    arp_idx = len(parts)
    parts.append(f'[{arp_idx}]tremolo=f={cfg["bpm"]/60*2}:d=0.9,volume=0.045[a]')
    # soft kick
    inputs += ['-f', 'lavfi', '-i', f'sine=frequency=60:duration={seconds}']
    kick_idx = len(parts)
    parts.append(f'[{kick_idx}]tremolo=f={cfg["bpm"]/60}:d=0.95,volume={cfg["kick"]*0.25}[k]')
    # air
    inputs += ['-f', 'lavfi', '-i', f'anoisesrc=d={seconds}:c=pink:r=44100']
    air_idx = len(parts)
    parts.append(f'[{air_idx}]highpass=f=3500,volume={cfg["air"]}[n]')
    labels = ''.join(f'[c{i}]' for i in range(len(cfg['chords']) * len(cfg['chords'][0])))
    parts.append(labels + f'[a][k][n]amix=inputs={len(cfg["chords"]) * len(cfg["chords"][0]) + 3}'
                 f':duration=longest:normalize=0,volume=1.2[m]')
    cmd = ['ffmpeg', '-y', '-loglevel', 'error'] + inputs + ['-filter_complex', ';'.join(parts),
           '-map', '[m]', '-c:a', 'aac', out]
    subprocess.run(cmd, check=True)
    return out


if __name__ == '__main__':
    style = sys.argv[1] if len(sys.argv) > 1 else 'tech'
    seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 10
    out = sys.argv[3] if len(sys.argv) > 3 else f'/tmp/{style}.m4a'
    print(build(style, seconds, out))
