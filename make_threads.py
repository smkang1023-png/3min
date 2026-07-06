# -*- coding: utf-8 -*-
"""스레드 글 포맷터: 같은 콘텐츠 JSON → 스레드 체인(훅 + 답글) 텍스트.

사용: python make_threads.py content/파일.json
출력: output/<slug>/threads.txt (각 게시물은 --- 로 구분, 500자 제한 검사)
나중 조각: Threads 공식 API(액세스 토큰)로 자동 게시.
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LIMIT = 500


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
    posts.append(f"{outro}\n\n{note}")
    return posts


def main():
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    posts = build_chain(spec)
    out_dir = Path(__file__).parent / "output" / spec["slug"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "threads.txt"
    out.write_text("\n\n---\n\n".join(posts), encoding="utf-8")
    for i, p in enumerate(posts):
        n = len(p)
        flag = "⚠ 500자 초과!" if n > LIMIT else "OK"
        print(f"[{i}] {n}자 {flag}")
    print(f"\n체인 {len(posts)}개 → {out}")


if __name__ == "__main__":
    main()
