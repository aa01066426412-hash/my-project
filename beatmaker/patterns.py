"""장르별 규칙으로 비트(노트 목록)를 만든다.

시간 단위는 '박(beat)'이다. 4/4 박자에서 한 마디 = 4박, 16분음표 한 칸 = 0.25박.
"""

import random
from dataclasses import dataclass

from . import theory

# General MIDI 드럼 번호
KICK, SNARE, CLAP, HAT, OPEN_HAT = 36, 38, 39, 42, 46


@dataclass
class Note:
    track: str      # "drums" | "bass" | "chords" | "melody"
    start: float    # 시작 위치(박)
    dur: float      # 길이(박)
    pitch: int      # MIDI 번호
    vel: int        # 세기 1~127


# 패턴 문자열: 16칸 = 한 마디의 16분음표. x = 강하게, o = 약하게(고스트), . = 쉼
GENRES = {
    "lofi": {
        "bpm": 82, "key": "A", "swing": 0.28, "humanize": 0.012,
        "kick": ["x.........x.x...", "x......x..x.....", "x.......x.x....."],
        "snare": ["....x.......x...", "....x.......x..o"],
        "hat": ["x.x.x.x.x.x.x.x.", "x.xox.x.x.xox.x."],
        "open_hat": ["................"],
        "progressions": [
            [(0, "m9"), (5, "m7"), (10, "7"), (3, "maj7")],
            [(5, "m9"), (10, "7"), (3, "maj9"), (8, "maj7")],
            [(0, "m7"), (8, "maj7"), (3, "maj7"), (10, "7")],
        ],
        "chord_style": "strum", "bass_style": "follow_kick",
        "melody_density": 0.35, "melody_grid": 0.5,
    },
    "hiphop": {
        "bpm": 90, "key": "D", "swing": 0.18, "humanize": 0.008,
        "kick": ["x.....x...x.....", "x..x......x..x..", "x.x.......x..x.."],
        "snare": ["....x.......x...", "....x.......x.o."],
        "hat": ["x.x.x.x.x.x.x.x.", "x.x.x.xxx.x.x.x."],
        "open_hat": ["..............x.", "................"],
        "progressions": [
            [(0, "m7"), (8, "maj7"), (5, "m7"), (7, "m7")],
            [(0, "m9"), (3, "maj7"), (8, "maj7"), (7, "7")],
        ],
        "chord_style": "hold", "bass_style": "follow_kick",
        "melody_density": 0.3, "melody_grid": 0.5,
    },
    "trap": {
        "bpm": 140, "key": "F", "swing": 0.0, "humanize": 0.0,
        "kick": ["x......x..x.....", "x.....x...x..x..", "x.x.......x....."],
        "snare": ["........x......."],
        "hat": ["xxxxxxxxxxxxxxxx", "x.xxx.xxx.xxx.xx"],
        "open_hat": ["................"],
        "progressions": [
            [(0, "min"), (8, "maj"), (3, "maj"), (10, "maj")],
            [(0, "min"), (1, "maj"), (0, "min"), (7, "min")],
            [(0, "min"), (5, "min"), (8, "maj"), (7, "min")],
        ],
        "chord_style": "pad", "bass_style": "808",
        "melody_density": 0.22, "melody_grid": 0.5, "hat_rolls": True,
    },
    "house": {
        "bpm": 124, "key": "G", "swing": 0.06, "humanize": 0.0, "clap": True,
        "kick": ["x...x...x...x..."],
        "snare": ["....x.......x..."],
        "hat": ["oooooooooooooooo"],
        "open_hat": ["..x...x...x...x."],
        "progressions": [
            [(0, "m7"), (8, "maj7"), (10, "7"), (5, "m7")],
            [(0, "m9"), (10, "7"), (8, "maj7"), (7, "m7")],
        ],
        "chord_style": "stab", "bass_style": "offbeat",
        "melody_density": 0.25, "melody_grid": 0.25,
    },
}


