# -*- coding: utf-8 -*-
"""아카이브 사이트 생성기: output/*/blog_draft.md → site/ 정적 HTML.

사용: python build_site.py
출력: site/index.html, site/posts/<slug>.html, about/privacy/style.css
GitHub Pages에 site/ 폴더를 올리면 그대로 블로그가 된다.
"""
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import markdown

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent
SITE = ROOT / "docs"  # GitHub Pages 브랜치 배포는 루트 또는 /docs만 지원
SITE_TITLE = "3분 정리"
SITE_DESC = "경제 · IT · 생활, 매일 아침 3분이면 끝나는 뉴스 정리"
# GitHub Pages 주소 확정 후 기입 (예: "https://<계정>.github.io/<repo>").
# 비어 있으면 canonical/og:url/RSS/sitemap은 생략되고, 채우면 다음 빌드에서 자동 생성된다.
BASE_URL = "https://smkang1023-png.github.io/3min"

NICHE_COLOR = {"econ": "#1D4ED8", "techlife": "#6D28D9", "ai": "#0891B2"}

PAGE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{site_title}">
<meta property="og:locale" content="ko_KR">
{extra_head}<link rel="stylesheet" href="{css}">
<!-- adsense: 승인 후 이 자리에 스크립트 삽입 -->
</head>
<body>
<header class="top">
  <a class="brand" href="{home}">⏱ {site_title}</a>
  <nav><a href="{home}about.html">소개</a></nav>
</header>
<main>
{body}
</main>
<footer>
  <p>{site_title} — {site_desc}</p>
  <p>본 사이트의 콘텐츠는 정보 제공 목적이며, 투자 판단의 책임은 본인에게 있습니다.</p>
  <p><a href="{home}about.html">소개</a> · <a href="{home}privacy.html">개인정보처리방침</a></p>
</footer>
</body>
</html>
"""

ABOUT_MD = f"""# {SITE_TITLE} 소개

**{SITE_TITLE}**는 매일 아침, 그날 꼭 알아야 할 경제·IT·생활 뉴스를 3분 분량으로 정리하는 사이트입니다.

- **경제**: 물가, 증시, 환율, 부동산 — 내 지갑에 닿는 것만
- **IT · 생활**: 요금·제도 변경, 신제품, 소비자 혜택 — 오늘 바뀌는 것만

어렵게 쓰지 않습니다. 사실을 먼저, 그게 나에게 무슨 의미인지를 한 줄로 덧붙입니다.

문의: smkang1023@gmail.com
"""

PRIVACY_MD = f"""# 개인정보처리방침

{SITE_TITLE}(이하 "사이트")는 방문자의 개인정보를 직접 수집하지 않습니다.

## 쿠키 및 광고

