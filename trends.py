# -*- coding: utf-8 -*-
"""소재 수집기 v2: niches.json에 정의된 니치별 소스에서 실측 수집.

사용: python trends.py [econ|techlife|all]   (기본 all)
출력: data/topics_<niche>_YYYYMMDD_HHMM.json + 콘솔 요약
소스 값이 "search:키워드"면 구글 뉴스 검색 RSS로 변환된다.
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
        row = {
            "source": source,
            "title": (it.findtext("title") or "").strip(),
            "link": (it.findtext("link") or "").strip(),
            "pubDate": (it.findtext("pubDate") or "").strip(),
        }
        traffic = it.findtext("ht:approx_traffic", namespaces=ns)
        if traffic:
            row["approx_traffic"] = traffic.strip()
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
    print(f"  → {out.name} ({len(rows)}건)")
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
        print(f"\n=== {niche} ({cfg['display']}) ===")
        collect_niche(niche, cfg, out_dir, stamp)


if __name__ == "__main__":
    main()
