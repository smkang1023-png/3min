# -*- coding: utf-8 -*-
"""스레드 글 포맷터: 같은 콘텐츠 JSON → 스레드 체인(훅 + 답글) 텍스트.

사용: python make_threads.py content/파일.json
출력: output/<slug>/threads.txt (500자 검사) + twitter.txt (280자 검사, 같은 체인)
      트위터 쪽에서 280자를 넘긴 게시물은 twitter.txt에서 그 게시물만 재작성한다
      (문장 중간 절단 금지 — pipeline-ops/STYLE_GUIDE.md §2).
      + caption.txt (인스타 캐러셀 캡션, 2,200자 검사, 해시태그는 niches.json)
나중 조각: Threads 공식 API(액세스 토큰)로 자동 게시.
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LIMIT = 500
LIMIT_TW = 280
LIMIT_IG = 2200


def build_chain(spec):
    posts = []
    hook = f"{spec['cover']['headline'].replace(chr(10), ' ')}\n\n"
    hook += spec["cover"]["sub"].replace("\n", " ")
    hook += f"\n\n오늘({spec['date']}) 꼭 알아야 할 {len(spec['cards'])}가지 🧵"
    posts.append(hook)
    for i, card in enumerate(spec["cards"], start=1):
        posts.append(f"{i}. {card['title']}\n\n{card['body']}")
    outro = spec["outro"]["text"].replace("\n", " ")
    note = spec["outro"].get("note", "")
    last = f"{outro}\n\n{note}"
    outlets = collect_outlets(spec)
    if outlets:
        community = all(o.startswith("r/") or o in ("Hacker News", "HN") for o in outlets)
        joined = " · ".join(outlets)
        last += f"\n\n출처: {joined}" if community else f"\n\n자료: {joined} 보도"
    posts.append(last)
    return posts


def collect_outlets(spec):
    outlets = []
    for card in spec["cards"]:
        o = card.get("source", {}).get("outlet")
        if o and o not in outlets:
            outlets.append(o)
    return outlets


def build_caption(spec, niche_cfg):
    """인스타 캐러셀 캡션 — 첫 줄이 '더보기' 접힘 전에 노출되므로 훅을 앞에 둔다."""
    hook = spec["cover"]["headline"].replace("\n", " ")
    sub = spec["cover"]["sub"].replace("\n", " ")
    lines = [f"{hook} ({spec['date']})", "", sub, ""]
    for i, card in enumerate(spec["cards"], start=1):
        lines.append(f"{i}. {card['title']}")
    lines += ["", "자세한 내용은 카드로 넘겨보세요. 저장해 두면 하루 3분이면 됩니다."]
    note = spec["outro"].get("note", "")
    if note:
        lines += ["", note]
    outlets = collect_outlets(spec)
    if outlets:
        community = all(o.startswith("r/") or o in ("Hacker News", "HN") for o in outlets)
        joined = " · ".join(outlets)
        lines += ["", f"출처: {joined}" if community else f"자료: {joined} 보도"]
    tags = niche_cfg.get("hashtags", [])
    if tags:
        lines += ["", " ".join(tags)]
    return "\n".join(lines)


def main():
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    niches = json.loads((Path(__file__).parent / "niches.json").read_text(encoding="utf-8"))
    niche_cfg = niches.get(spec["niche"], {})
    posts = build_chain(spec)
    out_dir = Path(__file__).parent / "output" / spec["slug"]
    out_dir.mkdir(parents=True, exist_ok=True)
    body = "\n\n---\n\n".join(posts)
    out = out_dir / "threads.txt"
    out.write_text(body, encoding="utf-8")
    out_tw = out_dir / "twitter.txt"
    out_tw.write_text(body, encoding="utf-8")
    tw_over = 0
    for i, p in enumerate(posts):
        n = len(p)
        flag_th = "⚠ 500자 초과!" if n > LIMIT else "OK"
        flag_tw = "⚠ 280자 초과" if n > LIMIT_TW else "OK"
        tw_over += n > LIMIT_TW
        print(f"[{i}] {n}자  threads:{flag_th}  twitter:{flag_tw}")
    print(f"\n체인 {len(posts)}개 → {out}")
    print(f"트위터용 → {out_tw}" + (f" (⚠ {tw_over}개 게시물 재작성 필요)" if tw_over else " (전부 280자 이내)"))

    caption = build_caption(spec, niche_cfg)
    out_ig = out_dir / "caption.txt"
    out_ig.write_text(caption, encoding="utf-8")
    flag_ig = "⚠ 2,200자 초과!" if len(caption) > LIMIT_IG else "OK"
    print(f"인스타 캡션 {len(caption)}자 ({flag_ig}) → {out_ig}")


if __name__ == "__main__":
    main()