@dataclass
class Beat:
    genre: str
    bpm: int
    key: int
    bars: int
    seed: int
    progression: list
    notes: list

    def summary(self):
        chords = " - ".join(theory.chord_label(self.key, o, t) for o, t in self.progression)
        return (f"장르 {self.genre} | {self.bpm} BPM | 키 {theory.NOTE_NAMES[self.key]} 마이너 | "
                f"{self.bars}마디 | seed {self.seed}\n코드 진행: {chords}")


def _step_time(step, swing):
    """16분음표 칸 번호를 박 위치로. 홀수 칸(엇박)은 swing만큼 뒤로 민다."""
    t = step * 0.25
    if step % 2 == 1:
        t += swing * 0.25
    return t


def _humanize(rng, amount):
    return rng.uniform(-amount, amount) if amount else 0.0


def _vel(rng, base, spread=8):
    return max(1, min(127, base + rng.randint(-spread, spread)))


def _drums(cfg, rng, bars):
    notes = []
    kick = rng.choice(cfg["kick"])
    kick_b = rng.choice(cfg["kick"])
    snare = rng.choice(cfg["snare"])
    hat = rng.choice(cfg["hat"])
    open_hat = rng.choice(cfg["open_hat"])
    swing, hum = cfg["swing"], cfg["humanize"]
    kick_steps = []

    for bar in range(bars):
        bar_start = bar * 4
        # 4마디마다 마지막 마디는 킥 변형 패턴으로 변화를 준다
        k = kick_b if bar % 4 == 3 else kick
        last_bar_of_phrase = bar % 4 == 3
        lines = [(KICK, k, 112), (CLAP if cfg.get("clap") else SNARE, snare, 105),
                 (HAT, hat, 70), (OPEN_HAT, open_hat, 72)]
        for pitch, pattern, base_vel in lines:
            for step, ch in enumerate(pattern):
                if ch == ".":
                    continue
                vel = base_vel if ch == "x" else int(base_vel * 0.45)
                if pitch == HAT and step % 4 == 0:
                    vel += 12  # 정박 하이햇 강조
                t = bar_start + _step_time(step, swing) + _humanize(rng, hum)
                notes.append(Note("drums", max(0.0, t), 0.2, pitch, _vel(rng, vel)))
                if pitch == KICK:
                    kick_steps.append(bar * 16 + step)

        # 트랩: 하이햇 롤(32분음표 연타)을 무작위로 넣는다
        if cfg.get("hat_rolls"):
            for _ in range(rng.randint(1, 2)):
                s = rng.choice([6, 7, 14, 15])
                div = rng.choice([2, 3])  # 32분음표 또는 셋잇단
                for i in range(div):
                    t = bar_start + s * 0.25 + i * 0.25 / div
                    notes.append(Note("drums", t, 0.1, HAT, _vel(rng, 60 + i * 10)))

        # 프레이즈 마지막 마디 끝에 스네어 필인
        if last_bar_of_phrase and rng.random() < 0.6 and not cfg.get("clap"):
            for s in (13, 14, 15):
                if rng.random() < 0.7:
                    notes.append(Note("drums", bar_start + _step_time(s, swing), 0.2, SNARE,
                                      _vel(rng, 60 + (s - 13) * 15)))
    return notes, sorted(kick_steps)


def _chords(cfg, rng, bars, key, prog):
    notes = []
    style = cfg["chord_style"]
    for bar in range(bars):
        offset, ctype = prog[bar % len(prog)]
        pitches = theory.chord_notes(key, offset, ctype)
        start = bar * 4
        if style == "strum":  # 로파이: 살짝 흩뿌리듯 누르고 한 마디 유지
            for i, p in enumerate(pitches):
                notes.append(Note("chords", start + i * 0.03 + _humanize(rng, 0.01), 3.8, p, _vel(rng, 62)))
        elif style == "hold":
            for p in pitches:
                notes.append(Note("chords", start, 3.9, p, _vel(rng, 64, 4)))
        elif style == "pad":
            for p in pitches:
                notes.append(Note("chords", start, 4.0, p + 12, _vel(rng, 55, 3)))
        elif style == "stab":  # 하우스: 엇박에 짧게 끊어 치기
            for s in (2, 5, 10, 13):
                for p in pitches:
                    notes.append(Note("chords", start + s * 0.25, 0.22, p + 12, _vel(rng, 78, 5)))
    return notes


