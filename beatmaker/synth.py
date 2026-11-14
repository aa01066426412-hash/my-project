"""간단한 소프트웨어 신디사이저: 노트 목록을 WAV 파일로 렌더링한다.

장비나 샘플 파일 없이 사인파와 노이즈를 계산해서 드럼, 베이스, 건반, 멜로디 소리를 만든다.
"""

import array
import math
import random
import wave

from .theory import midi_to_freq

SR = 22050  # 샘플레이트. 순수 파이썬 계산이라 CD 음질(44100)의 절반으로 속도를 확보
TWO_PI = 2 * math.pi


# ---------------------------------------------------------------- 드럼
def _kick(rng):
    n = int(SR * 0.45)
    out, phase = [], 0.0
    for i in range(n):
        t = i / SR
        freq = 48 + 110 * math.exp(-t * 32)       # 높은 음에서 낮은 음으로 떨어지는 '쿵'
        phase += TWO_PI * freq / SR
        click = math.exp(-t * 400) * 0.4
        out.append(math.sin(phase) * math.exp(-t * 7) + click)
    return out


def _snare(rng):
    n = int(SR * 0.25)
    out, prev = [], 0.0
    for i in range(n):
        t = i / SR
        noise = rng.uniform(-1, 1)
        hp = noise - prev * 0.6                    # 노이즈를 살짝 밝게
        prev = noise
        out.append(hp * math.exp(-t * 18) * 0.6 + math.sin(TWO_PI * 185 * t) * math.exp(-t * 28) * 0.5)
    return out


def _clap(rng):
    n = int(SR * 0.3)
    out, prev = [], 0.0
    for i in range(n):
        t = i / SR
        noise = rng.uniform(-1, 1)
        hp = noise - prev
        prev = noise
        # 손뼉 여러 개가 겹친 느낌: 짧은 반복 뒤 감쇠
        env = math.exp(-(t % 0.011) * 300) if t < 0.033 else math.exp(-(t - 0.033) * 16)
        out.append(hp * env * 0.55)
    return out


def _hat(rng, length, decay):
    n = int(SR * length)
    out, prev = [], 0.0
    for i in range(n):
        t = i / SR
        noise = rng.uniform(-1, 1)
        hp = noise - prev                          # 고음만 남기는 하이패스
        prev = noise
        out.append(hp * math.exp(-t * decay) * 0.35)
    return out


def _drum_kit(seed):
    rng = random.Random(seed)
    return {
        36: _kick(rng),
        38: _snare(rng),
        39: _clap(rng),
        42: _hat(rng, 0.06, 70),
        46: _hat(rng, 0.35, 11),
    }


# ---------------------------------------------------------------- 음정 있는 악기
def _env(t, dur, attack, decay, release):
    a = min(1.0, t / attack) if attack > 0 else 1.0
    e = a * math.exp(-t * decay)
    if t > dur:
        e *= math.exp(-(t - dur) / release)
    return e


