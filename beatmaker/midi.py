"""표준 MIDI 파일(.mid) 작성기. 외부 라이브러리 없이 바이트를 직접 쓴다."""

import struct

TICKS_PER_BEAT = 480

# 트랙별 MIDI 채널과 악기(General MIDI 프로그램 번호)
TRACKS = {
    "drums": {"channel": 9, "program": None, "name": "Drums"},
    "bass": {"channel": 1, "program": 38, "name": "Bass"},        # Synth Bass 1
    "chords": {"channel": 0, "program": 4, "name": "Keys"},       # Electric Piano 1
    "melody": {"channel": 2, "program": 11, "name": "Melody"},    # Vibraphone
}


def _vlq(value):
    """MIDI 가변 길이 숫자."""
    out = [value & 0x7F]
    value >>= 7
    while value:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(out))


def _chunk(kind, data):
    return kind + struct.pack(">I", len(data)) + data


def _meta_track(bpm, name):
    data = bytearray()
    title = name.encode("utf-8")
    data += _vlq(0) + b"\xFF\x03" + _vlq(len(title)) + title
    tempo = int(60_000_000 / bpm)
    data += _vlq(0) + b"\xFF\x51\x03" + tempo.to_bytes(3, "big")
    data += _vlq(0) + b"\xFF\x58\x04" + bytes([4, 2, 24, 8])  # 4/4 박자
    data += _vlq(0) + b"\xFF\x2F\x00"
    return _chunk(b"MTrk", bytes(data))


def _note_track(track, notes):
    info = TRACKS[track]
    ch = info["channel"]
    events = []  # (tick, 순서, 바이트) — 같은 시점이면 note off(0)를 note on(1)보다 먼저
    for n in notes:
        on = round(n.start * TICKS_PER_BEAT)
        off = max(on + 1, round((n.start + n.dur) * TICKS_PER_BEAT))
        events.append((on, 1, bytes([0x90 | ch, n.pitch, n.vel])))
        events.append((off, 0, bytes([0x80 | ch, n.pitch, 0])))
    events.sort(key=lambda e: (e[0], e[1]))

    data = bytearray()
    name = info["name"].encode()
    data += _vlq(0) + b"\xFF\x03" + _vlq(len(name)) + name
    if info["program"] is not None:
        data += _vlq(0) + bytes([0xC0 | ch, info["program"]])
    last = 0
    for tick, _, msg in events:
        data += _vlq(tick - last) + msg
        last = tick
    data += _vlq(0) + b"\xFF\x2F\x00"
    return _chunk(b"MTrk", bytes(data))


def write_midi(beat, path, title="beatmaker"):
    tracks = [_meta_track(beat.bpm, title)]
    for track in TRACKS:
        notes = [n for n in beat.notes if n.track == track]
        if notes:
            tracks.append(_note_track(track, notes))
    header = _chunk(b"MThd", struct.pack(">HHH", 1, len(tracks), TICKS_PER_BEAT))
    with open(path, "wb") as f:
        f.write(header + b"".join(tracks))
