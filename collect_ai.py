# -*- coding: utf-8 -*-
"""AI 트렌드 수집기: 레딧 + Hacker News에서 핫한 AI 글을 실측 수집.

사용: python collect_ai.py
출력: data/topics_ai_YYYYMMDD_HHMM.json + 콘솔 요약 (점수 상위)

수집원 (공개 API/RSS — 스크래핑 아님):
- 레딧 공개 RSS: 서브레딧별 top(day). JSON API는 403이라 RSS 사용 — 점수 대신
  피드 순서(=일간 랭킹)를 rank로 기록
- Hacker News (Algolia 공식 API): 프론트페이지 + Show HN(최근 24h, 점수 필터는 로컬)

주의: 커뮤니티 발 소재라 사실 검증은 라이트 모드(VERIFIER_SPEC §5 A 체크리스트).
원글 이미지·영상은 재업로드 금지 — 요약 + 링크만 쓴다.
"""
import datetime
import json
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UA = {"User-Agent": "content-engine/1.0 (personal daily digest; contact: smkang1023@gmail.com)"}

SUBREDDITS = [
    "LocalLLaMA",        # 오픈소스 모델·개발
    "artificial",        # AI 일반 뉴스
    "OpenAI",            # OpenAI 소식
    "ClaudeAI",          # Claude 소식
    "StableDiffusion",   # 이미지 생성·프롬프트
    "aivideo",           # 영상 생성
    "ChatGPT",           # 바이럴 활용 사례
]
REDDIT_TOP_N = 15
REDDIT_SLEEP = 15         # RSS 요청 간격(초) — 무인증 한도가 빡빡함
HN_MIN_POINTS = 30
HN_SHOW_WINDOW = 48 * 3600
AI_KEYWORDS = ["ai", "llm", "gpt", "claude", "gemini", "model", "agent", "diffusion",
               "openai", "anthropic", "prompt", "생성", "neural", "ml"]


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def get_json(url):
    return json.loads(fetch(url).decode("utf-8"))


ATOM = {"a": "http://www.w3.org/2005/Atom"}
TAG_RE = re.compile(r"<[^>]+>")


def collect_reddit():
    rows = []
    for i, sub in enumerate(SUBREDDITS):
        if i:
            time.sleep(REDDIT_SLEEP)
        url = f"https://www.reddit.com/r/{sub}/top/.rss?t=day&limit={REDDIT_TOP_N}"
        root = None
        for attempt in range(2):
            try:
                root = ET.fromstring(fetch(url))
                break
            except Exception as e:
                if attempt == 0 and "429" in str(e):
                    time.sleep(30)
                    continue
                print(f"  [r/{sub}] 실패: {e}")
        if root is None:
            continue
        got = 0
        for rank, entry in enumerate(root.findall("a:entry", ATOM), start=1):
            title = (entry.findtext("a:title", "", ATOM) or "").strip()
            link_el = entry.find("a:link", ATOM)
            link = link_el.get("href", "") if link_el is not None else ""
            content = entry.findtext("a:content", "", ATOM) or ""
            text = TAG_RE.sub(" ", content)
            text = re.sub(r"\s+", " ", text).replace("submitted by", "").strip()
            if not title:
                continue
            rows.append({
                "source": f"r/{sub}",
                "title": title,
                "selftext": text[:600],
                "link": link,
                "external_url": "",
                "rank": rank,           # 피드 순서 = 일간 top 순위
                "score": max(0, REDDIT_TOP_N + 1 - rank) * 100,  # 정렬용 근사치
            })
            got += 1
            if got >= REDDIT_TOP_N:
                break
        print(f"  [r/{sub}] {got}건")
    return rows


def looks_ai(title):
    t = title.lower()
    return any(k in t for k in AI_KEYWORDS)


def collect_hn():
    rows = []
    day_ago = int(time.time()) - HN_SHOW_WINDOW
    feeds = [
        ("HN 프론트", "https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=30", False),
        ("Show HN", "https://hn.algolia.com/api/v1/search_by_date?tags=show_hn"
                    f"&numericFilters=created_at_i%3E{day_ago}&hitsPerPage=50", True),
    ]
    for name, url, min_points in feeds:
        try:
            data = get_json(url)
        except Exception as e:
            print(f"  [{name}] 실패: {e}")
            continue
        got = 0
        for h in data.get("hits", []):
            title = (h.get("title") or "").strip()
            if not title or not looks_ai(title):
                continue
            if min_points and h.get("points", 0) < HN_MIN_POINTS:
                continue
            rows.append({
                "source": "Hacker News",
                "title": title,
                "selftext": "",
                "link": f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                "external_url": h.get("url") or "",
                "score": h.get("points", 0),
                "num_comments": h.get("num_comments", 0),
                "flair": "Show HN" if name == "Show HN" else "",
            })
            got += 1
        print(f"  [{name}] AI 관련 {got}건")
    return rows


def main():
    print("=== AI 트렌드 수집 ===")
    rows = collect_reddit() + collect_hn()
    rows.sort(key=lambda r: r["score"], reverse=True)
    out_dir = Path(__file__).parent / "data"
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    out = out_dir / f"topics_ai_{stamp}.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  → {out.name} ({len(rows)}건)")
    for r in rows[:8]:
        print(f"    - [{r['score']:>5}] ({r['source']}) {r['title'][:56]}")


if __name__ == "__main__":
    main()
