# -*- coding: utf-8 -*-
"""소재 수집기 v3: niches.json에 정의된 니치별 소스에서 실측 수집.

사용: python trends.py [econ|techlife|all]   (기본 all)
출력: data/topics_<niche>_YYYYMMDD_HHMM.json + 콘솔 요약
소스 값이 "search:키워드"면 구글 뉴스 검색 RSS로 변환된다.

v3: 항목별 매체명(outlet)을 추출하고, 검증된 언론사 화이트리스트에 따라
trusted 플래그를 붙인다. 사실 서술은 trusted=true 항목만 근거로 쓴다
(정보통신망법상 허위사실 유포 리스크 차단 — pipeline-ops/VERIFIER_SPEC.md).
"""
import datetime
import json
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# 검증된 언론사 화이트리스트 (통신사·지상파·종편·주요 일간지·경제지·IT 전문지·정부)
TRUSTED_OUTLETS = {
    # 통신사
    "연합뉴스", "연합인포맥스", "뉴시스", "뉴스1",
    # 방송
    "KBS", "KBS 뉴스", "MBC", "MBC 뉴스", "SBS", "SBS 뉴스", "SBS Biz",
    "YTN", "JTBC", "MBN", "채널A", "TV조선", "연합뉴스TV", "한국경제TV",
    # 종합 일간지
    "조선일보", "중앙일보", "동아일보", "한겨레", "경향신문",
    "한국일보", "서울신문", "국민일보", "세계일보", "문화일보", "노컷뉴스",
    # 경제지
    "매일경제", "한국경제", "서울경제", "머니투데이", "아시아경제",
    "파이낸셜뉴스", "이데일리", "헤럴드경제", "아주경제", "조선비즈", "매경이코노미",
    # IT·전문지
    "전자신문", "지디넷코리아", "ZDNet Korea", "디지털데일리",
    "디지털타임스", "블로터", "IT조선", "아이뉴스24", "테크M",
    # 정부·공공
    "대한민국 정책브리핑", "정책브리핑",
}


def match_outlet(name):
    """매체명이 화이트리스트에 있는지 (앞뒤 수식 허용: 'KBS 뉴스' 등)."""
    if not name:
        return False
    if name in TRUSTED_OUTLETS:
        return True
    return any(name.startswith(t) or t in name for t in TRUSTED_OUTLETS if len(t) >= 3)


def source_url(value):
    if value.startswith("search:"):
        q = urllib.parse.quote(value[len("search:"):])
        return f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"
    return value


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def parse_rss(raw, source):
    root = ET.fromstring(raw)
    ns = {"ht": "https://trends.google.com/trending/rss"}
    items = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        outlet = (it.findtext("source") or "").strip()
        if " - " in title:
            # 구글 뉴스 제목 꼬리("제목 - 매체명") 정리
            head, tail = title.rsplit(" - ", 1)
            head, tail = head.strip(), tail.strip()
            if not outlet:
                title, outlet = head, tail
            elif tail == outlet or tail in outlet or outlet in tail:
                title = head
        row = {
            "source": source,
            "title": title,
            "outlet": outlet,
            "trusted": match_outlet(outlet),
            "link": (it.findtext("link") or "").strip(),
            "pubDate": (it.findtext("pubDate") or "").strip(),
        }
        traffic = it.findtext("ht:approx_traffic", namespaces=ns)
        if traffic:
            row["approx_traffic"] = traffic.strip()
            row["trusted"] = False  # 트렌드 키워드는 소재 발굴용 — 사실 근거로 쓰지 않음
        items.append(row)
    return items


def collect_niche(niche, cfg, out_dir, stamp):
    rows = []
    for name, value in cfg["sources"].items():
        try:
            got = parse_rss(fetch(source_url(value)), name)
            print(f"  [{name}] {len(got)}건")
            rows += got
        except Exception as e:
            print(f"  [{name}] 실패: {e}")
    out = out_dir / f"topics_{niche}_{stamp}.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    n_trusted = sum(1 for r in rows if r.get("trusted"))
    print(f"  → {out.name} ({len(rows)}건, 검증 매체 {n_trusted}건)")
    for r in rows[:6]:
        print(f"    - {r['title'][:60]}")
    return rows


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "all"
    niches = json.loads((Path(__file__).parent / "niches.json").read_text(encoding="utf-8"))
    if target != "all" and target not in niches:
        sys.exit(f"알 수 없는 니치: {target} (가능: {', '.join(niches)}, all)")

    out_dir = Path(__file__).parent / "data"
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    for niche, cfg in niches.items():
        if target != "all" and niche != target:
            continue
        if not cfg.get("sources"):
            continue  # 별도 수집기를 쓰는 니치 (예: ai → collect_ai.py)
        print(f"\n=== {niche} ({cfg['display']}) ===")
        collect_niche(niche, cfg, out_dir, stamp)


if __name__ == "__main__":
    main()