사이트는 Google AdSense 등 제3자 광고 서비스를 사용할 수 있습니다. 광고 서비스 제공자는
쿠키를 사용하여 방문 기록에 기반한 광고를 표시할 수 있으며, 방문자는 브라우저 설정에서
쿠키를 차단하거나 [Google 광고 설정](https://adssettings.google.com)에서 맞춤 광고를
해제할 수 있습니다.

## 통계

사이트는 방문자 수 파악을 위해 익명화된 트래픽 통계 도구를 사용할 수 있습니다.
이 과정에서 개인을 식별할 수 있는 정보는 저장되지 않습니다.

## 문의

개인정보 관련 문의: smkang1023@gmail.com

시행일: 2026년 7월 6일
"""


def md_to_html(text):
    return markdown.markdown(text, extensions=["extra"])


def load_posts():
    posts = []
    for cj in sorted((ROOT / "content").glob("*.json"), reverse=True):
        spec = json.loads(cj.read_text(encoding="utf-8"))
        draft = ROOT / "output" / spec["slug"] / "blog_draft.md"
        if not draft.exists():
            continue
        md_text = draft.read_text(encoding="utf-8")
        m = re.search(r"^# (.+)$", md_text, re.M)
        title = m.group(1).strip() if m else spec["cover"]["headline"].replace("\n", " ")
        posts.append({
            "slug": spec["slug"],
            "niche": spec["niche"],
            "date": spec["date"],
            "title": title,
            "summary": " / ".join(c["title"] for c in spec["cards"]),
            "html": md_to_html(md_text),
        })
    return posts


def badge(niches, niche):
    color = NICHE_COLOR.get(niche, "#555")
    label = niches[niche]["display"]
    return f'<span class="badge" style="background:{color}">{label}</span>'


def post_date_iso(slug):
    """slug 앞 8자리(YYYYMMDD) → ISO 날짜. 형식이 다르면 None."""
    m = re.match(r"(\d{4})(\d{2})(\d{2})", slug)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def write_page(path, title, desc, body, home, og_type="website", rel_url=None):
    extra = []
    if BASE_URL and rel_url is not None:
        extra.append(f'<link rel="canonical" href="{BASE_URL}/{rel_url}">')
        extra.append(f'<meta property="og:url" content="{BASE_URL}/{rel_url}">')
    if BASE_URL:
        extra.append(f'<link rel="alternate" type="application/rss+xml" '
                     f'title="{SITE_TITLE}" href="{BASE_URL}/feed.xml">')
    extra_head = "".join(f"{tag}\n" for tag in extra)
    title, desc = html.escape(title, quote=True), html.escape(desc, quote=True)
    path.write_text(
        PAGE.format(title=title, desc=desc, body=body, home=home, og_type=og_type,
                    extra_head=extra_head,
                    css=f"{home}style.css", site_title=SITE_TITLE, site_desc=SITE_DESC),
        encoding="utf-8")


def write_feed(posts):
    """RSS 2.0 — BASE_URL이 있어야 절대 링크를 만들 수 있다."""
    items = []
    for p in posts:
        iso = post_date_iso(p["slug"])
        pub = ""
        if iso:
            dt = datetime.fromisoformat(iso).replace(hour=7, tzinfo=timezone.utc)
            pub = f"<pubDate>{dt.strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>"
        link = f"{BASE_URL}/posts/{p['slug']}.html"
        items.append(
            f"<item><title>{html.escape(p['title'])}</title>"
            f"<link>{link}</link><guid>{link}</guid>{pub}"
            f"<description>{html.escape(p['summary'])}</description></item>")
    feed = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<rss version="2.0"><channel>'
            f'<title>{html.escape(SITE_TITLE)}</title><link>{BASE_URL}/</link>'
            f'<description>{html.escape(SITE_DESC)}</description>'
            f'<language>ko</language>{"".join(items)}</channel></rss>\n')
    (SITE / "feed.xml").write_text(feed, encoding="utf-8")


def write_sitemap(posts):
    urls = [f"{BASE_URL}/", f"{BASE_URL}/about.html", f"{BASE_URL}/privacy.html"]
    urls += [f"{BASE_URL}/posts/{p['slug']}.html" for p in posts]
    body = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
    (SITE / "sitemap.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>\n',
        encoding="utf-8")


def main():
    niches = json.loads((ROOT / "niches.json").read_text(encoding="utf-8"))
    (SITE / "posts").mkdir(parents=True, exist_ok=True)
    posts = load_posts()

    # 개별 글
    for p in posts:
        body = f'<article class="post">{badge(niches, p["niche"])}' \
               f'<p class="date">{p["date"]}</p>{p["html"]}</article>'
        write_page(SITE / "posts" / f'{p["slug"]}.html', f'{p["title"]} — {SITE_TITLE}',
                   p["summary"], body, home="../", og_type="article",
                   rel_url=f'posts/{p["slug"]}.html')

    # 목록
    items = "\n".join(
        f'<a class="card" href="posts/{p["slug"]}.html">'
        f'{badge(niches, p["niche"])}<h2>{p["title"]}</h2>'
        f'<p class="date">{p["date"]}</p><p class="sum">{p["summary"]}</p></a>'
        for p in posts)
    hero = f'<section class="hero"><h1>{SITE_TITLE}</h1><p>{SITE_DESC}</p></section>'
    write_page(SITE / "index.html", SITE_TITLE, SITE_DESC, hero + f'<section class="list">{items}</section>', home="", rel_url="")

    write_page(SITE / "about.html", f"소개 — {SITE_TITLE}", SITE_DESC,
               f'<article class="post">{md_to_html(ABOUT_MD)}</article>', home="", rel_url="about.html")
    write_page(SITE / "privacy.html", f"개인정보처리방침 — {SITE_TITLE}", SITE_DESC,
               f'<article class="post">{md_to_html(PRIVACY_MD)}</article>', home="", rel_url="privacy.html")

    (SITE / "style.css").write_text(CSS, encoding="utf-8")
    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    robots = "User-agent: *\nAllow: /\n"
    if BASE_URL:
        robots += f"Sitemap: {BASE_URL}/sitemap.xml\n"
        write_feed(posts)
        write_sitemap(posts)
    (SITE / "robots.txt").write_text(robots, encoding="utf-8")
    seo = "RSS/sitemap 포함" if BASE_URL else "RSS/sitemap은 BASE_URL 기입 후 생성"
    print(f"글 {len(posts)}개 + 색인/소개/방침/robots ({seo}) → {SITE}")


CSS = """
:root { --ink:#17171c; --gray:#5f5f69; --line:#e8e8e6; --bg:#fafaf8; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
  font-family:"Pretendard","Malgun Gothic","Apple SD Gothic Neo",sans-serif; line-height:1.7; }
.top { display:flex; justify-content:space-between; align-items:center;
  padding:18px 24px; border-bottom:1px solid var(--line); background:#fff; }
.brand { font-weight:800; font-size:20px; color:var(--ink); text-decoration:none; }
.top nav a { color:var(--gray); text-decoration:none; margin-left:16px; }
main { max-width:720px; margin:0 auto; padding:24px 20px 60px; }
.hero { padding:36px 0 8px; }
.hero h1 { font-size:40px; margin:0 0 8px; }
.hero p { color:var(--gray); margin:0; }
.list { display:grid; gap:16px; margin-top:28px; }
.card { display:block; background:#fff; border:1px solid var(--line); border-radius:14px;
  padding:22px 24px; text-decoration:none; color:var(--ink); transition:transform .1s; }
.card:hover { transform:translateY(-2px); }
.card h2 { font-size:21px; margin:10px 0 6px; line-height:1.45; }
.card .sum { color:var(--gray); font-size:15px; margin:6px 0 0; }
.badge { display:inline-block; color:#fff; font-size:13px; font-weight:700;
  padding:3px 12px; border-radius:12px; }
.date { color:var(--gray); font-size:14px; margin:4px 0 0; }
.post { background:#fff; border:1px solid var(--line); border-radius:14px; padding:30px 28px; }
.post h1 { font-size:28px; line-height:1.45; }
.post h2 { font-size:21px; margin-top:34px; border-left:4px solid var(--ink); padding-left:12px; }
.post blockquote { margin:16px 0; padding:12px 18px; background:var(--bg);
  border-left:4px solid #ccc; color:var(--gray); }
.post hr { border:none; border-top:1px solid var(--line); margin:30px 0; }
footer { max-width:720px; margin:0 auto; padding:24px 20px 48px;
  color:var(--gray); font-size:13px; border-top:1px solid var(--line); }
footer a { color:var(--gray); }
"""


if __name__ == "__main__":
    main()
