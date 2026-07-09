# -*- coding: utf-8 -*-
"""쇼트리스트 번호 → 수집 원본 레코드 추출 (소재 확정 + 검수 입력용).

사용: python pick.py <niche> <번호> [번호 ...]
  번호는 같은 스탬프의 shortlist_<niche>_*.txt 기준 (1부터).
출력: 선택 레코드 JSON(콘솔) + data/picked_<niche>_<stamp>.json
  콘텐츠 JSON의 source 필드는 이 레코드의 outlet/title/link를 그대로 쓴다.
  검수자에게는 전체 topics 파일 대신 picked 파일만 전달한다 (토큰 절감).
"""
import io
import json
import sys
from pathlib import Path

from trends import build_shortlist

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA = Path(__file__).parent / "data"


def main():
    if len(sys.argv) < 3:
        sys.exit("사용법: python pick.py <niche> <번호> [번호 ...]")
    niche = sys.argv[1]
    nums = [int(a) for a in sys.argv[2:]]

    latest = sorted(DATA.glob(f"topics_{niche}_*.json"))[-1]
    stamp = latest.stem.replace(f"topics_{niche}_", "")
    rows = json.load(io.open(latest, encoding="utf-8"))
    shortlist = build_shortlist(rows)

    picked = []
    for n in nums:
        if not 1 <= n <= len(shortlist):
            sys.exit(f"번호 범위 밖: {n} (1~{len(shortlist)})")
        picked.append(shortlist[n - 1])

    out = DATA / f"picked_{niche}_{stamp}.json"
    out.write_text(json.dumps(picked, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(picked, ensure_ascii=False, indent=1))
    print(f"\n→ {out.name} (검수자 전달용)")


if __name__ == "__main__":
    main()
