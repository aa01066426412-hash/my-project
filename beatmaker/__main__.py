"""명령줄 실행: python -m beatmaker --genre lofi"""

import argparse
import time
from pathlib import Path

from .midi import write_midi
from .patterns import GENRES, generate
from .synth import render


def main(argv=None):
    p = argparse.ArgumentParser(prog="beatmaker", description="규칙 기반 비트 생성기 (MIDI + WAV)")
    p.add_argument("--genre", choices=list(GENRES), default="lofi", help="장르 (기본: lofi)")
    p.add_argument("--bpm", type=int, help="빠르기. 생략하면 장르 기본값")
    p.add_argument("--bars", type=int, default=8, help="마디 수 (기본: 8)")
    p.add_argument("--key", help="조성 근음, 예: A, F#, Bb (마이너 키로 생성)")
    p.add_argument("--seed", type=int, help="같은 seed를 주면 같은 비트가 다시 나온다")
    p.add_argument("--out", default="output", help="저장 폴더 (기본: output)")
    p.add_argument("--name", help="파일 이름 (기본: 장르_seed)")
    p.add_argument("--no-melody", action="store_true", help="멜로디 없이 반주만")
    p.add_argument("--no-wav", action="store_true", help="MIDI만 만들고 WAV 렌더링은 건너뛴다")
    args = p.parse_args(argv)

    if args.bars < 1 or args.bars > 64:
        p.error("--bars는 1~64 사이여야 합니다")
    if args.bpm is not None and not 40 <= args.bpm <= 220:
        p.error("--bpm은 40~220 사이여야 합니다")

    try:
        beat = generate(args.genre, args.bpm, args.bars, args.key, args.seed, melody=not args.no_melody)
    except ValueError as e:
        p.error(str(e))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    name = args.name or f"{beat.genre}_{beat.seed}"

    print(beat.summary())
    mid_path = out / f"{name}.mid"
    write_midi(beat, mid_path, title=name)
    print(f"MIDI 저장: {mid_path}")

    if not args.no_wav:
        t0 = time.time()
        length = render(beat, out / f"{name}.wav")
        print(f"WAV 저장: {out / f'{name}.wav'} ({length:.1f}초, 렌더링 {time.time() - t0:.1f}초)")


if __name__ == "__main__":
    main()