def _tone(kind, freq, dur, vel):
    release = {"pad": 0.4, "808": 0.08}.get(kind, 0.12)
    tail = release * 5
    n = int(SR * (dur + tail))
    amp = vel / 127
    out = []
    phase = 0.0
    for i in range(n):
        t = i / SR
        if kind == "808":
            f = freq * (1 + 0.6 * math.exp(-t * 45))   # 시작 순간 피치가 살짝 떨어지는 808 특유의 소리
            phase += TWO_PI * f / SR
            x = math.tanh(1.8 * math.sin(phase)) * _env(t, dur, 0.004, 0.9, release)
        elif kind == "sub":
            x = (math.sin(TWO_PI * freq * t) + 0.3 * math.sin(TWO_PI * 2 * freq * t)) * _env(t, dur, 0.006, 2.2, release)
        elif kind == "house_bass":
            x = (math.sin(TWO_PI * freq * t) + 0.35 * math.sin(TWO_PI * 2 * freq * t)
                 + 0.15 * math.sin(TWO_PI * 3 * freq * t)) * _env(t, dur, 0.003, 5, release)
        elif kind == "keys":  # 일렉트릭 피아노 비슷한 소리
            trem = 1 + 0.08 * math.sin(TWO_PI * 4.5 * t)
            x = (math.sin(TWO_PI * freq * t)
                 + 0.35 * math.sin(TWO_PI * 2 * freq * t) * math.exp(-t * 3)
                 + 0.12 * math.sin(TWO_PI * 3 * freq * t) * math.exp(-t * 7)) * trem * _env(t, dur, 0.005, 1.1, release)
        elif kind == "stab":
            x = (math.sin(TWO_PI * freq * t) + 0.4 * math.sin(TWO_PI * 2 * freq * t)) * _env(t, dur, 0.002, 7, release)
        elif kind == "pad":
            x = (math.sin(TWO_PI * freq * t) + 0.6 * math.sin(TWO_PI * freq * 1.006 * t)
                 + 0.6 * math.sin(TWO_PI * freq * 0.994 * t)) / 2.2 * _env(t, dur, 0.25, 0.15, release)
        elif kind == "bell":
            x = (math.sin(TWO_PI * freq * t) + 0.5 * math.sin(TWO_PI * freq * 2.76 * t) * math.exp(-t * 6)) * _env(t, dur, 0.002, 2.5, release)
        else:  # "lead": 부드러운 삼각파
            x = (2 / math.pi) * math.asin(math.sin(TWO_PI * freq * t)) * _env(t, dur, 0.01, 2.0, release)
        out.append(x * amp)
    return out


# 장르별 악기 선택과 음량
VOICES = {
    "lofi": {"bass": ("sub", 0.55), "chords": ("keys", 0.20), "melody": ("lead", 0.20)},
    "hiphop": {"bass": ("sub", 0.55), "chords": ("keys", 0.22), "melody": ("lead", 0.20)},
    "trap": {"bass": ("808", 0.60), "chords": ("pad", 0.14), "melody": ("bell", 0.20)},
    "house": {"bass": ("house_bass", 0.45), "chords": ("stab", 0.15), "melody": ("lead", 0.17)},
}
DRUM_GAIN = {36: 0.9, 38: 0.55, 39: 0.6, 42: 0.35, 46: 0.3}


def _mix_in(buf, start, samples, gain):
    end = min(len(buf), start + len(samples))
    for i in range(max(0, start), end):
        buf[i] += samples[i - start] * gain


def render(beat, path, lofi_fx=None):
    sec_per_beat = 60 / beat.bpm
    total = int(SR * (beat.bars * 4 * sec_per_beat + 2.0))
    buf = [0.0] * total
    kit = _drum_kit(beat.seed)
    voices = VOICES[beat.genre]
    cache = {}

    for n in beat.notes:
        start = int(n.start * sec_per_beat * SR)
        if n.track == "drums":
            _mix_in(buf, start, kit[n.pitch], DRUM_GAIN[n.pitch] * n.vel / 127)
            continue
        kind, gain = voices[n.track]
        freq = midi_to_freq(n.pitch)
        dur = n.dur * sec_per_beat
        k = (kind, n.pitch, round(dur, 3), n.vel)   # 같은 음은 다시 계산하지 않는다
        if k not in cache:
            cache[k] = _tone(kind, freq, dur, n.vel)
        _mix_in(buf, start, cache[k], gain)

    if lofi_fx is None:
        lofi_fx = beat.genre == "lofi"
    if lofi_fx:
        _lofi(buf, beat.seed)

    peak = max(1e-9, max(abs(x) for x in buf))
    scale = 0.9 / peak
    pcm = array.array("h", (int(math.tanh(x * scale * 1.1) * 32000) for x in buf))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return total / SR


def _lofi(buf, seed):
    """로파이 질감: 고음을 깎는 로우패스 + 레코드판 잡음."""
    rng = random.Random(seed + 1)
    alpha = 1 - math.exp(-TWO_PI * 3800 / SR)
    y = 0.0
    for i in range(len(buf)):
        y += alpha * (buf[i] - y)
        crackle = rng.uniform(-1, 1) * 0.004
        if rng.random() < 0.0004:
            crackle += rng.uniform(-0.15, 0.15)
        buf[i] = y + crackle