def _bass(cfg, rng, bars, key, prog, kick_steps):
    notes = []
    style = cfg["bass_style"]
    if style in ("follow_kick", "808"):
        total = bars * 16
        for i, step in enumerate(kick_steps):
            nxt = kick_steps[i + 1] if i + 1 < len(kick_steps) else total
            bar = step // 16
            offset, _ = prog[bar % len(prog)]
            pitch = theory.bass_note(key, offset)
            if style == "follow_kick" and rng.random() < 0.15:
                pitch += 7  # 가끔 5음으로 움직임
            max_len = 4.0 if style == "808" else 1.5
            dur = min((nxt - step) * 0.25, max_len) * 0.92
            start = _step_time(step % 16, cfg["swing"]) + bar * 4
            notes.append(Note("bass", start, max(dur, 0.2), pitch, _vel(rng, 100, 6)))
    elif style == "offbeat":
        for bar in range(bars):
            offset, _ = prog[bar % len(prog)]
            pitch = theory.bass_note(key, offset)
            for s in (2, 6, 10, 14):
                notes.append(Note("bass", bar * 4 + s * 0.25, 0.4, pitch, _vel(rng, 96, 5)))
    return notes


def _melody(cfg, rng, bars, key, prog):
    notes = []
    scale = theory.scale_notes(key)
    grid = cfg["melody_grid"]
    steps_per_bar = int(4 / grid)
    # 2마디짜리 모티프를 만들고 반복하면서 조금씩 바꾼다 (사람이 기억하기 쉬운 멜로디)
    motif = []
    idx = len(scale) // 2
    for s in range(steps_per_bar * 2):
        strong = (s * grid) % 1 == 0
        if rng.random() < cfg["melody_density"] * (1.4 if strong else 0.8):
            idx = max(0, min(len(scale) - 1, idx + rng.choice([-2, -1, -1, 0, 1, 1, 2])))
            length = grid * rng.choice([1, 1, 2, 3])
            motif.append((s * grid, length, idx))
    if not motif:
        motif.append((0.0, 1.0, idx))

    for phrase in range(0, bars, 2):
        variation = phrase % 4 == 2
        for t, length, i in motif:
            if variation and rng.random() < 0.3:
                i = max(0, min(len(scale) - 1, i + rng.choice([-1, 1])))
            start = phrase * 4 + t
            if start >= bars * 4:
                continue
            notes.append(Note("melody", start + _humanize(rng, cfg["humanize"]), length * 0.95,
                              scale[i], _vel(rng, 80, 10)))
    return notes


def generate(genre="lofi", bpm=None, bars=8, key=None, seed=None, melody=True):
    if genre not in GENRES:
        raise ValueError(f"지원하지 않는 장르: {genre} (가능: {', '.join(GENRES)})")
    cfg = GENRES[genre]
    if seed is None:
        seed = random.randrange(1, 1_000_000)
    rng = random.Random(seed)
    bpm = bpm or cfg["bpm"]
    key_num = theory.parse_key(key or cfg["key"])
    prog = rng.choice(cfg["progressions"])

    drum_notes, kick_steps = _drums(cfg, rng, bars)
    notes = drum_notes
    notes += _chords(cfg, rng, bars, key_num, prog)
    notes += _bass(cfg, rng, bars, key_num, prog, kick_steps)
    if melody:
        notes += _melody(cfg, rng, bars, key_num, prog)
    notes.sort(key=lambda n: n.start)
    return Beat(genre, bpm, key_num, bars, seed, prog, notes)
