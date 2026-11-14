"""음악 이론 도우미: 조성, 코드, 스케일."""

NOTE_OFFSETS = {
    "C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3, "E": 4, "F": 5,
    "F#": 6, "GB": 6, "G": 7, "G#": 8, "AB": 8, "A": 9, "A#": 10, "BB": 10, "B": 11,
}
NOTE_NAMES = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]

CHORD_TYPES = {
    "min": [0, 3, 7],
    "maj": [0, 4, 7],
    "m7": [0, 3, 7, 10],
    "maj7": [0, 4, 7, 11],
    "7": [0, 4, 7, 10],
    "m9": [0, 3, 7, 10, 14],
    "maj9": [0, 4, 7, 11, 14],
}

# 마이너 펜타토닉: 어떤 코드 위에서도 크게 어긋나지 않는 안전한 멜로디 스케일
MINOR_PENTATONIC = [0, 3, 5, 7, 10]


def parse_key(name):
    """'A', 'Am', 'F#', 'Bb' 같은 문자열을 0~11 숫자로 바꾼다. 끝의 m(마이너 표시)은 무시한다."""
    s = name.strip()
    if len(s) > 1 and s.endswith("m"):
        s = s[:-1]
    key = s.upper()
    if key not in NOTE_OFFSETS:
        raise ValueError(f"알 수 없는 키: {name} (예: C, F#, Bb)")
    return NOTE_OFFSETS[key]


def chord_label(key, offset, ctype):
    suffix = {"maj": "", "min": "m"}.get(ctype, ctype)
    return f"{NOTE_NAMES[(key + offset) % 12]}{suffix}"


def chord_notes(key, offset, ctype, base=48):
    """코드 구성음(MIDI 번호). 근음을 base 근처에 둬서 보이싱이 너무 높아지지 않게 한다."""
    root = base + (key + offset) % 12
    if root > base + 7:
        root -= 12
    return [root + i for i in CHORD_TYPES[ctype]]


def bass_note(key, offset, base=36):
    return base + (key + offset) % 12


def scale_notes(key, low=64, high=86, intervals=MINOR_PENTATONIC):
    notes = []
    for n in range(low, high + 1):
        if (n - key) % 12 in intervals:
            notes.append(n)
    return notes


def midi_to_freq(note):
    return 440.0 * 2 ** ((note - 69) / 12)
